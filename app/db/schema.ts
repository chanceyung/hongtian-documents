import { sqliteTable, text, integer } from "drizzle-orm/sqlite-core";
import { nanoid } from "nanoid";

function nid() {
  return text("id")
    .primaryKey()
    .$defaultFn(() => nanoid(16));
}

export const users = sqliteTable("users", {
  id: nid(),
  name: text("name").notNull().default("桌面用户"),
  email: text("email"),
  avatar: text("avatar"),
  role: text("role", { enum: ["user", "admin"] }).notNull().default("admin"),
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .$defaultFn(() => new Date()),
  updatedAt: integer("updated_at", { mode: "timestamp" })
    .notNull()
    .$defaultFn(() => new Date()),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;

export const conversations = sqliteTable("conversations", {
  id: nid(),
  userId: text("user_id")
    .notNull()
    .references(() => users.id),
  title: text("title").notNull().default("新对话"),
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .$defaultFn(() => new Date()),
  updatedAt: integer("updated_at", { mode: "timestamp" })
    .notNull()
    .$defaultFn(() => new Date()),
});

export type Conversation = typeof conversations.$inferSelect;

export const messages = sqliteTable("messages", {
  id: nid(),
  conversationId: text("conversation_id")
    .notNull()
    .references(() => conversations.id),
  role: text("role", { enum: ["user", "assistant"] }).notNull(),
  content: text("content").notNull(),
  attachments: text("attachments"),
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .$defaultFn(() => new Date()),
});

export interface Attachment {
  fileName: string;
  fileSize: string;
  fileType: string;
  fileUrl: string;
}

export type Message = typeof messages.$inferSelect;

export const tasks = sqliteTable("tasks", {
  id: nid(),
  conversationId: text("conversation_id")
    .notNull()
    .references(() => conversations.id),
  userId: text("user_id")
    .notNull()
    .references(() => users.id),
  status: text("status", { enum: ["pending", "running", "completed", "failed"] })
    .notNull()
    .default("pending"),
  outputFormat: text("output_format", { enum: ["pdf", "pptx"] })
    .notNull()
    .default("pdf"),
  outputFile: text("output_file"),
  progress: integer("progress").notNull().default(0),
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .$defaultFn(() => new Date()),
  completedAt: integer("completed_at", { mode: "timestamp" }),
});

export type Task = typeof tasks.$inferSelect;

export const agentStates = sqliteTable("agent_states", {
  id: nid(),
  taskId: text("task_id")
    .notNull()
    .references(() => tasks.id),
  agentType: text("agent_type").notNull(),
  status: text("status", { enum: ["pending", "running", "completed", "error"] })
    .notNull()
    .default("pending"),
  progress: integer("progress").notNull().default(0),
  logs: text("logs"),
  startedAt: integer("started_at", { mode: "timestamp" }),
  completedAt: integer("completed_at", { mode: "timestamp" }),
});

export type AgentState = typeof agentStates.$inferSelect;

export const userSettings = sqliteTable("user_settings", {
  id: nid(),
  userId: text("user_id")
    .notNull()
    .references(() => users.id)
    .unique(),
  zhipuApiKey: text("zhipu_api_key"),
  zhipuModel: text("zhipu_model").default("glm-4-flash"),
  defaultFormat: text("default_format", { enum: ["pdf", "pptx"] }).default("pdf"),
  defaultTemplate: text("default_template").default("modern_tech"),
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .$defaultFn(() => new Date()),
  updatedAt: integer("updated_at", { mode: "timestamp" })
    .notNull()
    .$defaultFn(() => new Date()),
});

export type UserSettings = typeof userSettings.$inferSelect;
