import { z } from "zod";
import { createRouter, publicQuery } from "./middleware";
import { getDb } from "./queries/connection";
import { userSettings } from "@db/schema";
import { eq } from "drizzle-orm";

export const settingsRouter = createRouter({
  get: publicQuery.query(async ({ ctx }) => {
    const db = getDb();
    const userId = ctx.user?.id;
    if (!userId) return null;
    const [settings] = await db.select().from(userSettings)
      .where(eq(userSettings.userId, userId));
    return settings || null;
  }),

  save: publicQuery.input(z.object({
    zhipuApiKey: z.string().optional(),
    zhipuModel: z.string().default("glm-4-flash"),
    defaultFormat: z.enum(["pdf", "pptx"]).default("pdf"),
    defaultTemplate: z.string().default("modern_tech"),
  })).mutation(async ({ input, ctx }) => {
    const db = getDb();
    const userId = ctx.user?.id;
    if (!userId) throw new Error("未登录");
    const [existing] = await db.select().from(userSettings)
      .where(eq(userSettings.userId, userId));
    if (existing) {
      await db.update(userSettings).set({
        zhipuApiKey: input.zhipuApiKey,
        zhipuModel: input.zhipuModel,
        defaultFormat: input.defaultFormat,
        defaultTemplate: input.defaultTemplate,
      }).where(eq(userSettings.id, existing.id));
      const [updated] = await db.select().from(userSettings).where(eq(userSettings.id, existing.id));
      return updated;
    } else {
      const result = await db.insert(userSettings).values({
        userId,
        zhipuApiKey: input.zhipuApiKey,
        zhipuModel: input.zhipuModel,
        defaultFormat: input.defaultFormat,
        defaultTemplate: input.defaultTemplate,
      }).$returningId();
      const [settings] = await db.select().from(userSettings).where(eq(userSettings.id, result[0].id));
      return settings;
    }
  }),

  testZhipuKey: publicQuery.input(z.object({
    apiKey: z.string().min(1),
  })).mutation(async ({ input }) => {
    try {
      const response = await fetch("https://open.bigmodel.cn/api/paas/v4/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${input.apiKey}`,
        },
        body: JSON.stringify({
          model: "glm-4-flash",
          messages: [{ role: "user", content: "Hi" }],
          max_tokens: 5,
        }),
      });
      if (response.status === 200) {
        return { valid: true, message: "API Key 有效" };
      } else {
        const data = await response.text();
        return { valid: false, message: `API 返回错误: ${response.status}`, details: data };
      }
    } catch (e) {
      return { valid: false, message: `连接失败: ${(e as Error).message}` };
    }
  }),
});
