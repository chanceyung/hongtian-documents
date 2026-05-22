import { authRouter } from "./auth-router";
import { conversationRouter } from "./conversation-router";
import { messageRouter } from "./message-router";
import { taskRouter } from "./task-router";
import { settingsRouter } from "./settings-router";
import { uploadRouter } from "./upload-router";
import { createRouter, publicQuery } from "./middleware";

export const appRouter = createRouter({
  ping: publicQuery.query(() => ({ ok: true, ts: Date.now() })),
  auth: authRouter,
  conversation: conversationRouter,
  message: messageRouter,
  task: taskRouter,
  settings: settingsRouter,
  upload: uploadRouter,
});

export type AppRouter = typeof appRouter;
