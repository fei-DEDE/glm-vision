# glm-vision

> 让纯文本模型也能"看图"——调用智谱 GLM 视觉模型(`glm-5.3-flash`),把图片变成文字描述或定向回答。

专为 **DeepSeek Harness(DSH)** 适配,也可用于其他 AI 编程助手(Claude Code / Codex / 任意能跑脚本的 agent)。

## 为什么需要它

- glm-5.3、DeepSeek-R1 等模型是**纯文本**模型:接口只收文本,`read_image` 被拒、贴图被客户端拦截("当前模型不适合放图片")
- 技能(SKILL.md)只是指令,无法改变模型模态——但可以让 agent **借一双眼睛**:脚本调用视觉模型看图,把描述文本带回主模型的上下文

```
你(截图/复制图片) → 剪贴板/文件
        ↓
describe_image.py(取图 → base64 → 带 prompt)
        ↓
智谱 API · glm-5.3-flash(原生多模态,同 key 同端点)
        ↓
文字描述 → stdout → 主模型上下文 → 回答你
```

## 特性

- **四条图片入口**:剪贴板截图/复制图(`--clipboard`,贴图被拒时的首选)、明确路径/URL、文件夹最新图(`--dir`)、DSH 附件库(`--find-latest`)
- **零配置**:API key 自动读取 DSH 凭据库(`~/.dsh/.credentials.yaml` 的 `ZAI_API_KEY`);也可用环境变量或 `config.json`
- **结果缓存**:同图同问 1 小时内直接复用,省 token 省时延
- **自动压缩**:超过智谱限制(2000×2000 / 4.5MB)自动用 Pillow 缩放
- **健壮读取**:magic bytes 识别格式(扩展名无关)、Windows 文件锁三级兜底、429/5xx 自动重试

## 安装

### DeepSeek Harness

```powershell
git clone https://github.com/fei-DEDE/glm-vision "$env:USERPROFILE\.dsh\skills\glm-vision"
```

或直接把本目录复制到 `~\.dsh\skills\glm-vision\`。无需其他配置——只要你的 DSH 用智谱(zai)提供商并存了 `ZAI_API_KEY`。

### 其他 agent(Claude Code 等)

把 `SKILL.md`、`config.json`、`scripts/` 复制到你的技能目录,并任选一种方式配 key:

- 环境变量 `VISION_API_KEY`(或 `ZAI_API_KEY`)
- 在 `config.json` 的 `api_key` 填入(**不要提交到 git**)

## 用法

```powershell
# 读剪贴板(截图 Win+Shift+S / 网页右键复制图片 / 复制图片文件后)
python scripts\describe_image.py --clipboard

# 定向提问(OCR / 读数值 / 找元素)
python scripts\describe_image.py --clipboard --prompt "图中有哪些文字?"

# 明确路径或 URL(可多图)
python scripts\describe_image.py C:\path\to\img.png https://example.com/x.jpg

# 文件夹取最新图(桌面/下载/保存目录)
python scripts\describe_image.py --dir "$env:USERPROFILE\Downloads" --list
```

脚本 stdout 就是视觉模型的回答。完整参数:`--minutes`(时间窗,默认 240)、`--max`(张数,默认 5)、`--model` / `--base-url` / `--api-key`(覆盖)、`--no-thinking`(更快)。

## 配置(config.json)

| 字段 | 默认 | 说明 |
|---|---|---|
| `base_url` | `https://api.z.ai/api/coding/paas/v4` | 智谱 OpenAI 兼容端点;bigmodel.cn 用 `https://open.bigmodel.cn/api/coding/paas/v4` |
| `api_key` | 空 | 留空则自动读 DSH 凭据库;否则填智谱 API key(**勿提交**) |
| `model` | `glm-5.3-flash` | GLM-5 系列首个原生多模态模型;追求质量可试 `glm-4.6v`(bigmodel.cn) |
| `thinking` | `true` | 思考模式 |

环境变量 `VISION_BASE_URL` / `VISION_API_KEY` / `VISION_MODEL` 优先于 config.json。

## 边界

二手视觉:主模型看到的是**转述**,细节精度取决于视觉模型的描述质量;每次看图是一次独立 API 调用(有缓存)。模型本身支持图像输入时(如 glm-5.3-flash、glm-4.6v)请直接用原生贴图/读图能力,不需要本技能。

## 致谢

改编自 [kuohii/vision-describe](https://github.com/kuohii/vision-describe)(调用阿里 qwen-vl 的原版,MIT License)。本仓库将视觉后端改为智谱 GLM,并适配 DSH 的凭据库、附件库与技能格式。

## License

[MIT](LICENSE)
