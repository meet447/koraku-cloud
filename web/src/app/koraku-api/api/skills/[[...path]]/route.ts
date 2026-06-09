export const runtime = "nodejs";
export const dynamic = "force-dynamic";

import { skills } from "@/lib/koraku-api-routes";

export const GET = skills.GET;
export const PUT = skills.PUT;
export const DELETE = skills.DELETE;
