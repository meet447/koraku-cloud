/** ``sms:`` URI that opens the number in Messages / iMessage on iOS (and SMS elsewhere). */
export function messagesAppUrl(e164: string): string {
  const raw = (e164 || "").trim().replace(/[\s()-]/g, "");
  if (!raw) return "";
  const normalized = raw.startsWith("+") ? raw : `+${raw.replace(/^\+/, "")}`;
  return `sms:${normalized}`;
}
