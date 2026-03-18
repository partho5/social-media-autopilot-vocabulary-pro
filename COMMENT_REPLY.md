# FB Comment Auto-Reply

Standalone Flask server. Listens for Facebook comment webhooks, calls OpenAI GPT-4o mini, posts reply.

---

## Start

```bash
./start_comment_reply.sh
curl http://localhost:8003/health
```

## Stop

```bash
kill $(cat comment_reply.pid)
```

---

## Config

All in `.env`:

| Key | Required | Notes |
|-----|----------|-------|
| `OPENAI_API_KEY` | yes | already set |
| `FB_APP_SECRET` | yes | used for webhook validation, already set |
| `FB_VERIFY_TOKEN` | yes | set to `vocab_pro_verify`, used during Meta registration |
| `FB_REPLY_PORT` | no | default `8003` |

Behaviour defaults — edit in `modules/fb_comment_auto_reply.py`:

```python
DEFAULT_SYSTEM_PROMPT = "You are a helpful and friendly assistant..."
DEFAULT_INCLUDE_PARENT = True   # include parent comment in context
DEFAULT_INCLUDE_POST   = False  # include post content in context
```

---

## Register Webhook (Meta Dashboard)

1. Run ngrok: `ngrok http 8003` → copy the `https://xxxx.ngrok-free.app` URL
2. Go to **developers.facebook.com** → your app → **Webhooks**
3. Add subscription → **Page**
   - Callback URL: `https://xxxx.ngrok-free.app/webhook/comment`
   - Verify Token: `vocab_pro_verify`
   - Field: `feed`
4. Click **Verify and Save**

---

## Logs

```bash
tail -f logs/comment_reply.log
```

Successful reply looks like:
```
[INFO] Processing comment: 123_456
[INFO] Comment text: Nice post!
[INFO] Generated reply: Thank you so much!...
[INFO] Reply posted successfully: 123_789
```

---

## Notes

- Only replies to **new** comments from the moment webhook is registered. Not past comments.
- Runs independently from main server (`./start.sh`). Both can run at the same time.
- Token is read from `data/fb_tokens.json` — always fresh, auto-refreshed by main project.
