#!/usr/bin/env python3
"""图片 → 智谱 GLM 视觉模型 → 文字描述。改编自 kuohii/vision-describe(qwen-vl 版),
改为调用智谱 GLM(glm-5.3-flash),并适配 DeepSeek Harness(DSH)的附件存储与凭据库。
零第三方依赖(urllib + 剪贴板/压缩所需的 Pillow,DSH 自带),Python 3.9+。

图片入口(按优先级):
  1. --clipboard    直接读 Windows 剪贴板(截图/复制图片)——纯文本模型贴图被拒时的首选
  2. <图片路径或URL>...  明确路径
  3. --dir <文件夹>  取文件夹(桌面/下载等)里最新的图
  4. --find-latest   扫 DSH 附件库(仅当图已成功进入 DSH 时有用)

其他: --prompt "问题" | --list 只列不调 | --minutes/--max 时间窗与数量
"""

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)  # 技能根目录(SKILL.md 与 config.json 所在)
CONFIG_PATH = os.path.join(SKILL_DIR, "config.json")
FALLBACK_PROMPT = "请描述这张图片的内容。"
TMP_PREFIX = "vision_tmp_"
CACHE_DIR = os.path.join(tempfile.gettempdir(), "glm_vision_cache")
CACHE_TTL = 3600  # 缓存 1 小时

# 智谱 GLM 图像输入限制(与 DSH 模型目录中 glm-5.3-flash 的 inputLimits 一致)
MAX_IMAGE_BYTES = 4718592   # 4.5 MiB
MAX_DIMENSION = 2000        # 宽/高上限

# Windows 管道默认 GBK 输出,强制 UTF-8 避免乱码
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_dsh_credential(ref_name):
    """从 DSH 凭据库 ~/.dsh/.credentials.yaml 的 refs 段读取值(如 ZAI_API_KEY)。
    找不到或文件不存在返回 None;绝不打印内容。"""
    path = os.path.join(os.path.expanduser("~"), ".dsh", ".credentials.yaml")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return None
    m = re.search(re.escape(ref_name) + r"\s*:\s*([^\s,}\"]+)", text)
    return m.group(1).strip("'\"") if m else None


def load_config():
    config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
    api_key = (os.environ.get("VISION_API_KEY")
               or os.environ.get("ZAI_API_KEY")
               or str(config.get("api_key") or ""))
    if not api_key:
        api_key = load_dsh_credential("ZAI_API_KEY") or ""
    return {
        "base_url": os.environ.get("VISION_BASE_URL") or config.get("base_url", ""),
        "api_key": api_key,
        "model": os.environ.get("VISION_MODEL") or config.get("model", ""),
        "thinking": config.get("thinking", True),
        "default_prompt": config.get("default_prompt") or FALLBACK_PROMPT,
    }


def _read_via_ctypes(path, size=None):
    """CreateFileW 全共享模式读取(Python open 打不开被占用文件时使用)。"""
    try:
        import ctypes
    except ImportError:
        raise PermissionError(f"文件被占用且无法读取: {path}")
    k32 = ctypes.windll.kernel32
    k32.CreateFileW.restype = ctypes.c_void_p
    k32.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                                ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
    k32.ReadFile.restype = ctypes.c_bool
    k32.ReadFile.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32,
                             ctypes.POINTER(ctypes.c_uint32), ctypes.c_void_p]
    k32.GetFileSize.restype = ctypes.c_uint32
    k32.GetFileSize.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    INVALID = ctypes.c_void_p(-1).value
    h = k32.CreateFileW(path, 0x80000000, 0x1 | 0x2 | 0x4, None, 3, 0, None)
    if not h or h == INVALID:
        raise PermissionError(f"CreateFileW 失败: {path}")
    try:
        if size is None:
            size_hi = ctypes.c_ulong()
            size_lo = k32.GetFileSize(h, ctypes.byref(size_hi))
            size = (size_hi.value << 32) | size_lo
        buf = ctypes.create_string_buffer(max(size, 1))
        nread = ctypes.c_ulong()
        if not k32.ReadFile(h, buf, size, ctypes.byref(nread), None):
            raise PermissionError(f"ReadFile 失败: {path}")
        return buf.raw[: nread.value]
    finally:
        k32.CloseHandle(h)


