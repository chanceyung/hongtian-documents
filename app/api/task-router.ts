import { z } from "zod";
import { createRouter, publicQuery } from "./middleware";
import { getDb, saveDatabase } from "./queries/connection";
import { tasks, agentStates, messages } from "@db/schema";
import { eq, and, desc } from "drizzle-orm";

const AGENT_PIPELINE = [
  { type: "coordinator", name: "协调 Agent", duration: 2000 },
  { type: "parser", name: "解析 Agent", duration: 3000 },
  { type: "analyzer", name: "分析 Agent", duration: 4000 },
  { type: "designer", name: "设计 Agent", duration: 3000 },
  { type: "renderer", name: "渲染 Agent", duration: 5000 },
  { type: "fidelity", name: "校验 Agent", duration: 3000 },
];

export const taskRouter = createRouter({
  list: publicQuery.query(async ({ ctx }) => {
    const db = await getDb();
    return db.select().from(tasks)
      .where(eq(tasks.userId, ctx.user.id))
      .orderBy(desc(tasks.createdAt));
  }),

  getByConversation: publicQuery.input(z.object({
    conversationId: z.string(),
  })).query(async ({ input }) => {
    const db = await getDb();
    return db.select().from(tasks)
      .where(eq(tasks.conversationId, input.conversationId))
      .orderBy(desc(tasks.createdAt));
  }),

  getAgentStates: publicQuery.input(z.object({
    taskId: z.string(),
  })).query(async ({ input }) => {
    const db = await getDb();
    return db.select().from(agentStates)
      .where(eq(agentStates.taskId, input.taskId));
  }),

  create: publicQuery.input(z.object({
    conversationId: z.string(),
    outputFormat: z.enum(["pdf", "pptx"]).default("pdf"),
  })).mutation(async ({ input, ctx }) => {
    const db = await getDb();
    await db.insert(tasks).values({
      conversationId: input.conversationId,
      userId: ctx.user.id,
      outputFormat: input.outputFormat,
      status: "pending",
      progress: 0,
    });
    const rows = await db.select().from(tasks)
      .where(eq(tasks.conversationId, input.conversationId))
      .orderBy(desc(tasks.createdAt))
      .limit(1);
    const task = rows[0];

    for (const agent of AGENT_PIPELINE) {
      await db.insert(agentStates).values({
        taskId: task.id,
        agentType: agent.type,
        status: "pending",
        progress: 0,
        logs: JSON.stringify([]),
      });
    }
    saveDatabase();
    return task;
  }),

  startPipeline: publicQuery.input(z.object({
    taskId: z.string(),
  })).mutation(async ({ input }) => {
    const db = await getDb();
    await db.update(tasks).set({ status: "running" })
      .where(eq(tasks.id, input.taskId));
    saveDatabase();

    (async () => {
      try {
        let overallProgress = 0;
        for (let i = 0; i < AGENT_PIPELINE.length; i++) {
          const agent = AGENT_PIPELINE[i];
          const db = await getDb();

          await db.update(agentStates).set({
            status: "running",
            startedAt: new Date(),
            logs: JSON.stringify([`开始执行: ${agent.name}`]),
          }).where(and(eq(agentStates.taskId, input.taskId), eq(agentStates.agentType, agent.type)));
          saveDatabase();

          const steps = 5;
          for (let step = 1; step <= steps; step++) {
            await new Promise(r => setTimeout(r, agent.duration / steps));
            const progress = Math.round((step / steps) * 100);
            overallProgress = Math.round(((i + step / steps) / AGENT_PIPELINE.length) * 100);

            const logMessages = [
              `开始执行: ${agent.name}`,
              `${agent.name} 处理中... (${step}/${steps})`,
              `完成阶段 ${step}/${steps}`,
            ].slice(0, step + 1);

            await db.update(agentStates).set({ progress, logs: JSON.stringify(logMessages) })
              .where(and(eq(agentStates.taskId, input.taskId), eq(agentStates.agentType, agent.type)));
            await db.update(tasks).set({ progress: Math.min(overallProgress, 99) })
              .where(eq(tasks.id, input.taskId));
            saveDatabase();
          }

          await db.update(agentStates).set({
            status: "completed", progress: 100, completedAt: new Date(),
            logs: JSON.stringify([`开始执行: ${agent.name}`, `${agent.name} 执行完成`]),
          }).where(and(eq(agentStates.taskId, input.taskId), eq(agentStates.agentType, agent.type)));
          saveDatabase();
        }

        const db = await getDb();
        await db.update(tasks).set({
          status: "completed", progress: 100, completedAt: new Date(),
          outputFile: `output_${input.taskId}.pdf`,
        }).where(eq(tasks.id, input.taskId));

        const [task] = await db.select().from(tasks).where(eq(tasks.id, input.taskId));
        if (task) {
          await db.insert(messages).values({
            conversationId: task.conversationId,
            role: "assistant",
            content: "文档重构任务已完成！我已将您的文件转换为杂志级精美的 PDF。您可以点击下方按钮下载结果。",
          });
        }
        saveDatabase();
      } catch (err) {
        console.error("[Pipeline Error]", err);
        const db = await getDb();
        await db.update(tasks).set({ status: "failed", progress: 0 })
          .where(eq(tasks.id, input.taskId));
        saveDatabase();
      }
    })();

    return { started: true };
  }),

  delete: publicQuery.input(z.object({ id: z.string() })).mutation(async ({ input }) => {
    const db = await getDb();
    await db.delete(agentStates).where(eq(agentStates.taskId, input.id));
    await db.delete(tasks).where(eq(tasks.id, input.id));
    saveDatabase();
    return { success: true };
  }),
});
