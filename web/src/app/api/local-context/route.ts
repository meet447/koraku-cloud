import {
  clientIpFromRequest,
  resolveLocalContextPlace,
} from "@/lib/local-context-server";

export const runtime = "nodejs";

export async function GET(request: Request) {
  const clientIp = clientIpFromRequest(request);
  const place = await resolveLocalContextPlace(clientIp);
  if (!place) {
    return Response.json({ error: "unavailable" }, { status: 503 });
  }
  return Response.json(place);
}
