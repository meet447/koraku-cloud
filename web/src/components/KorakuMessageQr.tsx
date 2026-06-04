"use client";

import { QRCodeSVG } from "qrcode.react";
import { messagesAppUrl } from "@/lib/messages-app-url";

type KorakuMessageQrProps = {
  phoneE164: string;
  size?: number;
  className?: string;
};

/** QR encodes a ``sms:`` link so scanning opens the thread in Messages / iMessage. */
export function KorakuMessageQr({ phoneE164, size = 120, className }: KorakuMessageQrProps) {
  const href = messagesAppUrl(phoneE164);
  if (!href) return null;

  return (
    <div className={className}>
      <a
        href={href}
        className="inline-flex flex-col items-center gap-2 rounded-xl bg-white p-3 ring-1 ring-neutral-200/80 transition hover:ring-neutral-300"
        aria-label={`Open ${phoneE164} in Messages`}
      >
        <QRCodeSVG
          value={href}
          size={size}
          level="M"
          marginSize={2}
          bgColor="#ffffff"
          fgColor="#171717"
          title={`Message ${phoneE164}`}
        />
        <span className="text-[10px] font-semibold uppercase tracking-wide text-koraku-muted">
          Scan for iMessage
        </span>
      </a>
    </div>
  );
}
