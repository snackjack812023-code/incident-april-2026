import type { webhook } from "@line/bot-sdk";
import { after } from "next/server";
import { getDb } from "@/db";
import { serverEnv } from "@/lib/env";
import { createLineMessenger } from "@/lib/line/messenger";
import { verifyLineSignature } from "@/lib/line/signature";
import { handleWebhookEvents } from "@/lib/line/webhook-handler";

/** LINE Messaging API webhook. Set the URL to https://<your-app>/api/line/webhook in LINE Developers Console. */
export async function POST(req: Request) {
  const { lineChannelSecret } = serverEnv();
  if (!lineChannelSecret) return new Response("LINE_CHANNEL_SECRET is not set", { status: 500 });

  // The signature covers the raw body, so read it as text before parsing.
  const rawBody = await req.text();
  if (!verifyLineSignature(rawBody, req.headers.get("x-line-signature") ?? "", lineChannelSecret)) {
    return new Response("Invalid signature", { status: 401 });
  }

  let body: webhook.CallbackRequest;
  try {
    body = JSON.parse(rawBody);
  } catch {
    return new Response("Invalid JSON", { status: 400 });
  }

  // Acknowledge immediately; handle events after the response (reply tokens stay valid for a while).
  const events = Array.isArray(body.events) ? body.events : [];
  if (events.length) {
    after(() => handleWebhookEvents({ db: getDb(), line: createLineMessenger() }, events));
  }
  return Response.json({ ok: true });
}
