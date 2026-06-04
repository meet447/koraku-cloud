export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { korakuRunStatusGet } from "@/lib/koraku-api-routes";

export const GET = korakuRunStatusGet;