def _read_retry(path, reader, size=None):
    """读文件;Windows 被占用时依次:直接读 → CreateFileW 全共享 → 拷贝到临时目录再读。"""
    try:
        return reader(path)
    except PermissionError:
        pass
    try:
        return _read_via_ctypes(path, size)
    except PermissionError:
        pass
    dst = os.path.join(tempfile.gettempdir(), TMP_PREFIX + os.path.basename(path))
    try:
        if os.path.exists(dst):
            os.remove(dst)
        shutil.copy2(path, dst)
    except PermissionError:
        raise PermissionError(f"图片文件被其他进程锁定且无法读取: {path}(请另存路径后重试)")
    except OSError as e:
        raise OSError(f"读取失败且无法拷贝 {path}: {e}")
    return reader(dst)


def _read_head(path):
    with open(path, "rb") as f:
        return f.read(12)


def _read_all(path):
    with open(path, "rb") as f:
        return f.read()


def detect_image_format(path):
    """magic bytes 识别图片格式,返回 mime;无法识别返回 None。"""
    head = _read_retry(path, _read_head, size=12)
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"GIF8"):
        return "image/gif"
    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return "image/webp"
    if head.startswith(b"BM"):
        return "image/bmp"
    return None


def read_image_bytes(path):
    return _read_retry(path, _read_all)


def shrink_image_if_needed(data, mime):
    """超过智谱限制(4.5MB 或边超 2000px)时,用 Pillow 压缩到长边 2000、JPEG q80。
    Pillow 不可用或仍超限则原样返回(交由 API 报错)。"""
    try:
        from io import BytesIO
        from PIL import Image
    except ImportError:
        return data, mime
    if len(data) <= MAX_IMAGE_BYTES:
        try:
            with Image.open(BytesIO(data)) as im:
                if max(im.size) <= MAX_DIMENSION:
                    return data, mime
        except Exception:
            return data, mime
    try:
        with Image.open(BytesIO(data)) as im:
            im = im.convert("RGB")
            im.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
            out = BytesIO()
            im.save(out, format="JPEG", quality=80)
            shrunk = out.getvalue()
            if len(shrunk) < len(data):
                return shrunk, "image/jpeg"
    except Exception:
        pass
    return data, mime


def _cache_key(data, prompt):
    return hashlib.sha256(data + b"\x00" + prompt.encode("utf-8")).hexdigest()


def cache_lookup(key):
    fp = os.path.join(CACHE_DIR, key + ".txt")
    try:
        if time.time() - os.path.getmtime(fp) < CACHE_TTL:
            with open(fp, "r", encoding="utf-8") as f:
                return f.read()
    except OSError:
        pass
    return None


