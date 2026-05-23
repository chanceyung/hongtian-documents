import { z } from "zod";
import { createRouter, publicQuery } from "./middleware";
import { getDb, saveDatabase } from "./queries/connection";
import { userSettings } from "@db/schema";
import { eq } from "drizzle-orm";

export const settingsRouter = createRouter({
  get: publicQuery.query(async ({ ctx }) => {
    const db = await getDb();
    const [settings] = await db.select().from(userSettings)
      .where(eq(userSettings.userId, ctx.user.id));
    return settings || null;
  }),

  save: publicQuery.input(z.object({
    zhipuApiKey: z.string().optional(),
    zhipuModel: z.string().default("glm-4-flash"),
    defaultFormat: z.enum(["pdf", "pptx"]).default("pdf"),
    defaultTemplate: z.string().default("modern_tech"),
  })).mutation(async ({ input, ctx }) => {
    const db = await getDb();
    const [existing] = await db.select().from(userSettings)
      .where(eq(userSettings.userId, ctx.user.id));
    if (existing) {
      await db.update(userSettings).set({
        zhipuApiKey: input.zhipuApiKey,
        zhipuModel: input.zhipuModel,
        defaultFormat: input.defaultFormat,
        defaultTemplate: input.defaultTemplate,
        updatedAt: new Date(),
      }).where(eq(userSettings.id, existing.id));
      const [updated] = await db.select().from(userSettings).where(eq(userSettings.id, existing.id));
      saveDatabase();

      // Sync API key to Python backend
      if (input.zhipuApiKey) {
        try {
          const pythonPort = process.env.PYTHON_BACKEND_PORT || "8000";
          await fetch(`http://127.0.0.1:${pythonPort}/api/api-keys/save`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              session_id: "desktop",
              zhipu_api_key: input.zhipuApiKey,
              zhipu_model: input.zhipuModel,
            }),
          });
        } catch (err) {
          console.error("[Settings] Failed to sync API key to Python backend:", err);
        }
      }

      return updated;
    } else {
      await db.insert(userSettings).values({
        userId: ctx.user.id,
        zhipuApiKey: input.zhipuApiKey,
        zhipuModel: input.zhipuModel,
        defaultFormat: input.defaultFormat,
        defaultTemplate: input.defaultTemplate,
      });
      const rows = await db.select().from(userSettings)
        .where(eq(userSettings.userId, ctx.user.id)).limit(1);
      saveDatabase();

      // Sync API key to Python backend
      if (input.zhipuApiKey) {
        try {
          const pythonPort = process.env.PYTHON_BACKEND_PORT || "8000";
          await fetch(`http://127.0.0.1:${pythonPort}/api/api-keys/save`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              session_id: "desktop",
              zhipu_api_key: input.zhipuApiKey,
              zhipu_model: input.zhipuModel,
            }),
          });
        } catch (err) {
          console.error("[Settings] Failed to sync API key to Python backend:", err);
        }
      }

      return rows[0];
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
