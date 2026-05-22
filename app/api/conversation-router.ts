import { z } from "zod";
import { createRouter, publicQuery } from "./middleware";
import { getDb } from "./queries/connection";
import { conversations, messages } from "@db/schema";
import { eq, desc } from "drizzle-orm";

export const conversationRouter = createRouter({
  list: publicQuery.query(async ({ ctx }) => {
    const db = await getDb();
    return db.select().from(conversations)
      .where(eq(conversations.userId, ctx.user.id))
      .orderBy(desc(conversations.updatedAt));
  }),

  create: publicQuery.input(z.object({
    title: z.string().min(1).max(255).default("新对话"),
  })).mutation(async ({ input, ctx }) => {
    const db = await getDb();
    await db.insert(conversations).values({
      userId: ctx.user.id,
      title: input.title,
    });
    const rows = await db.select().from(conversations)
      .where(eq(conversations.userId, ctx.user.id))
      .orderBy(desc(conversations.createdAt))
      .limit(1);
    return rows[0];
  }),

  getById: publicQuery.input(z.object({ id: z.string() })).query(async ({ input, ctx }) => {
    const db = await getDb();
    const [conv] = await db.select().from(conversations)
      .where(eq(conversations.id, input.id));
    if (!conv) throw new Error("对话不存在");
    const msgs = await db.select().from(messages)
      .where(eq(messages.conversationId, input.id))
      .orderBy(messages.createdAt);
    return { ...conv, messages: msgs };
  }),

  updateTitle: publicQuery.input(z.object({
    id: z.string(),
    title: z.string().min(1).max(255),
  })).mutation(async ({ input }) => {
    const db = await getDb();
    await db.update(conversations).set({ title: input.title, updatedAt: new Date() })
      .where(eq(conversations.id, input.id));
    return { success: true };
  }),

  delete: publicQuery.input(z.object({ id: z.string() })).mutation(async ({ input }) => {
    const db = await getDb();
    await db.delete(messages).where(eq(messages.conversationId, input.id));
    await db.delete(conversations).where(eq(conversations.id, input.id));
    return { success: true };
  }),
});
