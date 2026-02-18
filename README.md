# Vocabulary Pro – Automated Facebook Word-of-the-Day

An automated system that posts daily English vocabulary content to a Facebook Page.
Each post contains a Bengali educational story, AI-generated image, and English example sentences —
published automatically at scheduled times without any manual intervention.

---

## Features

- **Sequential word selection** — works through a word list (IELTS/GRE vocabulary) in order, wraps around when exhausted, state persists across restarts
- **Bengali story generation** — GPT-4o mini or Claude Sonnet writes a natural, conversational Bengali story about তমা using the target word 2–3 times in different contexts
- **English examples** — 2 English example sentences appended to every post
- **Unicode bold** — `**word**` markers from the LLM are converted to Unicode Mathematical Bold (𝐰𝐨𝐫𝐝) so they render bold on Facebook without Markdown support
- **AI image generation** — Replicate (SDXL-Lightning 4-step, fast) generates a scene matching the story's emotion and action
- **Image compositing** — 1080×1350 canvas (4:5 Facebook ratio), Bengali "আজকের ওয়ার্ড:" header at top, AI image anchored to bottom edge
- **Automatic Facebook token management** — short-lived token → long-lived (60 days) → never-expiring page token, auto-refreshed before expiry; zero manual token work after initial setup
- **Scheduled posting** — APScheduler fires at 08:00, 12:00, 18:00, 20:00 (Asia/Dhaka) daily
- **FastAPI webhook** — `POST /webhook/trigger` for manual or external cron triggers
- **Single-command deploy** — `./start.sh` stops old processes and starts fresh ones
- **Rotating logs** — separate logs for server and scheduler, auto-rotated at 5 MB

---

## Project Structure

```
.
├── main.py                  # FastAPI app (webhook server)
├── scheduler.py             # APScheduler (daily auto-posting)
├── start.sh                 # VPS start/restart script
├── requirements.txt
├── .env.example
├── modules/
│   ├── config.py            # All env vars loaded here
│   ├── word_manager.py      # Sequential word selection + state
│   ├── openai_client.py     # GPT-4o mini + Claude text generation
│   ├── replicate_client.py  # SDXL-Lightning image generation
│   ├── image_processor.py   # PIL canvas compositing
│   ├── facebook_client.py   # Facebook Graph API + token lifecycle
│   └── prompts.py           # LLM prompt templates
├── data/                    # Runtime data (gitignored)
│   ├── words.txt            # One English word per line
│   ├── hashtags.txt         # Hashtags appended to every post
│   ├── state.json           # Current word index (auto-managed)
│   └── fb_tokens.json       # Facebook tokens (auto-managed)
├── fonts/                   # NotoSansBengali.ttf (gitignored)
├── output/                  # Generated post images (gitignored)
└── logs/                    # Application logs (gitignored)
```

---

## Prerequisites

