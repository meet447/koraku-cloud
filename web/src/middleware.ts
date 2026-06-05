import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { isSupabaseConfigured } from "@/lib/supabase/is-configured";
import { withSupabaseAuth } from "@/lib/supabase/middleware";

export async function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  // Only run Supabase auth verification for protected routes (e.g. starting with /app or /api or /koraku-api)
  const isProtectedRoute =
    pathname.startsWith("/app") ||
    pathname.startsWith("/api") ||
    pathname.startsWith("/koraku-api");

  if (!isProtectedRoute) {
    return NextResponse.next();
  }

  const { response, userId } = await withSupabaseAuth(request);

  if (pathname.startsWith("/app") && !isSupabaseConfigured()) {
    return NextResponse.json(
      { error: "Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY." },
      { status: 503 },
    );
  }

  if (pathname.startsWith("/app") && !userId) {
    const signIn = new URL("/sign-in", request.url);
    signIn.searchParams.set("next", `${pathname}${search}`);
    return NextResponse.redirect(signIn);
  }

  return response;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
