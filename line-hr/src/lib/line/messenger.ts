import { HTTPFetchError, messagingApi } from "@line/bot-sdk";
import { serverEnv } from "../env";

export type LineMessage = messagingApi.Message;

/** Outgoing LINE messages. Sending is best-effort: failures are logged and never break the caller's action. */
export interface LineMessenger {
  reply(replyToken: string, messages: LineMessage[]): Promise<void>;
  push(to: string, messages: LineMessage[]): Promise<void>;
  multicast(to: string[], messages: LineMessage[]): Promise<void>;
}

const MULTICAST_LIMIT = 500;

function logError(op: string, err: unknown) {
  if (err instanceof HTTPFetchError) {
    console.error(`[line] ${op} failed: ${err.status} ${err.body}`);
  } else {
    console.error(`[line] ${op} failed`, err);
  }
}

export function createLineMessenger(): LineMessenger {
  const env = serverEnv();
  if (!env.lineChannelAccessToken) {
    // Local development without a LINE channel: print what would have been sent.
    const log = (op: string, target: string, messages: LineMessage[]) =>
      console.info(`[line:dry-run] ${op} → ${target}`, JSON.stringify(messages).slice(0, 500));
    return {
      reply: async (token, messages) => log("reply", token, messages),
      push: async (to, messages) => log("push", to, messages),
      multicast: async (to, messages) => log("multicast", to.join(","), messages),
    };
  }

  const client = new messagingApi.MessagingApiClient({
    channelAccessToken: env.lineChannelAccessToken,
    ...(env.lineApiBaseUrl ? { baseURL: env.lineApiBaseUrl } : {}),
  });

  return {
    async reply(replyToken, messages) {
      try {
        await client.replyMessage({ replyToken, messages });
      } catch (err) {
        logError("reply", err);
      }
    },
    async push(to, messages) {
      try {
        await client.pushMessage({ to, messages });
      } catch (err) {
        logError("push", err);
      }
    },
    async multicast(to, messages) {
      const recipients = [...new Set(to)];
      for (let i = 0; i < recipients.length; i += MULTICAST_LIMIT) {
        try {
          await client.multicast({ to: recipients.slice(i, i + MULTICAST_LIMIT), messages });
        } catch (err) {
          logError("multicast", err);
        }
      }
    },
  };
}
