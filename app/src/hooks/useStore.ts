import { create } from "zustand";

export interface Attachment {
  fileName: string;
  fileSize: string;
  fileType: string;
  fileUrl: string;
}

export interface AgentStateUI {
  id: string;
  agentType: string;
  name: string;
  color: string;
  status: "pending" | "running" | "completed" | "error";
  progress: number;
  logs: string[];
  isExpanded: boolean;
}

export interface MessageUI {
  id: string;
  role: "user" | "assistant";
  content: string;
  attachments?: Attachment[];
  createdAt: Date;
}

export interface ConversationUI {
  id: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface TaskUI {
  id: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  outputFormat: "pdf" | "pptx";
  outputFile?: string;
  pythonTaskId?: string;
  agentStates: AgentStateUI[];
}

interface AppState {
  // Conversations
  conversations: ConversationUI[];
  activeConversationId: string | null;
  setConversations: (convs: ConversationUI[]) => void;
  setActiveConversation: (id: string | null) => void;
  addConversation: (conv: ConversationUI) => void;

  // Messages
  messages: MessageUI[];
  setMessages: (msgs: MessageUI[]) => void;
  addMessage: (msg: MessageUI) => void;

  // Tasks
  activeTask: TaskUI | null;
  setActiveTask: (task: TaskUI | null) => void;
  updateAgentState: (agentType: string, updates: Partial<AgentStateUI>) => void;

  // UI
  isAgentPanelOpen: boolean;
  isSidebarOpen: boolean;
  toggleAgentPanel: () => void;
  toggleSidebar: () => void;

  // Input
  inputText: string;
  attachments: Attachment[];
  setInputText: (text: string) => void;
  setAttachments: (atts: Attachment[]) => void;
  addAttachment: (att: Attachment) => void;
  removeAttachment: (index: number) => void;
}

export const useStore = create<AppState>((set) => ({
  conversations: [],
  activeConversationId: null,
  setConversations: (convs) => set({ conversations: convs }),
  setActiveConversation: (id) => set({ activeConversationId: id }),
  addConversation: (conv) => set((s) => ({ conversations: [conv, ...s.conversations] })),

  messages: [],
  setMessages: (msgs) => set({ messages: msgs }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

  activeTask: null,
  setActiveTask: (task) => set({ activeTask: task }),
  updateAgentState: (agentType, updates) =>
    set((s) => {
      if (!s.activeTask) return s;
      const updatedAgents = s.activeTask.agentStates.map((a) =>
        a.agentType === agentType ? { ...a, ...updates } : a
      );
      return {
        activeTask: { ...s.activeTask, agentStates: updatedAgents },
      };
    }),

  isAgentPanelOpen: true,
  isSidebarOpen: true,
  toggleAgentPanel: () => set((s) => ({ isAgentPanelOpen: !s.isAgentPanelOpen })),
  toggleSidebar: () => set((s) => ({ isSidebarOpen: !s.isSidebarOpen })),

  inputText: "",
  attachments: [],
  setInputText: (text) => set({ inputText: text }),
  setAttachments: (atts) => set({ attachments: atts }),
  addAttachment: (att) => set((s) => ({ attachments: [...s.attachments, att] })),
  removeAttachment: (index) =>
    set((s) => ({ attachments: s.attachments.filter((_, i) => i !== index) })),
}));
