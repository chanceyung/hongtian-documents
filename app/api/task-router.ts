import { z } from "zod";
import { createRouter, publicQuery } from "./middleware";
import { getDb } from "./queries/connection";
import { tasks, agentStates, messages } from "@db/schema";
import { eq, desc } from "drizzle-orm";

// 模拟多 Agent 编排流程
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
    const db = getDb();
    const userId = ctx.user?.id;
    if (!userId) return [];
    return db.select().from(tasks)
      .where(eq(tasks.userId, userId))
      .orderBy(desc(tasks.createdAt));
  }),

  getByConversation: publicQuery.input(z.object({
    conversationId: z.number(),
  })).query(async ({ input, ctx }) => {
    const db = getDb();
    const userId = ctx.user?.id;
    if (!userId) return [];
    return db.select().from(tasks)
      .where(eq(tasks.conversationId, input.conversationId))
      .orderBy(desc(tasks.createdAt));
  }),

  getAgentStates: publicQuery.input(z.object({
    taskId: z.number(),
  })).query(async ({ input }) => {
    const db = getDb();
    return db.select().from(agentStates)
      .where(eq(agentStates.taskId, input.taskId));
  }),

  create: publicQuery.input(z.object({
    conversationId: z.number(),
    outputFormat: z.enum(["pdf", "pptx"]).default("pdf"),
  })).mutation(async ({ input, ctx }) => {
    const db = getDb();
    const userId = ctx.user?.id;
    if (!userId) throw new Error("未登录");

    // 创建任务
    const taskResult = await db.insert(tasks).values({
      conversationId: input.conversationId,
      userId,
      outputFormat: input.outputFormat,
      status: "pending",
      progress: 0,
    }).$returningId();
    const [task] = await db.select().from(tasks).where(eq(tasks.id, taskResult[0].id));

    // 创建 Agent 状态记录
    for (const agent of AGENT_PIPELINE) {
      await db.insert(agentStates).values({
        taskId: task.id,
        agentType: agent.type,
        status: "pending",
        progress: 0,
        logs: JSON.stringify([]),
      });
    }

    return task;
  }),

  // 模拟启动 Agent 管道（实际项目中这里会调用 Python 服务）
  startPipeline: publicQuery.input(z.object({
    taskId: z.number(),
  })).mutation(async ({ input }) => {
    const db = getDb();

    // 更新任务状态为运行中
    await db.update(tasks).set({ status: "running" })
      .where(eq(tasks.id, input.taskId));

    // 模拟异步 Agent 执行
    (async () => {
      let overallProgress = 0;
      for (let i = 0; i < AGENT_PIPELINE.length; i++) {
        const agent = AGENT_PIPELINE[i];

        // 更新 Agent 状态为运行中
        await db.update(agentStates).set({
          status: "running",
          startedAt: new Date(),
          logs: JSON.stringify([`开始执行: ${agent.name}`]),
        }).where(eq(agentStates.taskId, input.taskId));

        // 模拟进度更新
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

          await db.update(agentStates).set({
            progress,
            logs: JSON.stringify(logMessages),
          }).where(eq(agentStates.taskId, input.taskId));

          await db.update(tasks).set({
            progress: Math.min(overallProgress, 99),
          }).where(eq(tasks.id, input.taskId));
        }

        // Agent 完成
        await db.update(agentStates).set({
          status: "completed",
          progress: 100,
          completedAt: new Date(),
          logs: JSON.stringify([...JSON.parse((await db.select().from(agentStates).where(eq(agentStates.taskId, input.taskId)))[0]?.logs || "[]"), `${agent.name} 执行完成`]),
        }).where(eq(agentStates.taskId, input.taskId));
      }

      // 任务完成
      await db.update(tasks).set({
        status: "completed",
        progress: 100,
        completedAt: new Date(),
        outputFile: `output_${input.taskId}.pdf`,
      }).where(eq(tasks.id, input.taskId));

      // 添加完成消息到对话
      const [task] = await db.select().from(tasks).where(eq(tasks.id, input.taskId));
      if (task) {
        await db.insert(messages).values({
          conversationId: task.conversationId,
          role: "assistant",
          content: "文档重构任务已完成！我已将您的文件转换为杂志级精美的 PDF。您可以点击下方按钮下载结果。",
        });
      }
    })();

    return { started: true };
  }),

  delete: publicQuery.input(z.object({ id: z.number() })).mutation(async ({ input, ctx }) => {
    const db = getDb();
    const userId = ctx.user?.id;
    if (!userId) throw new Error("未登录");
    await db.delete(agentStates).where(eq(agentStates.taskId, input.id));
    await db.delete(tasks).where(eq(tasks.id, input.id));
    return { success: true };
  }),
});
