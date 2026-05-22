import { useState, useEffect } from "react";
import {
  Settings,
  LogOut,
  PanelLeft,
  PanelRight,
  Command,
} from "lucide-react";
import { useStore } from "@/hooks/useStore";
import { trpc } from "@/providers/trpc";
import { useAuth } from "@/hooks/useAuth";
import Sidebar from "@/components/Sidebar";
import ChatInterface from "@/components/ChatInterface";
import AgentPanel from "@/components/AgentPanel";
import SettingsDialog from "@/components/SettingsDialog";

export default function Home() {
  const [showSettings, setShowSettings] = useState(false);
  const { isAgentPanelOpen, isSidebarOpen, toggleAgentPanel, toggleSidebar, setActiveConversation, activeConversationId, setMessages, setActiveTask } = useStore();
  const { user, logout } = useAuth();

  const { data: convData } = trpc.conversation.list.useQuery(undefined, {
    enabled: !!user,
  });

  useEffect(() => {
    if (convData && convData.length > 0) {
      if (!activeConversationId) {
        setActiveConversation(convData[0].id);
      }
    }
  }, [convData, activeConversationId]);

  const createConv = trpc.conversation.create.useMutation({
    onSuccess: (conv) => {
      setActiveConversation(conv.id);
      setMessages([]);
      setActiveTask(null);
    },
  });

  useEffect(() => {
    if (user && convData && convData.length === 0) {
      createConv.mutate({ title: "新对话" });
    }
  }, [user, convData]);

  return (
    <div className="h-screen w-screen bg-[#060b14] flex flex-col overflow-hidden relative bg-mesh">
      {/* ─── Top Navigation Bar ─── */}
      <header className="h-[52px] bg-[#0c1220]/80 backdrop-blur-xl border-b border-white/[0.06] flex items-center justify-between px-3.5 shrink-0 z-50">
        {/* Left */}
        <div className="flex items-center gap-2">
          {!isSidebarOpen && (
            <button
              onClick={toggleSidebar}
              className="p-1.5 rounded-lg hover:bg-white/[0.06] transition-colors mr-1"
            >
              <PanelLeft className="w-4 h-4 text-slate-400" />
            </button>
          )}
          <div className="flex items-center gap-2.5">
            <div className="w-[30px] h-[30px] rounded-lg overflow-hidden flex items-center justify-center bg-gradient-to-br from-blue-500/20 to-purple-500/20 ring-1 ring-white/[0.08]">
              <img
                src="/logo-white.png"
                alt="弘天文档"
                className="w-[22px] h-[22px] object-contain"
              />
            </div>
            <div className="flex items-baseline gap-1.5">
              <span className="text-[14px] font-semibold text-slate-100 tracking-tight">弘天文档</span>
              <span className="text-[10px] text-slate-600 font-medium tracking-wider uppercase">v1.0</span>
            </div>
          </div>
        </div>

        {/* Center - Keyboard shortcut hint */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/[0.03] border border-white/[0.05]">
          <Command className="w-3 h-3 text-slate-600" />
          <span className="text-[11px] text-slate-600">快捷键 Ctrl+K</span>
        </div>

        {/* Right */}
        <div className="flex items-center gap-0.5">
          {!isAgentPanelOpen && (
            <button
              onClick={toggleAgentPanel}
              className="p-2 rounded-lg hover:bg-white/[0.06] transition-colors"
              title="打开任务面板"
            >
              <PanelRight className="w-4 h-4 text-slate-400" />
            </button>
          )}
          <button
            onClick={() => setShowSettings(true)}
            className="p-2 rounded-lg hover:bg-white/[0.06] transition-colors"
            title="设置"
          >
            <Settings className="w-4 h-4 text-slate-400" />
          </button>
          {user && (
            <div className="flex items-center gap-2 ml-2 pl-2.5 border-l border-white/[0.06]">
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-[11px] font-semibold text-white shadow-lg shadow-blue-500/20">
                {user.name?.charAt(0) || "U"}
              </div>
              <button
                onClick={logout}
                className="p-1.5 rounded-lg hover:bg-white/[0.06] transition-colors"
                title="退出登录"
              >
                <LogOut className="w-3.5 h-3.5 text-slate-500" />
              </button>
            </div>
          )}
        </div>
      </header>

      {/* ─── Main Content ─── */}
      <div className="flex-1 flex overflow-hidden relative">
        <Sidebar />
        <main className="flex-1 flex flex-col min-w-0 relative">
          <ChatInterface />
        </main>
        <AgentPanel />
      </div>

      {/* ─── Settings Dialog ─── */}
      <SettingsDialog open={showSettings} onClose={() => setShowSettings(false)} />
    </div>
  );
}
