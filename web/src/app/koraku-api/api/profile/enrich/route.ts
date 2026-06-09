import type { NextRequest } from "next/server";
import { profileEnrich } from "@/lib/koraku-api-routes";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 120;

export async function POST(req: NextRequest) {
  return profileEnrich.POST(req);
}