- Python 3.11+
- VPS or local machine with outbound HTTPS access
- Accounts / API keys for:
  - [OpenAI](https://platform.openai.com/) — GPT-4o mini (text generation + image prompts)
  - [Anthropic](https://console.anthropic.com/) *(optional)* — Claude Sonnet (alternative text generator)
  - [Replicate](https://replicate.com/) — SDXL-Lightning image generation
  - [Facebook Developer App](https://developers.facebook.com/) — Graph API posting

---

## Clone & Install

```bash
git clone https://github.com/partho5/social-media-autopilot-vocabulary-pro.git
cd social-media-autopilot-vocabulary-pro

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Bengali font

Download NotoSansBengali and place it at `fonts/NotoSansBengali.ttf`:

```bash
mkdir -p fonts
curl -L "https://github.com/google/fonts/raw/main/ofl/notosansbengali/NotoSansBengali%5Bwdth%2Cwght%5D.ttf" \
     -o fonts/NotoSansBengali.ttf
```

---

## Configuration

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `ANTHROPIC_API_KEY` | No | Anthropic key (only if using Claude) |
| `TEXT_GENERATION_PROVIDER` | No | `gpt` (default) or `claude` |
| `REPLICATE_API_TOKEN` | Yes | Replicate API token |
| `FB_APP_ID` | Yes | Facebook App ID |
| `FB_APP_SECRET` | Yes | Facebook App Secret |
| `FB_USER_ACCESS_TOKEN` | Yes | Short-lived User Access Token (one-time setup) |
| `FB_PAGE_ID` | Yes | Facebook Page ID to post to |
| `WEBHOOK_SECRET` | No | Optional secret header for the webhook endpoint |
| `LOG_LEVEL` | No | `DEBUG` / `INFO` (default) / `WARNING` / `ERROR` |
| `PORT` | No | FastAPI port (default `8000`) |

### Switching text provider

Change one variable in `.env`:

```env
TEXT_GENERATION_PROVIDER=claude   # or gpt
```

---

## Data Files

Create the `data/` directory and add your word list and hashtags:

```bash
mkdir -p data

# One word per line
cat > data/words.txt <<'EOF'
ephemeral
eloquent
enervate
...
EOF

# Hashtags appended to every post (space or newline separated)
cat > data/hashtags.txt <<'EOF'
#EnglishWithBengali #WordOfTheDay #IELTS #Vocabulary
EOF
```

`state.json` and `fb_tokens.json` are created automatically on first run.

---

## Facebook Token Setup

You only need to do this **once**. The system handles all renewals automatically after that.

1. Go to [Facebook Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app, grant `pages_manage_posts` and `pages_read_engagement` permissions
3. Copy the generated **User Access Token** (short-lived is fine)
4. Paste it as `FB_USER_ACCESS_TOKEN` in `.env`

On first trigger the system will:
- Exchange it for a 60-day long-lived user token
- Derive a never-expiring Page Access Token
- Store both in `data/fb_tokens.json`
- Auto-refresh the user token when fewer than 10 days remain

---

## Posting Schedule

The scheduler (`scheduler.py`) fires daily at these times in **Asia/Dhaka** timezone:

| Slot | Dhaka time |
|---|---|
| Morning | 08:00 |
| Noon | 12:00 |
| Evening | 18:00 |
| Night | 20:00 |

Edit `POSTING_TIMES` in `scheduler.py` to change the slots.

---

## Deploy & Run

```bash
chmod +x start.sh
./start.sh
```

This will:
1. Stop any previously running FastAPI server and scheduler
2. Start `uvicorn` (FastAPI) in the background → `logs/startup.log`
3. Wait 3 seconds for the server to be ready
4. Start the APScheduler process in the background → `logs/scheduler.log`

**Restart** (same command):

```bash
./start.sh
```

### Manual trigger

```bash
# Without secret
curl -X POST http://localhost:8000/webhook/trigger

# With secret
curl -X POST http://localhost:8000/webhook/trigger \
     -H "X-Webhook-Secret: your_secret"
```

### Health & status

```bash
curl http://localhost:8000/health
curl http://localhost:8000/status
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/webhook/trigger` | Run the full posting workflow |
| `GET` | `/health` | Liveness check |
| `GET` | `/status` | Current word index and state info |

---

## Workflow

Each trigger runs these steps in order. Any failure aborts with a logged error.

```
1. Select next word from words.txt (sequential, wraps around)
2. Generate Bengali story (GPT-4o mini or Claude Sonnet)
3. Generate image prompt (GPT-4o mini, based on the story)
4. Generate image (Replicate – SDXL-Lightning 4-step, 1024×1024)
5. Composite image onto 1080×1350 canvas with Bengali header
6. Validate / refresh Facebook token if needed
7. Post to Facebook page (text + image + hashtags)
8. Update state.json with new word index
```

---

## Logs

| File | Contents |
|---|---|
| `logs/startup.log` | FastAPI / uvicorn output |
| `logs/scheduler.log` | Scheduler fire events and results |
| `logs/vocab_pro.log` | Full workflow logs (5 MB rotating, 5 backups) |

---

## Extending

The codebase is intentionally modular. To add a new module:

1. Create `modules/your_module.py`
2. Import config values from `modules/config.py`
3. Call it from `_run_workflow()` in `main.py`

The `selectNextWord()` function in `modules/word_manager.py` is designed as a stub — replace the internals with any selection logic (random, weighted, spaced repetition) without changing the callers.
