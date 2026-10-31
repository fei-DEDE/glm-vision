# glm-vision

[简体中文](README.md) | [English](README.en.md)

> **给 GLM-5.3 装上眼睛**——调用同门视觉模型 `glm-5.3-flash`,把图片变成文字描述或定向回答。
> 适用于任何能跑 Python 的环境:DeepSeek Harness(DSH)、Claude Code、Codex、任意终端脚本。

## 为什么是 GLM-5.3 专属

- **GLM-5.3 是纯文本旗舰**:接口只收文本,看不了图——`read_image` 被拒、贴图被客户端拦截,任务里一遇到截图/图表/UI 图就卡住
- **同门 GLM-5.3-Flash 是 GLM-5 系列首个原生多模态模型**(输入支持 图/视频/文本/文件),和 GLM-5.3 **同一端点、同一把 API key**,还便宜(输入 $0.15/M tok,约为主力的 1/10)
- 天作之合:**GLM-5.3 继续当大脑,glm-vision 让 GLM-5.3-Flash 当眼睛**,本技能就是两者之间的传话筒

```
GLM-5.3(大脑,纯文本)◄──── 文字描述 ────┐
                                        │
你(截图/复制图片)→ 剪贴板/文件/URL       │
        ↓                               │
describe_image.py(取图 → base64)        │
        ↓                               │
GLM-5.3-Flash(眼睛,原生多模态)──────────┘
```

## 🚀 三步上手(所有环境通用)

**第 1 步 · 放好文件**

```powershell
# 任意位置克隆(或从 Releases 下载 ZIP 解压)
git clone https://github.com/fei-DEDE/glm-vision
```

**第 2 步 · 配一次 API key**(任选其一)

- 环境变量:`VISION_API_KEY`(或 `ZAI_API_KEY`)
- 编辑 `config.json` 的 `api_key`(**勿提交到 git**)
- **DSH 用户免配**:在 设置→模型 里存过智谱 key 就行,技能自动读取

**第 3 步 · 说人话 / 跑命令**

| 你想做什么 | 你说 / 做 | 发生什么 |
|---|---|---|
| 看屏幕上的东西 | `Win+Shift+S` 截图,说 **"看看我刚截的图"** | 从剪贴板读图并描述 |
| 看网页/聊天里的图片 | 右键复制图片,说 **"看剪贴板"** | 同上 |
| 看刚下载的图片 | 说 **"看一下载文件夹里最新那张图"** | 扫描文件夹取最新图 |
| 提取图片文字(OCR) | 说 **"把这张图里的文字都打出来"** | 带定向问题看图 |
| 分析报错截图 | 截图 + 说 **"这个报错是什么意思"** | 定向分析并给答案 |

## 各环境接入方式

### DeepSeek Harness(DSH)

```powershell
git clone https://github.com/fei-DEDE/glm-vision "$env:USERPROFILE\.dsh\skills\glm-vision"
```

技能目录自动发现,无需重启。**零配置**:自动读 DSH 凭据库;额外支持扫描 DSH 附件库(`--find-latest`)。
注意:DSH 对纯文本模型会拦截贴图("当前模型不适合放图片")——走**剪贴板入口**即可完全绕开。

### Claude Code / 其他 agent

把 `SKILL.md`、`config.json`、`scripts/` 复制到你的技能目录(如 `~\.claude\skills\glm-vision\`),配上 key 即可。

### 纯命令行

不依赖任何 agent,直接用(见下节)。

## 🛠 命令行用法

```powershell
# 读剪贴板(截图 / 右键复制图片 / 复制图片文件后)
python scripts\describe_image.py --clipboard

# 定向提问(OCR / 读数值 / 找元素)
python scripts\describe_image.py --clipboard --prompt "图中有哪些文字?"

# 明确路径或 URL(可多图)
python scripts\describe_image.py C:\path\to\img.png https://example.com/x.jpg

# 文件夹取最新图;--list 只列出不调模型
python scripts\describe_image.py --dir "$env:USERPROFILE\Downloads" --list
```

脚本 stdout 就是 GLM-5.3-Flash 的回答。其他参数:`--minutes`(时间窗,默认 240)、`--max`(张数,默认 5)、`--model` / `--base-url` / `--api-key`(覆盖)、`--no-thinking`(更快)。

## ✨ 特性

- **四条图片入口**:剪贴板(`--clipboard`)、明确路径/URL、文件夹最新图(`--dir`)、DSH 附件库(`--find-latest`)
- **零配置优先**:DSH 凭据库自动读取;其他环境 env / config.json
- **结果缓存**:同图同问 1 小时内直接复用,省 token 省时延
- **自动压缩**:超过智谱限制(2000×2000 / 4.5MB)自动用 Pillow 缩放
- **健壮读取**:magic bytes 识别格式(扩展名无关)、Windows 文件锁三级兜底、429/5xx 自动重试

## ⚙️ 配置(config.json)

| 字段 | 默认 | 说明 |
|---|---|---|
| `base_url` | `https://api.z.ai/api/coding/paas/v4` | 智谱 OpenAI 兼容端点;bigmodel.cn 用 `https://open.bigmodel.cn/api/coding/paas/v4` |
| `api_key` | 空 | 留空则:DSH 下自动读凭据库,其他环境读 `VISION_API_KEY`/`ZAI_API_KEY` |
| `model` | `glm-5.3-flash` | GLM-5 系列首个原生多模态模型;追求质量可试 `glm-4.6v`(bigmodel.cn) |
| `thinking` | `true` | 思考模式 |

环境变量 `VISION_BASE_URL` / `VISION_API_KEY` / `VISION_MODEL` 优先于 config.json。

## ❓ 常见问题

**Q: 我的模型/客户端贴不了图怎么办?**
不少客户端按模型能力拦截贴图(DSH 即如此)。走**剪贴板入口**:截图或复制图片后让 agent 跑 `--clipboard`,或直接命令行调用,完全不经过客户端上传通道。

**Q: 只能配 GLM-5.3 用吗?**
为 GLM-5.3 而生,但任何纯文本模型(DeepSeek-R1 等)都能用同一套技能借眼;模型本身支持图像输入时(如 glm-5.3-flash)直接用原生贴图即可,不需要本技能。

**Q: 效果和原生多模态一样吗?**
不完全一样:主模型看到的是**转述**,细节精度取决于视觉模型的描述质量,但 OCR、布局分析、读数等任务足够好用。

## 🙏 致谢

改编自 [kuohii/vision-describe](https://github.com/kuohii/vision-describe)(调用阿里 qwen-vl 的原版,MIT License)。本仓库将视觉后端改为智谱 GLM,并适配 DSH 的凭据库、附件库与技能格式。

## License

[MIT](LICENSE)
