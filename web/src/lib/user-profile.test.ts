import { describe, expect, it } from "vitest";
import type { User } from "@supabase/supabase-js";
import { getUserAvatarUrl, getUserDisplayName, getUserInitials } from "./user-profile";

function user(partial: Partial<User>): User {
  return partial as User;
}

describe("user-profile", () => {
  it("reads Google-style metadata", () => {
    const u = user({
      email: "a@b.com",
      user_metadata: {
        full_name: "Jane Doe",
        avatar_url: "https://lh3.googleusercontent.com/a/photo",
        picture: "https://lh3.googleusercontent.com/a/fallback",
      },
    });
    expect(getUserDisplayName(u)).toBe("Jane Doe");
    expect(getUserAvatarUrl(u)).toBe("https://lh3.googleusercontent.com/a/photo");
    expect(getUserInitials(u)).toBe("JD");
  });

  it("reads GitHub avatar_url", () => {
    const u = user({
      email: "dev@github.com",
      user_metadata: {
        name: "octocat",
        avatar_url: "https://avatars.githubusercontent.com/u/1",
      },
    });
    expect(getUserDisplayName(u)).toBe("octocat");
    expect(getUserAvatarUrl(u)).toBe("https://avatars.githubusercontent.com/u/1");
  });
});