def cache_store(key, text):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(os.path.join(CACHE_DIR, key + ".txt"), "w", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        pass  # 缓存写失败不影响主流程


def to_data_uri(path):
    mime = detect_image_format(path)
    if mime is None:
        raise ValueError(f"无法识别的图片格式: {path}(DSH 附件为无扩展名文件,按内容识别)")
    data = read_image_bytes(path)
    if len(data) > MAX_IMAGE_BYTES:
        data, mime = shrink_image_if_needed(data, mime)
        if len(data) > MAX_IMAGE_BYTES:
            raise ValueError(f"图片 {path} 压缩后仍超过智谱 4.5MB 限制")
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def find_latest_attachments(minutes=240, max_count=5):
    """扫描 DSH 附件库 ~/.dsh/attachments/v1/objects/(内容寻址、无扩展名、
    已规范化为 JPEG/WebP),按修改时间倒序返回最近图片。每个条目:
    (mtime, path, mime 或 None)。"""
    root = os.path.join(os.path.expanduser("~"), ".dsh", "attachments", "v1", "objects")
    if not os.path.isdir(root):
        return []
    cutoff = time.time() - minutes * 60
    candidates = []
    for d in os.listdir(root):
        dpath = os.path.join(root, d)
        if not os.path.isdir(dpath):
            continue
        for fn in os.listdir(dpath):
            fp = os.path.join(dpath, fn)
            if not os.path.isfile(fp):
                continue
            try:
                mtime = os.path.getmtime(fp)
            except OSError:
                continue
            if mtime < cutoff:
                continue
            try:
                fmt = detect_image_format(fp)
            except OSError:
                fmt = None
            if fmt is None:
                continue  # DSH 附件库只存图片,非图片(或读不了)的跳过
            candidates.append((mtime, fp, fmt))
    candidates.sort(key=lambda c: c[0], reverse=True)
    return candidates[:max_count]


def latest_images_in_dir(folder, minutes=240, max_count=5):
    """取某个文件夹(如桌面/下载)中最近修改的图片文件(不递归子目录)。
    用 magic bytes 识别,扩展名无关。返回 [(mtime, path, mime)]。"""
    if not os.path.isdir(folder):
        raise OSError(f"文件夹不存在: {folder}")
    cutoff = time.time() - minutes * 60
    candidates = []
    for fn in os.listdir(folder):
        fp = os.path.join(folder, fn)
        if not os.path.isfile(fp):
            continue
        try:
            mtime = os.path.getmtime(fp)
        except OSError:
            continue
        if mtime < cutoff:
            continue
        try:
            fmt = detect_image_format(fp)
        except OSError:
            continue
        if fmt is not None:
            candidates.append((mtime, fp, fmt))
    candidates.sort(key=lambda c: c[0], reverse=True)
    return candidates[:max_count]


def grab_clipboard_targets():
    """从 Windows 剪贴板取图(需要 Pillow,DSH 自带的 Python 已含)。
    支持两种形态:位图(截图/网页右键复制)→ 存临时 PNG;文件复制列表 → 按
    magic bytes 过滤出图片文件。返回目标路径列表。"""
    try:
        from PIL import ImageGrab
    except ImportError:
        raise OSError("剪贴板模式需要 Pillow。请用 load_workspace_dependencies 返回的 Python 运行。")
    grabbed = None
    try:
        grabbed = ImageGrab.grabclipboard()
    except Exception as e:
        raise OSError(f"读取剪贴板失败: {e}")
    targets = []
    if grabbed is None:
        raise ValueError("剪贴板里没有图片。请先截图(Win+Shift+S)或复制图片/图片文件,再重试。")
    if isinstance(grabbed, list):
        # 复制的文件(资源管理器里复制的图片文件)→ 文件路径列表
        for item in grabbed:
            if isinstance(item, str) and os.path.isfile(item):
                try:
                    if detect_image_format(item) is not None:
                        targets.append(item)
                except OSError:
                    continue
        if not targets:
            raise ValueError(f"剪贴板里的文件不是图片: {grabbed}")
    else:
        # 位图(截图 / 右键复制图片)→ PIL Image
        fp = os.path.join(tempfile.gettempdir(),
                          f"clipboard_{time.strftime('%Y%m%d_%H%M%S')}.png")
        grabbed.save(fp, format="PNG")
        targets.append(fp)
    return targets


def extract_content(result):
    """兼容 content 为字符串或分段数组两种返回形态,忽略 reasoning_content。"""
    try:
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        print("错误: 响应格式异常: " + json.dumps(result, ensure_ascii=False)[:2000], file=sys.stderr)
        sys.exit(1)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return str(content)


def call_vision(base_url, api_key, model, prompt, image_target, thinking=True):
    """单图:查缓存 → 调智谱 GLM 视觉模型 → 写缓存。返回描述文本。"""
    if image_target.startswith(("http://", "https://")):
        image_part = {"type": "image_url", "image_url": {"url": image_target}}
        key_data = image_target.encode("utf-8")
    else:
        uri = to_data_uri(image_target)
        image_part = {"type": "image_url", "image_url": {"url": uri}}
        key_data = base64.b64decode(uri.split(",", 1)[1])
    key = _cache_key(key_data, prompt)
    cached = cache_lookup(key)
    if cached is not None:
        return cached

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            image_part,
        ]}],
    }
    if thinking:
        payload["thinking"] = {"type": "enabled"}
    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps(payload).encode("utf-8")

    for attempt in range(3):
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + api_key,
        }, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            print(f"错误: 智谱视觉模型返回 HTTP {e.code}\n{detail[:2000]}", file=sys.stderr)
            sys.exit(1)
        except urllib.error.URLError as e:
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            print(f"错误: 无法连接智谱 API: {e.reason}", file=sys.stderr)
            sys.exit(1)

    text = extract_content(result)
    cache_store(key, text)
    return text


