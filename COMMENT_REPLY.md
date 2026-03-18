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

## Meta Dashboard Setup (Full)

### Step 1 — App Permissions

Go to **developers.facebook.com** → your app → **App Review → Permissions and Features**

Request / confirm these permissions are granted:

| Permission | Why |
|-----------|-----|
| `pages_show_list` | List pages you manage |
| `pages_read_engagement` | Read comments on your page |
| `pages_read_user_content` | Read content posted by users on your page |
| `pages_manage_posts` | Post as your page |
| `pages_manage_engagement` | Reply to comments as your page |
| `pages_manage_metadata` | Subscribe to webhooks for your page |
| `read_page_mailboxes` | Read page inbox |
| `pages_messaging` | Send messages via page |
| `page_events` | Read page events |
| `pages_manage_ads` | Manage page ads |
| `pages_utility_messaging` | Utility messaging |
| `publish_video` | Publish video to page |
| `whatsapp_business_management` | WhatsApp business management |
| `whatsapp_business_messaging` | WhatsApp messaging |

---

### Step 2 — Generate Page Access Token

Go to **developers.facebook.com** → **Tools → Graph API Explorer**

1. Top right dropdown — select your **App**
2. Second dropdown — change from **User Token** to **Page** → select **Vocabulary Pro**
3. Click **Generate Access Token** → approve permissions
4. Copy the token
5. Exchange for long-lived token:
   ```
   GET /oauth/access_token
       ?grant_type=fb_exchange_token
       &client_id={app_id}
       &client_secret={app_secret}
       &fb_exchange_token={short_lived_token}
   ```
6. Paste the long-lived page token into `.env` → `FB_USER_ACCESS_TOKEN`
7. Restart server: `./start.sh`

---

### Step 3 — Register Webhook

Go to **developers.facebook.com** → your app → **Webhooks**

1. Click **Add Subscriptions**
2. From the dropdown select **Page** (not User)
3. Fill in:
   - **Callback URL:** `https://vocabulary-auto-social.nanybot.com/webhook/comment`
   - **Verify Token:** `vocab_pro_verify`
4. Click **Verify and Save**
5. After verified — in the subscription list find **feed** → click **Subscribe**

---

### Step 4 — Subscribe Your Page

Go to **developers.facebook.com** → your app → **Webhooks**

1. Find the **Page** object row
2. Click **Test** next to `feed` to confirm webhooks are arriving
3. Check logs: `tail -f logs/comment_reply.log`

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
