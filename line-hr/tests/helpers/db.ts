import { PGlite } from "@electric-sql/pglite";
import { drizzle } from "drizzle-orm/pglite";
import { migrate } from "drizzle-orm/pglite/migrator";
import * as schema from "@/db/schema";
import type { DB } from "@/db/types";
import type { LineMessage, LineMessenger } from "@/lib/line/messenger";

/** A fresh in-memory Postgres (PGlite) with the real migrations applied. */
export async function createTestDb(): Promise<{ db: DB; close: () => Promise<void> }> {
  const client = new PGlite();
  const db = drizzle(client, { schema });
  await migrate(db, { migrationsFolder: "drizzle" });
  return { db, close: () => client.close() };
}

export type SentMessage = { op: "reply" | "push" | "multicast"; to: string | string[]; messages: LineMessage[] };

export function createFakeMessenger(): LineMessenger & { sent: SentMessage[] } {
  const sent: SentMessage[] = [];
  return {
    sent,
    reply: async (to, messages) => void sent.push({ op: "reply", to, messages }),
    push: async (to, messages) => void sent.push({ op: "push", to, messages }),
    multicast: async (to, messages) => void sent.push({ op: "multicast", to, messages }),
  };
}
