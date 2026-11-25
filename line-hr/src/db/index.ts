import "server-only";
import { drizzle } from "drizzle-orm/node-postgres";
import { Pool } from "pg";
import * as schema from "./schema";
import type { DB } from "./types";

// Reuse one pool per server instance (and across hot reloads in dev).
const globalForDb = globalThis as unknown as { lineHrDb?: DB };

export function getDb(): DB {
  if (!globalForDb.lineHrDb) {
    const connectionString = process.env.DATABASE_URL;
    if (!connectionString) throw new Error("DATABASE_URL is not set");
    const pool = new Pool({ connectionString, max: 5 });
    globalForDb.lineHrDb = drizzle(pool, { schema });
  }
  return globalForDb.lineHrDb;
}

export type { DB };
