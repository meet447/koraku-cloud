# SendBlue + Koraku (iMessage)

Koraku uses SendBlue for inbound iMessage/SMS and outbound replies. The Python API handles webhooks on **`POST /sendblue/webhook`** (port **8000**), not the Next.js app.

Official SendBlue docs: https://docs.sendblue.com/

## Free Tier (your plan)

- **Shared line** — one SendBlue number for all free accounts (`sendblue lines`).
- **Up to 10 verified contacts** — each person you reply to must be a contact.
- **They must text your SendBlue number first** — then you can reply (inbound + replies only; no cold outbound).
- Koraku must also have the same number in **External** (`koraku_phone_link`).

If outbound fails with *"contact must be verified"*, add the contact in SendBlue **before** expecting Koraku to reply.

## 1. Credentials (CLI)

```bash
npm install -g @sendblue/cli
sendblue login
# Email: meet.sonawane2015@gmail.com → enter OTP from email

sendblue show-keys    # SENDBLUE_API_KEY, SENDBLUE_API_SECRET
sendblue lines        # SENDBLUE_FROM_NUMBER
```

Put keys in repo-root **`.env`** (API reads this):

```bash
SENDBLUE_API_KEY=…
SENDBLUE_API_SECRET=…
SENDBLUE_FROM_NUMBER=+1…
# Optional override (default is official host):
# SENDBLUE_API_BASE=https://api.sendblue.co/api
```

Optional in **`web/.env.local`** for the External tab label:

```bash
NEXT_PUBLIC_SENDBLUE_FROM_NUMBER=+1…
KORAKU_BACKEND_URL=http://127.0.0.1:8000
```

Restart **`python main.py`** and **`npm run dev`** after changing env.

## 2. Verify your phone in SendBlue

Use your **real** iMessage number (E.164, e.g. `+91…` or `+1…`). Do not use example numbers like `+14155551234`.

```bash
sendblue add-contact +1YOUR_REAL_NUMBER
```

Then **text your SendBlue line once** from that phone (required on Free Tier before any API reply).

## 3. Link the same number in Koraku

1. Open Koraku → **External**.
2. Enter the **same** number you text from.
3. Complete SMS verification (or reply `KORAKU-######` to the Koraku line).

## 4. Webhook (local or production)

SendBlue must POST inbound messages to your **public** Koraku API URL.

**Local (ngrok):**

```bash
# API running on :8000
./scripts/ngrok-sendblue.sh
# Webhook URL:
#   https://<ngrok-host>/sendblue/webhook
```

**CLI:**

```bash
sendblue webhooks set-receive https://<public-host>/sendblue/webhook
```

If you set a signing secret in SendBlue, add the same value to `.env` as `SENDBLUE_WEBHOOK_SECRET`.

## 5. Test

1. From your verified phone, iMessage the Koraku/SendBlue line: `hello`
2. API logs should show:
   - `sendblue inbound from +1…`
   - `sendblue inbound linked user …`
3. You should get an iMessage reply from Koraku.

## Troubleshooting

| Symptom | Fix |
|--------|-----|
| No log line on text | Webhook URL wrong, ngrok down, or API not on :8000 |
| `no koraku_phone_link` | Re-link on External with the exact number SendBlue sends |
| `contact must be verified` | `sendblue add-contact` + text the line first |
| 401 on webhook | Match `SENDBLUE_WEBHOOK_SECRET` with SendBlue dashboard |

Inspect requests: ngrok UI http://127.0.0.1:4040
