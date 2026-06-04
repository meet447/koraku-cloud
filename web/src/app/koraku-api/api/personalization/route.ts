export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { personalization } from "@/lib/koraku-api-routes";

export const GET = personalization.GET;
export const PUT = personalization.PUT;
