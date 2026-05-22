import {
  mysqlTable,
  mysqlEnum,
  serial,
  varchar,
  text,
  timestamp,
  bigint,
  int,
} from "drizzle-orm/mysql-core";

export const users = mysqlTable("users", {
  id: serial("id").primaryKey(),
  unionId: varchar("unionId", { length: 255 }).notNull().unique(),
  name: varchar("name", { length: 255 }),
  email: varchar("email", { length: 320 }),
  avatar: text("avatar"),
  role: mysqlEnum("role", ["user", "admin"]).default("user").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt")
    .defaultNow()
    .notNull()
    .$onUpdate(() => new Date()),
  lastSignInAt: timestamp("lastSignInAt").defaultNow().notNull(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;

// 对话表
export const conversations = mysqlTable("conversations", {
  id: serial("id").primaryKey(),
  userId: bigint("userId", { mode: "number", unsigned: true }).notNull(),
  title: varchar("title", { length: 255 }).notNull().default("新对话"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt")
    .defaultNow()
    .notNull()
    .$onUpdate(() => new Date()),
});

export type Conversation = typeof conversations.$inferSelect;

// 消息表
export const messages = mysqlTable("messages", {
  id: serial("id").primaryKey(),
  conversationId: bigint("conversationId", { mode: "number", unsigned: true }).notNull(),
  role: mysqlEnum("role", ["user", "assistant"]).notNull(),
  content: text("content").notNull(),
  attachments: text("attachments"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export interface Attachment {
  fileName: string;
  fileSize: string;
  fileType: string;
  fileUrl: string;
}

export type Message = typeof messages.$inferSelect;

// 任务表
export const tasks = mysqlTable("tasks", {
  id: serial("id").primaryKey(),
  conversationId: bigint("conversationId", { mode: "number", unsigned: true }).notNull(),
  userId: bigint("userId", { mode: "number", unsigned: true }).notNull(),
  status: mysqlEnum("status", ["pending", "running", "completed", "failed"]).default("pending").notNull(),
  outputFormat: mysqlEnum("outputFormat", ["pdf", "pptx"]).default("pdf").notNull(),
  outputFile: varchar("outputFile", { length: 500 }),
  progress: int("progress").default(0).notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  completedAt: timestamp("completedAt"),
});

export type Task = typeof tasks.$inferSelect;

// Agent 状态表
export const agentStates = mysqlTable("agentStates", {
  id: serial("id").primaryKey(),
  taskId: bigint("taskId", { mode: "number", unsigned: true }).notNull(),
  agentType: varchar("agentType", { length: 50 }).notNull(),
  status: mysqlEnum("status", ["pending", "running", "completed", "error"]).default("pending").notNull(),
  progress: int("progress").default(0).notNull(),
  logs: text("logs"),
  startedAt: timestamp("startedAt"),
  completedAt: timestamp("completedAt"),
});

export type AgentState = typeof agentStates.$inferSelect;

// 用户设置表
export const userSettings = mysqlTable("userSettings", {
  id: serial("id").primaryKey(),
  userId: bigint("userId", { mode: "number", unsigned: true }).notNull().unique(),
  zhipuApiKey: varchar("zhipuApiKey", { length: 500 }),
  zhipuModel: varchar("zhipuModel", { length: 100 }).default("glm-4-flash"),
  defaultFormat: mysqlEnum("defaultFormat", ["pdf", "pptx"]).default("pdf"),
  defaultTemplate: varchar("defaultTemplate", { length: 100 }).default("modern_tech"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt")
    .defaultNow()
    .notNull()
    .$onUpdate(() => new Date()),
});

export type UserSettings = typeof userSettings.$inferSelect;
