import type { PgDatabase, PgQueryResultHKT } from "drizzle-orm/pg-core";
import type * as schema from "./schema";

/** Works for both the node-postgres pool (app) and PGlite (tests), and for transactions. */
export type DB = PgDatabase<PgQueryResultHKT, typeof schema>;
