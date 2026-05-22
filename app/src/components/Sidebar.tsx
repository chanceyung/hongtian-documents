import { motion } from "framer-motion";
import {
  MessageSquare,
  Plus,
  PanelLeftClose,
  Trash2,
  Search,
  FileText,
  Clock,
} from "lucide-react";
import { useStore } from "@/hooks/useStore";
import { trpc } from "@/providers/trpc";
import { useAuth } from "@/hooks/useAuth";
import { useState } from "react";

interface ConvItem {
  id: number;
  title: string;
  createdAt: Date;
  updatedAt: Date;
  userId: number;
}

export default function Sidebar() {
  const { isSidebarOpen, toggleSidebar, setActiveConversation, activeConversationId, setMessages, setActiveTask } = useStore();
  const { user } = useAuth();
  const [searchQuery, setSearchQuery] = useState("");
  const utils = trpc.useUtils();

  const createConv = trpc.conversation.create.useMutation({
    onSuccess: () => utils.conversation.list.invalidate(),
  });
  const deleteConv = trpc.conversation.delete.useMutation({
    onSuccess: () => {
      utils.conversation.list.invalidate();
      setActiveConversation(null);
      setMessages([]);
      setActiveTask(null);
    },
  });

  const { data: convData } = trpc.conversation.list.useQuery(undefined, {
    enabled: !!user,
  });

  const displayConversations: ConvItem[] = (convData as ConvItem[] | undefined) || [];
  const filteredConversations = displayConversations.filter((c: ConvItem) =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleSelectConversation = async (id: number) => {
    setActiveConversation(id);
    const data = await utils.conversation.getById.fetch({ id });
    if (data && data.messages) {
      setMessages(
        data.messages.map((m: { id: number; role: "user" | "assistant"; content: string; attachments: string | null; createdAt: Date }) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          attachments: m.attachments ? JSON.parse(m.attachments) : [],
          createdAt: new Date(m.createdAt),
        }))
      );
    }
  };

  const handleNewConversation = () => {
    createConv.mutate({ title: "新对话" });
  };

  if (!isSidebarOpen) {
    return (
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: 52 }}
        className="h-full bg-[#0a0f1c]/60 backdrop-blur-md border-r border-white/[0.05] flex flex-col items-center py-3 shrink-0"
      >
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-xl hover:bg-white/[0.06] transition-all mb-2"
        >
          <PanelLeftClose className="w-4 h-4 text-slate-500" />
        </button>
        <button
          onClick={handleNewConversation}
          className="p-2 rounded-xl hover:bg-white/[0.06] transition-all mb-3"
        >
          <Plus className="w-4 h-4 text-slate-400" />
        </button>
        <div className="flex-1 overflow-y-auto w-full flex flex-col items-center gap-1 py-2">
          {filteredConversations.slice(0, 8).map((conv: ConvItem) => (
            <button
              key={conv.id}
              onClick={() => handleSelectConversation(conv.id)}
              title={conv.title}
              className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all ${
                activeConversationId === conv.id
                  ? "bg-blue-500/15 text-blue-400 ring-1 ring-blue-500/20"
                  : "hover:bg-white/[0.04] text-slate-600"
              }`}
            >
              <MessageSquare className="w-4 h-4" />
            </button>
          ))}
        </div>
        <div className="w-8 h-8 rounded-lg overflow-hidden flex items-center justify-center bg-gradient-to-br from-blue-500/10 to-purple-500/10 ring-1 ring-white/[0.06] mb-2">
          <img src="/logo-white.png" alt="" className="w-5 h-5 object-contain opacity-50" />
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ width: 0, opacity: 0 }}
      animate={{ width: 264, opacity: 1 }}
      exit={{ width: 0, opacity: 0 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className="h-full bg-[#0a0f1c]/60 backdrop-blur-md border-r border-white/[0.05] flex flex-col shrink-0"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3.5 py-3">
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded-lg hover:bg-white/[0.06] transition-colors"
        >
          <PanelLeftClose className="w-4 h-4 text-slate-500" />
        </button>
        <button
          onClick={handleNewConversation}
          className="flex items-center gap-1.5 px-3 py-[7px] bg-blue-600 hover:bg-blue-500 text-white text-[12px] font-medium rounded-lg transition-all shadow-lg shadow-blue-600/20 hover:shadow-blue-500/30"
        >
          <Plus className="w-3.5 h-3.5" />
          新对话
        </button>
      </div>

      {/* Search */}
      <div className="px-3 pb-2.5">
        <div className="relative group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-600 group-focus-within:text-blue-400 transition-colors" />
          <input
            type="text"
            placeholder="搜索对话..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl pl-9 pr-3 py-[9px] text-[12px] text-slate-300 placeholder-slate-600 focus:outline-none focus:border-blue-500/30 focus:bg-white/[0.05] transition-all"
          />
        </div>
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto px-2.5 py-1">
        <div className="px-2 mb-1.5 flex items-center gap-1.5">
          <Clock className="w-3 h-3 text-slate-700" />
          <span className="text-[10px] text-slate-600 font-medium tracking-wider uppercase">最近对话</span>
        </div>

        {filteredConversations.map((conv: ConvItem) => (
          <div
            key={conv.id}
            onClick={() => handleSelectConversation(conv.id)}
            className={`group flex items-center gap-2.5 px-3 py-2.5 rounded-xl cursor-pointer transition-all mb-0.5 ${
              activeConversationId === conv.id
                ? "bg-white/[0.06] border border-white/[0.08] shadow-sm"
                : "hover:bg-white/[0.03] border border-transparent"
            }`}
          >
            <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 transition-colors ${
              activeConversationId === conv.id
                ? "bg-blue-500/15 text-blue-400"
                : "bg-white/[0.04] text-slate-600"
            }`}>
              <MessageSquare className="w-3.5 h-3.5" />
            </div>
            <div className="flex-1 min-w-0">
              <p className={`text-[12px] font-medium truncate ${
                activeConversationId === conv.id ? "text-slate-200" : "text-slate-400"
              }`}>{conv.title}</p>
              <p className="text-[10px] text-slate-700 mt-0.5">
                {new Date(conv.updatedAt).toLocaleDateString("zh-CN", { month: "short", day: "numeric" })}
              </p>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                deleteConv.mutate({ id: conv.id });
              }}
              className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-red-500/10 transition-all"
            >
              <Trash2 className="w-3 h-3 text-slate-600 hover:text-red-400 transition-colors" />
            </button>
          </div>
        ))}

        {filteredConversations.length === 0 && (
          <div className="flex flex-col items-center justify-center py-10 text-slate-700">
            <div className="w-10 h-10 rounded-xl bg-white/[0.03] flex items-center justify-center mb-2.5">
              <FileText className="w-5 h-5 opacity-40" />
            </div>
            <p className="text-[11px]">暂无对话</p>
            <p className="text-[10px] mt-0.5 opacity-60">点击上方按钮开始</p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-3.5 py-3 border-t border-white/[0.05]">
        <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-white/[0.02]">
          <div className="w-5 h-5 rounded overflow-hidden flex items-center justify-center opacity-40">
            <img src="/logo-white.png" alt="" className="w-4 h-4 object-contain" />
          </div>
          <div>
            <p className="text-[10px] text-slate-600 font-medium">弘天文档</p>
            <p className="text-[9px] text-slate-800">杂志级文档重构</p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
