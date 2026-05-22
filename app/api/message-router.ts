import { z } from "zod";
import { createRouter, publicQuery } from "./middleware";
import { getDb } from "./queries/connection";
import { messages } from "@db/schema";
import { eq, asc, desc } from "drizzle-orm";

export const messageRouter = createRouter({
  list: publicQuery.input(z.object({
    conversationId: z.string(),
  })).query(async ({ input }) => {
    const db = await getDb();
    return db.select().from(messages)
      .where(eq(messages.conversationId, input.conversationId))
      .orderBy(asc(messages.createdAt));
  }),

  create: publicQuery.input(z.object({
    conversationId: z.string(),
    role: z.enum(["user", "assistant"]),
    content: z.string().min(1),
    attachments: z.string().optional(),
  })).mutation(async ({ input }) => {
    const db = await getDb();
    await db.insert(messages).values({
      conversationId: input.conversationId,
      role: input.role,
      content: input.content,
      attachments: input.attachments,
    });
    const rows = await db.select().from(messages)
      .where(eq(messages.conversationId, input.conversationId))
      .orderBy(desc(messages.createdAt))
      .limit(1);
    return rows[0];
  }),
});
