---
name: glm-vision
description: 让纯文本模型(如 glm-5.3)也能"看图":调用智谱 GLM 视觉模型(glm-5.3-flash)把图片转成详细文字描述,或回答针对图片的问题(OCR、截图/图表/UI/报错图分析)。当 read_image 报 "does not declare image input"、用户贴图被拒("当前模型不适合放图片")、用户让看剪贴板/截图/图片路径、或要求识图时使用。
whenToUse: 当前模型不支持图像输入却需要理解图片内容时。图片四条入口:剪贴板(--clipboard,贴图被拒时首选)、明确路径/URL、文件夹最新图(--dir)、DSH 附件库(--find-latest)。
metadata:
  version: "1.2.0"
  author: adapted from kuohii/vision-describe (qwen-vl) for Zhipu GLM (made for glm-5.3)
---

# glm-vision

给 **GLM-5.3**(及其他纯文本模型)装上眼睛:调用同门视觉模型 `glm-5.3-flash`(同一端点、同一把 API key)把图片内容转成文字描述或回答问题。GLM-5.3 继续当大脑,本技能让 GLM-5.3-Flash 当眼睛。适用于任何能跑 Python 的 agent 环境;在 DSH 中额外零配置——API key 自动从 DSH 凭据库(`~/.dsh/.credentials.yaml` 的 `ZAI_API_KEY`)读取,其他环境用 `VISION_API_KEY`/`ZAI_API_KEY` 环境变量或 config.json。

**重要背景**:纯文本模型的贴图会被不少客户端拦截(DSH 提示"当前模型不适合放图片"),这是客户端行为,无法在技能层解除。所以本技能的图片入口不依赖任何贴图通道。

## 何时使用(自动触发)

- **`read_image` 被拒**:报错含 `does not declare image input` → 本技能是唯一出路
- **用户贴图被拒**:提到"放不进去/不让贴图/模型不适合图片" → 引导用户用剪贴板或文件夹入口(见下)
- **用户让看剪贴板/截图**:"看看我刚截的图"、"看剪贴板" → `--clipboard`
- **用户给了图片路径或 URL** → 直接以路径/URL 为参数
- **用户说图片在桌面/下载/某文件夹** → `--dir <文件夹>`
- **任务需要看图才能继续**:OCR、分析截图/图表/UI/报错图 → 上述任一入口 + `--prompt` 定向提问

## 用法

Python 3.9+(剪贴板/压缩需 Pillow):DSH 里优先用 `load_workspace_dependencies` 返回的 Python(自带 Pillow);其他环境用任意装了 Pillow 的 Python。脚本位于本技能目录 `scripts/describe_image.py`:

```powershell
# 首选:读剪贴板(用户截图 Win+Shift+S / 网页右键复制图片 / 资源管理器复制图片文件后)
python <技能目录>\scripts\describe_image.py --clipboard
python <技能目录>\scripts\describe_image.py --clipboard --prompt "图中有哪些文字?"

# 明确路径/URL(支持多图)
python <技能目录>\scripts\describe_image.py <图片路径或URL>

# 文件夹取最新图(桌面/下载/保存目录)
python <技能目录>\scripts\describe_image.py --dir "$env:USERPROFILE\Desktop"
python <技能目录>\scripts\describe_image.py --dir "$env:USERPROFILE\Downloads" --list   # 先列出不调模型

# DSH 附件库(图已进 DSH 时;纯文本模型通常进不去,仅兜底)
python <技能目录>\scripts\describe_image.py --find-latest
```

- `--prompt`:定向问题;不传则用通用描述提示词(逐字转录图中所有文字)
- `--dir` / `--find-latest`:按修改时间倒序取最新 `--max` 张(默认 5),时间窗 `--minutes`(默认 240);`--list` 只列不调模型
- 结果缓存:同图同问 1 小时内直接读缓存(`%TEMP%\glm_vision_cache\`)
- 脚本 stdout 就是视觉模型的回答,直接用它回复用户或继续任务
- 覆盖项:`--model` / `--base-url` / `--api-key`;`--no-thinking` 更快

## 用户贴图被拒时的引导话术

"这个模型本身看不了图,DSH 就不让贴。你可以:① 截图(Win+Shift+S)或右键复制图片,然后跟我说『看剪贴板』;② 把图片存到桌面或下载文件夹,跟我说在哪儿;③ 直接给我图片文件路径。"

## 配置

编辑本技能目录下 `config.json`:

| 字段 | 默认 | 说明 |
|---|---|---|
| `base_url` | `https://api.z.ai/api/coding/paas/v4` | 智谱 OpenAI 兼容端点;bigmodel.cn 改 `https://open.bigmodel.cn/api/coding/paas/v4` |
| `api_key` | 空 | 留空自动读 DSH 凭据库 `ZAI_API_KEY` |
| `model` | `glm-5.3-flash` | 智谱视觉模型;追求质量可试 `glm-4.6v`(bigmodel.cn) |
| `thinking` | `true` | 思考模式 |
| `default_prompt` | 详细描述+逐字转录 | 默认描述提示词 |

环境变量 `VISION_BASE_URL` / `VISION_API_KEY` / `VISION_MODEL` 优先于 config.json。

## 注意

- 模型本身支持图像时(如 glm-5.3-flash、glm-4.6v)直接用 `read_image`,不需要本技能
- 超智谱限制(2000×2000 / 4.5MB)的图自动 Pillow 压缩;DSH 附件库的图已预规范化
- 上游来源:改编自 [kuohii/vision-describe](https://github.com/kuohii/vision-describe)(qwen-vl 版,MIT)