def main():
    parser = argparse.ArgumentParser(description="调用智谱 GLM 视觉模型(glm-5.3-flash)描述图片")
    parser.add_argument("images", nargs="*", help="图片文件路径或 http(s) URL,可多个")
    parser.add_argument("--find-latest", action="store_true",
                        help="自动定位 DSH 附件库中最近的贴图(~/.dsh/attachments/v1/objects/)")
    parser.add_argument("--clipboard", action="store_true",
                        help="直接读 Windows 剪贴板里的图(截图/复制的图片或图片文件);贴图被客户端拒绝时的首选入口")
    parser.add_argument("--dir", metavar="FOLDER",
                        help="取指定文件夹(如桌面/下载)里最新的图片文件,配合 --minutes/--max")
    parser.add_argument("--minutes", type=int, default=240, help="--find-latest/--dir 的时间窗(分钟,默认 240)")
    parser.add_argument("--max", type=int, default=5, help="--find-latest 描述几张(默认 5)")
    parser.add_argument("--list", action="store_true", help="只列出候选图片,不调用模型")
    parser.add_argument("--prompt", help="针对图片的具体问题(默认用 config.json 的 default_prompt)")
    parser.add_argument("--model", help="覆盖模型名")
    parser.add_argument("--base-url", help="覆盖 API base URL")
    parser.add_argument("--api-key", help="覆盖 API key")
    parser.add_argument("--no-thinking", action="store_true", help="关闭 thinking(更快,质量略降)")
    args = parser.parse_args()

    if not args.images and not args.find_latest and not args.clipboard and not args.dir:
        parser.print_help()
        sys.exit(1)

    if args.clipboard:
        targets = grab_clipboard_targets()
        src = "剪贴板"
        if len(targets) > 1:
            print(f"剪贴板中有 {len(targets)} 张图片,逐张描述。", file=sys.stderr)
    elif args.dir:
        found = latest_images_in_dir(args.dir, args.minutes, args.max)
        if not found:
            print(f"文件夹 {args.dir} 最近 {args.minutes} 分钟内没有图片文件。", file=sys.stderr)
            sys.exit(1)
        if args.list:
            for mtime, fp, fmt in found:
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))}  {fmt}  {fp}")
            sys.exit(0)
        targets = [fp for _, fp, _ in found]
        src = args.dir
        if len(found) > 1:
            print(f"文件夹 {src} 找到 {len(found)} 张近期图片,按时间倒序逐张描述(最新优先)。", file=sys.stderr)
    elif args.find_latest:
        found = find_latest_attachments(args.minutes, args.max)
        if not found:
            print(f"未找到最近 {args.minutes} 分钟内 DSH 附件库中的图片。", file=sys.stderr)
            sys.exit(1)
        if args.list:
            for mtime, fp, fmt in found:
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))}  {fmt}  {fp}")
            sys.exit(0)
        targets = [fp for _, fp, _ in found]
        src = "DSH 附件库"
        if len(found) > 1:
            print(f"附件库中找到 {len(found)} 张近期图片,按时间倒序逐张描述(最新优先)。", file=sys.stderr)
    else:
        targets = args.images
        src = None
    _ = src

    cfg = load_config()
    base_url = args.base_url or cfg["base_url"]
    api_key = args.api_key or cfg["api_key"]
    model = args.model or cfg["model"]
    prompt = args.prompt or cfg["default_prompt"]

    if not (base_url and api_key and model):
        print(
            "错误: 配置不完整。默认自动读取 ~/.dsh/.credentials.yaml 中的 ZAI_API_KEY;\n"
            "也可在 config.json 填写 base_url/api_key/model,或设置环境变量\n"
            "VISION_BASE_URL / VISION_API_KEY / VISION_MODEL。配置文件: " + CONFIG_PATH,
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        if len(targets) > 1:
            for i, t in enumerate(targets, 1):
                print(f"--- 图片 {i}/{len(targets)} ---", flush=True)
                print(call_vision(base_url, api_key, model, prompt, t,
                                  thinking=not args.no_thinking))
        else:
            print(call_vision(base_url, api_key, model, prompt, targets[0],
                              thinking=not args.no_thinking))
    except PermissionError:
        print("错误: 图片文件被其他进程锁定且无法读取。请稍后重试,或另存路径后重试。", file=sys.stderr)
        sys.exit(1)
    except (FileNotFoundError, ValueError, OSError) as e:
        print("错误: " + str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
