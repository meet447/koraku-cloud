export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { admin } from "@/lib/koraku-api-routes";

export const GET = admin.GET;
export const POST = admin.POST;
export const PATCH = admin.PATCH;
