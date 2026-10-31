# glm-vision

[简体中文](README.md) | [English](README.en.md)

> **Give GLM-5.3 eyes** — calls its sibling vision model `glm-5.3-flash` to turn images into detailed descriptions or targeted answers.
> Runs anywhere Python does: DeepSeek Harness (DSH), Claude Code, Codex, plain terminal scripts.

## Why it's made for GLM-5.3

- **GLM-5.3 is a text-only flagship**: its API accepts text only — `read_image` is refused, pasting is blocked, and any task involving screenshots/charts/UI images stalls.
- **GLM-5.3-Flash is the first native multimodal model of the GLM-5 series** (image/video/text/file input), on the **same endpoint with the same API key** — and cheap ($0.15/M input tokens, ~1/10 of the flagship).
- A natural pair: **GLM-5.3 stays the brain; glm-vision makes GLM-5.3-Flash the eyes.**

```
GLM-5.3 (brain, text-only) ◄──── text description ────┐
                                                       │
you (screenshot / copy image) → clipboard/file/URL     │
        ↓                                              │
describe_image.py (fetch → base64)                     │
        ↓                                              │
GLM-5.3-Flash (eyes, native multimodal) ───────────────┘
```

## 🚀 Quick Start (any environment)

**1 · Get the files**

```powershell
git clone https://github.com/fei-DEDE/glm-vision
```

**2 · Set your API key once** (any one of)

- Env var: `VISION_API_KEY` (or `ZAI_API_KEY`)
- Fill `api_key` in `config.json` (**never commit it**)
- **DSH users: nothing to do** — the key saved in Settings → Models is picked up automatically

**3 · Talk / run**

| You want | You say / do | What happens |
|---|---|---|
| Look at your screen | `Win+Shift+S`, then **"look at my screenshot"** | Reads the clipboard image |
| A web image | Right-click → Copy image, **"check the clipboard"** | Same |
| A fresh download | **"look at the newest image in Downloads"** | Scans the folder |
| Extract text (OCR) | **"transcribe all text in this image"** | Targeted vision query |
| An error dialog | Screenshot + **"what does this error mean?"** | Targeted analysis |

## Per-environment setup

- **DeepSeek Harness (DSH)**: clone into `~\.dsh\skills\glm-vision` — auto-discovered, zero config (auto-reads the DSH credential store; also supports scanning the DSH attachment store via `--find-latest`). Note DSH blocks pasting for text-only models — the clipboard entry bypasses it.
- **Claude Code / other agents**: copy `SKILL.md`, `config.json`, `scripts/` into your skills dir (e.g. `~/.claude/skills/glm-vision/`) and set the key.
- **Plain CLI**: no agent required (see below).

## 🛠 CLI usage

```powershell
python scripts\describe_image.py --clipboard
python scripts\describe_image.py --clipboard --prompt "What text is in this image?"
python scripts\describe_image.py C:\path\to\img.png https://example.com/x.jpg
python scripts\describe_image.py --dir "$env:USERPROFILE\Downloads" --list
```

stdout is GLM-5.3-Flash's answer. More: `--minutes` (window, default 240), `--max` (count, default 5), `--model` / `--base-url` / `--api-key` overrides, `--no-thinking`.

## ✨ Features

Four image entry points (clipboard / path / URL / folder / DSH store) · result cache (1h) · auto-resize over Zhipu limits (2000×2000, 4.5MB) · magic-byte detection · Windows file-lock fallbacks · 429/5xx retries.

## ⚙️ config.json

| Field | Default | Notes |
|---|---|---|
| `base_url` | `https://api.z.ai/api/coding/paas/v4` | bigmodel.cn → `https://open.bigmodel.cn/api/coding/paas/v4` |
| `api_key` | empty | Empty → DSH credential store, else `VISION_API_KEY`/`ZAI_API_KEY` |
| `model` | `glm-5.3-flash` | First native multimodal GLM-5 model; `glm-4.6v` (bigmodel.cn) for max quality |
| `thinking` | `true` | Thinking mode |

## ❓ FAQ

**My client blocks pasting images.** Many clients gate pasting by model capability (DSH does). Use the **clipboard entry**: screenshot or copy the image, then run `--clipboard` — no upload channel involved.

**Only for GLM-5.3?** Built for it, but any text-only model (e.g. DeepSeek-R1) can borrow the same eyes. If your model already accepts images (glm-5.3-flash, glm-4.6v), use native pasting instead.

## 🙏 Credits

Adapted from [kuohii/vision-describe](https://github.com/kuohii/vision-describe) (Aliyun qwen-vl original, MIT). This fork switches the vision backend to Zhipu GLM and adapts DSH's credential/attachment stores and skill format.

## License

[MIT](LICENSE)
