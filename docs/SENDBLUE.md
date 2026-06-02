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

**Local API reload:** If you see typing but no reply, disable hot reload so webhook work is not killed mid-turn:

```bash
UVICORN_RELOAD=false python main.py
```

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

Set a signing secret in SendBlue and add the same value to `.env` as `SENDBLUE_WEBHOOK_SECRET`. When SendBlue credentials are configured, the API **rejects** webhooks if this secret is missing or wrong.

## 5. Test

1. From your verified phone, iMessage the Koraku/SendBlue line: `hello`
2. API logs should show:
   - `sendblue inbound from +1…`
   - `sendblue inbound linked user …`
3. You should get an iMessage reply from Koraku.

## Voice notes

Users can send **iMessage voice memos** instead of typing. Koraku downloads the audio from SendBlue, transcribes it with **Whisper** (Fireworks `FIREWORKS_API_KEY` by default, or `OPENAI_API_KEY`), and runs the agent on the transcript.

Disable with `IMESSAGE_VOICE_TRANSCRIPTION_ENABLED=false`. Optional: `VOICE_TRANSCRIPTION_BASE_URL`, `VOICE_TRANSCRIPTION_MODEL` (default `whisper-large-v3` on Fireworks).

## Progress bubbles

During an iMessage turn, Koraku automatically sends a short bubble **before each tool** (e.g. “Searching the web…”, “Editing notes.md…”), with the typing indicator between steps. The **final** model message is a brief wrap-up only — not a repeat of those steps.

## File attachments

When the agent **Write**s or **Edit**s a file during an iMessage turn, Koraku uploads it to SendBlue and sends it as an attachment (📎 filename) after the text reply. Limits: 8 files per turn, 20 MB each; secrets like `.env` are skipped.

## Typing indicator lingers after a reply

iMessage keeps the “…” bubble visible for a few seconds after each typing signal (SendBlue has no “stop typing” API). Koraku pauses typing refresh **before** each outbound bubble, then **resumes** it while tools are still running (so you see “…” between interim `ChannelSend` messages and the final reply).

If typing still hangs too long, check SendBlue **Settings** for **auto typing on inbound** — turn it off when Koraku manages typing during agent turns (otherwise you get a second indicator from SendBlue).

## File tools in iMessage turns

When `BLAXEL_CLOUD_SANDBOX_ENABLED=true`, each iMessage thread gets its own folder on the user's Blaxel VM:

`{workdir}/koraku/users/{user}/imessage/{thread_id}/`

Koraku provisions that sandbox **at the start of each iMessage turn** (not lazy-only), so **Write** / **Edit** work reliably and files can be sent as iMessage attachments. Web chat sessions stay under `.../sessions/{session_id}/` and do not share that folder.

## Troubleshooting

| Symptom | Fix |
|--------|-----|
| No log line on text | Webhook URL wrong, ngrok down, or API not on :8000 |
| `no koraku_phone_link` | Re-link on External with the exact number SendBlue sends |
| `contact must be verified` | `sendblue add-contact` + text the line first |
| 401 on webhook | Match `SENDBLUE_WEBHOOK_SECRET` with SendBlue dashboard |

Inspect requests: ngrok UI http://127.0.0.1:4040
