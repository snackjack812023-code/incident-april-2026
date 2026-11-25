import "server-only";
import { after } from "next/server";
import { createLineMessenger, type LineMessenger } from "./messenger";

/** Sends LINE messages after the HTTP response is finished, so LIFF / admin actions return immediately. */
export function createDeferredLineMessenger(): LineMessenger {
  const inner = createLineMessenger();
  return {
    reply: async (token, messages) => after(() => inner.reply(token, messages)),
    push: async (to, messages) => after(() => inner.push(to, messages)),
    multicast: async (to, messages) => after(() => inner.multicast(to, messages)),
  };
}
