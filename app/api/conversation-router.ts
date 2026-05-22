import { z } from "zod";
import { createRouter, publicQuery } from "./middleware";
import { getDb } from "./queries/connection";
import { conversations, messages } from "@db/schema";
import { eq, desc } from "drizzle-orm";

export const conversationRouter = createRouter({
  list: publicQuery.query(async ({ ctx }) => {
    const db = getDb();
    const userId = ctx.user?.id;
    if (!userId) return [];
    return db.select().from(conversations)
      .where(eq(conversations.userId, userId))
      .orderBy(desc(conversations.updatedAt));
  }),

  create: publicQuery.input(z.object({
    title: z.string().min(1).max(255).default("新对话"),
  })).mutation(async ({ input, ctx }) => {
    const db = getDb();
    const userId = ctx.user?.id;
    if (!userId) throw new Error("未登录");
    const result = await db.insert(conversations).values({
      userId,
      title: input.title,
    }).$returningId();
    const [conv] = await db.select().from(conversations).where(eq(conversations.id, result[0].id));
    return conv;
  }),

  getById: publicQuery.input(z.object({ id: z.number() })).query(async ({ input, ctx }) => {
    const db = getDb();
    const userId = ctx.user?.id;
    if (!userId) throw new Error("未登录");
    const [conv] = await db.select().from(conversations)
      .where(eq(conversations.id, input.id));
    if (!conv || conv.userId !== userId) throw new Error("对话不存在");
    const msgs = await db.select().from(messages)
      .where(eq(messages.conversationId, input.id))
      .orderBy(messages.createdAt);
    return { ...conv, messages: msgs };
  }),

  updateTitle: publicQuery.input(z.object({
    id: z.number(),
    title: z.string().min(1).max(255),
  })).mutation(async ({ input, ctx }) => {
    const db = getDb();
    const userId = ctx.user?.id;
    if (!userId) throw new Error("未登录");
    await db.update(conversations).set({ title: input.title })
      .where(eq(conversations.id, input.id));
    return { success: true };
  }),

  delete: publicQuery.input(z.object({ id: z.number() })).mutation(async ({ input, ctx }) => {
    const db = getDb();
    const userId = ctx.user?.id;
    if (!userId) throw new Error("未登录");
    await db.delete(messages).where(eq(messages.conversationId, input.id));
    await db.delete(conversations).where(eq(conversations.id, input.id));
    return { success: true };
  }),
});
