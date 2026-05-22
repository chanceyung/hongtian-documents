import { z } from "zod";
import { createRouter, publicQuery } from "./middleware";
import { getDb } from "./queries/connection";
import { messages } from "@db/schema";
import { eq, asc } from "drizzle-orm";

export const messageRouter = createRouter({
  list: publicQuery.input(z.object({
    conversationId: z.number(),
  })).query(async ({ input, ctx }) => {
    const db = getDb();
    const userId = ctx.user?.id;
    if (!userId) return [];
    return db.select().from(messages)
      .where(eq(messages.conversationId, input.conversationId))
      .orderBy(asc(messages.createdAt));
  }),

  create: publicQuery.input(z.object({
    conversationId: z.number(),
    role: z.enum(["user", "assistant"]),
    content: z.string().min(1),
    attachments: z.string().optional(),
  })).mutation(async ({ input }) => {
    const db = getDb();
    const result = await db.insert(messages).values({
      conversationId: input.conversationId,
      role: input.role,
      content: input.content,
      attachments: input.attachments,
    }).$returningId();
    const [msg] = await db.select().from(messages).where(eq(messages.id, result[0].id));
    return msg;
  }),
});
