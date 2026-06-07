export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import {
  korakuPersonalizationGetCached,
  korakuPersonalizationPut,
} from "@/lib/koraku-bff-cache";

export const GET = korakuPersonalizationGetCached;
export const PUT = korakuPersonalizationPut;
