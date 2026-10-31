# glm-vision

[简体中文](README.md) | [English](README.en.md)

> Give text-only models "eyes" — calls the Zhipu GLM vision model (`glm-5.3-flash`) to turn images into detailed descriptions or targeted answers.
> Built for **DeepSeek Harness (DSH)**; works with any AI coding agent that can run scripts (Claude Code, Codex, ...).

## 🚀 Quick Start (3 steps)

**1 · Install** (one time)

```powershell
git clone https://github.com/fei-DEDE/glm-vision "$env:USERPROFILE\.dsh\skills\glm-vision"
```

No git? Grab `glm-vision-skill-vX.Y.Z.zip` from [Releases](https://github.com/fei-DEDE/glm-vision/releases), extract, and drop the `glm-vision` folder into `C:\Users\<you>\.dsh\skills\`.

**2 · Make sure you have a Zhipu API key**

Configure the z.ai provider once in DSH **Settings → Models** and save the key — the skill reads it automatically. Get a key at [z.ai](https://z.ai).

**3 · Just talk to your AI** (that's all)

| You want | You say / do | What happens |
|---|---|---|
| Look at your screen | Screenshot with `Win+Shift+S`, then say **"look at my screenshot"** | Reads the clipboard image |
| Look at a web image | Right-click → Copy image, say **"check the clipboard"** | Same |
| Check a fresh download | Say **"look at the newest image in my Downloads"** | Scans the folder |
| Extract text (OCR) | Say **"transcribe all text in this image"** | Targeted vision query |
| Analyze an error dialog | Screenshot + **"what does this error mean?"** | Targeted analysis |
| A specific file | Say **"look at C:\pics\photo.png"** | Reads that path |

> 💡 Text-only models can't paste images in DSH ("current model does not support images") — that's exactly why this skill exists. The **clipboard** entry point bypasses it completely.

## ✨ Features

- **Four image entry points**: clipboard (`--clipboard`, recommended when pasting is blocked), explicit path/URL, newest file in a folder (`--dir`), DSH attachment store (`--find-latest`)
- **Zero config**: API key auto-read from the DSH credential store (`ZAI_API_KEY` in `~/.dsh/.credentials.yaml`); env vars or `config.json` also work
- **Result cache**: identical image + question reused for 1 hour
- **Auto-resize**: images over Zhipu limits (2000×2000 / 4.5MB) are shrunk with Pillow
- **Robust reads**: magic-byte format detection, Windows file-lock fallbacks, 429/5xx retries

## 🔍 How it works

```
you (screenshot / copied image) → clipboard / file
        ↓
describe_image.py (fetch → base64 → attach prompt)
        ↓
Zhipu API · glm-5.3-flash (native multimodal, same key & endpoint)
        ↓
text description → stdout → main model context → answer
```

Text-only models (e.g. glm-5.3) accept text only; `read_image` is refused and pasting is blocked client-side. A skill cannot change a model's modalities, but it lets the agent **borrow eyes**: a script asks a vision model, and the description text enters the main model's context.

## 📦 Install details

- **DSH**: clone or copy into `~\.dsh\skills\glm-vision\` — auto-discovered, no restart needed.
- **Other agents**: copy `SKILL.md`, `config.json`, `scripts/` into your skills dir (e.g. `~/.claude/skills/glm-vision/`) and set `VISION_API_KEY` (or fill `config.json` — never commit it).

## 🛠 CLI usage

```powershell
python scripts\describe_image.py --clipboard
python scripts\describe_image.py --clipboard --prompt "What text is in this image?"
python scripts\describe_image.py C:\path\to\img.png https://example.com/x.jpg
python scripts\describe_image.py --dir "$env:USERPROFILE\Downloads" --list
```

stdout is the vision model's answer. More: `--minutes` (window, default 240), `--max` (count, default 5), `--model` / `--base-url` / `--api-key` overrides, `--no-thinking`.

## ⚙️ config.json

| Field | Default | Notes |
|---|---|---|
| `base_url` | `https://api.z.ai/api/coding/paas/v4` | Zhipu OpenAI-compatible endpoint; bigmodel.cn → `https://open.bigmodel.cn/api/coding/paas/v4` |
| `api_key` | empty | Empty = auto-read DSH credential store; otherwise your key (**do not commit**) |
| `model` | `glm-5.3-flash` | First native multimodal GLM-5 model; try `glm-4.6v` (bigmodel.cn) for max quality |
| `thinking` | `true` | Thinking mode |

Env vars `VISION_BASE_URL` / `VISION_API_KEY` / `VISION_MODEL` override config.json.

## 🙏 Credits

Adapted from [kuohii/vision-describe](https://github.com/kuohii/vision-describe) (original targets Aliyun qwen-vl, MIT License). This fork switches the vision backend to Zhipu GLM and adapts it to DSH's credential store, attachment store, and skill format.

## License

[MIT](LICENSE)
