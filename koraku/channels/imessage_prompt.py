"""System prompt appendix for iMessage / SMS turns."""


def imessage_system_appendix(imessage_workspace_root: str | None = None) -> str:
    workspace_line = ""
    if (imessage_workspace_root or "").strip():
        workspace_line = (
            f"- **iMessage workspace** (Blaxel): use **Write** / **Edit** for files the user should get "
            f"(e.g. `todo.txt`, `notes.md`). Paths are relative to your dedicated iMessage folder; "
            f"Koraku sends them as attachments after your reply.\n"
        )
    return f"""
## iMessage / SMS (this turn)
- The user is texting you from iMessage or SMS. Koraku **automatically** sends a bubble before each tool (with typing between steps).
- Do **not** repeat tool status in **ChannelSend** — use **ChannelSend** only for extra context the user needs mid-turn.
- Your **final** assistant message should be a **short wrap-up** (findings / answer only), not a repeat of steps already messaged.
- Users may send **voice notes** (transcribed automatically) or text. Reply naturally to what they said.
- Plain text only — no markdown headers, tables, or code fences.
- Each bubble under ~400 characters.
{workspace_line}- You have full tools: **WebSearch**, **MemorySearch**, **ComposioRun**, and workspace tools when relevant.
"""
