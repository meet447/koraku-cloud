"use client";

import { useState } from "react";
import clsx from "clsx";
import type { User } from "@supabase/supabase-js";
import { getUserAvatarUrl, getUserInitials } from "@/lib/user-profile";

export function UserAvatar({
  user,
  size = 32,
  className,
}: {
  user: User;
  size?: number;
  className?: string;
}) {
  const [broken, setBroken] = useState(false);
  const avatarUrl = getUserAvatarUrl(user);
  const initials = getUserInitials(user);
  const px = `${size}px`;

  if (avatarUrl && !broken) {
    return (
      /* eslint-disable-next-line @next/next/no-img-element */
      <img
        src={avatarUrl}
        alt=""
        width={size}
        height={size}
        referrerPolicy="no-referrer"
        onError={() => setBroken(true)}
        className={clsx(
          "shrink-0 rounded-full object-cover ring-1 ring-neutral-200/80",
          className,
        )}
        style={{ width: px, height: px }}
      />
    );
  }

  return (
    <span
      aria-hidden
      className={clsx(
        "flex shrink-0 items-center justify-center rounded-full bg-neutral-200 font-bold text-neutral-600 ring-1 ring-neutral-200/80",
        size >= 36 ? "text-xs" : "text-[10px]",
        className,
      )}
      style={{ width: px, height: px }}
    >
      {initials}
    </span>
  );
}
