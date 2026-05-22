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
import { useState } from "react";

interface ConvItem {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  userId: string;
}

export default function Sidebar() {
  const { isSidebarOpen, toggleSidebar, setActiveConversation, activeConversationId, setMessages, setActiveTask } = useStore();
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

  const { data: convData } = trpc.conversation.list.useQuery(undefined);

  const displayConversations: ConvItem[] = (convData as ConvItem[] | undefined) || [];
  const filteredConversations = displayConversations.filter((c: ConvItem) =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleSelectConversation = async (id: string) => {
    setActiveConversation(id);
    const data = await utils.conversation.getById.fetch({ id });
    if (data && data.messages) {
      setMessages(
        data.messages.map((m: { id: string; role: "user" | "assistant"; content: string; attachments: string | null; createdAt: string }) => ({
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
      <div className="h-full w-[52px] bg-[#080c16] flex flex-col items-center py-3 shrink-0">
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-xl hover:bg-white/[0.08] transition-all mb-2 group"
          title="展开侧栏"
        >
          <PanelLeftClose className="w-4 h-4 text-white/30 group-hover:text-white/60" />
        </button>
        <button
          onClick={handleNewConversation}
          className="p-2 rounded-xl hover:bg-white/[0.08] transition-all mb-3 group"
          title="新建对话"
        >
          <Plus className="w-4 h-4 text-white/40 group-hover:text-blue-400" />
        </button>
        <div className="flex-1 overflow-y-auto w-full flex flex-col items-center gap-1.5 py-2">
          {filteredConversations.slice(0, 10).map((conv: ConvItem, idx: number) => (
            <button
              key={conv.id}
              onClick={() => handleSelectConversation(conv.id)}
              title={conv.title}
              className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all relative group ${
                activeConversationId === conv.id
                  ? "bg-blue-500/20 text-blue-400"
                  : "hover:bg-white/[0.06] text-white/25 hover:text-white/50"
              }`}
            >
              <span className="text-[11px] font-semibold">{idx + 1}</span>
              <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 rounded-r-full bg-blue-400 opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
          ))}
        </div>
        <div className="w-8 h-8 rounded-lg overflow-hidden flex items-center justify-center mb-2 opacity-40">
          <img src="/logo-white.png" alt="" className="w-5 h-5 object-contain" />
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ width: 0, opacity: 0 }}
      animate={{ width: 260, opacity: 1 }}
      exit={{ width: 0, opacity: 0 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className="h-full bg-[#080c16] flex flex-col shrink-0"
    >
      {/* 新建对话按钮 */}
      <div className="px-3 pt-3 pb-2">
        <button
          onClick={handleNewConversation}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5 bg-white/[0.04] hover:bg-white/[0.07] border border-white/[0.06] hover:border-white/[0.1] text-white/70 hover:text-white/90 text-[13px] font-medium rounded-xl transition-all"
        >
          <Plus className="w-4 h-4" />
          新建对话
        </button>
      </div>

      {/* 搜索 */}
      <div className="px-3 pb-2">
        <div className="relative group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-white/20 group-focus-within:text-blue-400 transition-colors" />
          <input
            type="text"
            placeholder="搜索对话..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-white/[0.02] border border-white/[0.04] rounded-xl pl-9 pr-3 py-2 text-[12px] text-white/70 placeholder-white/20 focus:outline-none focus:border-blue-500/20 focus:bg-white/[0.03] transition-all"
          />
        </div>
      </div>

      {/* 对话列表 */}
      <div className="flex-1 overflow-y-auto px-2 py-1">
        <div className="px-2 mb-2 flex items-center gap-1.5">
          <Clock className="w-3 h-3 text-white/15" />
          <span className="text-[10px] text-white/20 font-medium tracking-wider">最近对话</span>
        </div>

        {filteredConversations.map((conv: ConvItem) => (
          <div
            key={conv.id}
            onClick={() => handleSelectConversation(conv.id)}
            className={`group flex items-center gap-2.5 px-3 py-2.5 rounded-xl cursor-pointer transition-all mb-0.5 ${
              activeConversationId === conv.id
                ? "bg-white/[0.05]"
                : "hover:bg-white/[0.025]"
            }`}
          >
            <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 transition-colors ${
              activeConversationId === conv.id
                ? "bg-blue-500/15 text-blue-400"
                : "bg-white/[0.03] text-white/20"
            }`}>
              <MessageSquare className="w-3.5 h-3.5" />
            </div>
            <div className="flex-1 min-w-0">
              <p className={`text-[12px] font-medium truncate ${
                activeConversationId === conv.id ? "text-white/80" : "text-white/40"
              }`}>{conv.title}</p>
              <p className="text-[10px] text-white/15 mt-0.5">
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
              <Trash2 className="w-3 h-3 text-white/20 hover:text-red-400 transition-colors" />
            </button>
          </div>
        ))}

        {filteredConversations.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-white/15">
            <FileText className="w-8 h-8 mb-2 opacity-40" />
            <p className="text-[11px]">暂无对话</p>
          </div>
        )}
      </div>

      {/* 底部折叠按钮 */}
      <div className="px-3 py-2.5 border-t border-white/[0.04]">
        <button
          onClick={toggleSidebar}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-white/[0.04] transition-all text-white/30 hover:text-white/50 text-[12px]"
        >
          <PanelLeftClose className="w-4 h-4" />
          收起侧栏
        </button>
      </div>
    </motion.div>
  );
}
