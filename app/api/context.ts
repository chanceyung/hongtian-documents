import type { FetchCreateContextFnOptions } from "@trpc/server/adapters/fetch";
import type { User } from "@db/schema";
import { env } from "./lib/env";
import { getDb } from "./queries/connection";
import { eq } from "drizzle-orm";
import { users } from "@db/schema";

const FALLBACK_USER: User = {
  id: env.desktopUserId,
  name: "桌面用户",
  email: "desktop@hongtian.ai",
  role: "admin",
  createdAt: new Date(),
  updatedAt: new Date(),
};

export type TrpcContext = {
  req: Request;
  resHeaders: Headers;
  user: User;
};

export async function createContext(
  opts: FetchCreateContextFnOptions,
): Promise<TrpcContext> {
  let user: User | undefined;

  if (env.isDesktop) {
    try {
      const db = await getDb();
      const rows = await db.select().from(users).where(eq(users.id, env.desktopUserId)).limit(1);
      if (rows.length > 0) user = rows[0];
      else {
        await db.insert(users).values({ id: env.desktopUserId, name: "桌面用户", role: "admin" });
        const created = await db.select().from(users).where(eq(users.id, env.desktopUserId)).limit(1);
        if (created.length > 0) user = created[0];
      }
    } catch (err) {
      console.error("[Context] Failed to init desktop user:", err);
    }
  }

  return {
    req: opts.req,
    resHeaders: opts.resHeaders,
    user: user ?? FALLBACK_USER,
  };
}
