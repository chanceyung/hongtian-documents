import { relations } from "drizzle-orm";
import { users, conversations, messages, tasks, agentStates } from "./schema";

export const usersRelations = relations(users, ({ many }) => ({
  conversations: many(conversations),
}));

export const conversationsRelations = relations(conversations, ({ one, many }) => ({
  user: one(users, { fields: [conversations.userId], references: [users.id] }),
  messages: many(messages),
  tasks: many(tasks),
}));

export const messagesRelations = relations(messages, ({ one }) => ({
  conversation: one(conversations, { fields: [messages.conversationId], references: [conversations.id] }),
}));

export const tasksRelations = relations(tasks, ({ one, many }) => ({
  conversation: one(conversations, { fields: [tasks.conversationId], references: [conversations.id] }),
  agentStates: many(agentStates),
}));

export const agentStatesRelations = relations(agentStates, ({ one }) => ({
  task: one(tasks, { fields: [agentStates.taskId], references: [tasks.id] }),
}));
