export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 300;

import { automations } from "@/lib/koraku-api-routes";

export const GET = automations.GET;
export const POST = automations.POST;
export const PATCH = automations.PATCH;
export const DELETE = automations.DELETE;
