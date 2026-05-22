import { useState, useEffect } from "react";
import {
  Settings,
  PanelRight,
  Minus,
  Square,
  X,
} from "lucide-react";
import { useStore } from "@/hooks/useStore";
import { trpc } from "@/providers/trpc";
import Sidebar from "@/components/Sidebar";
import ChatInterface from "@/components/ChatInterface";
import AgentPanel from "@/components/AgentPanel";
import SettingsDialog from "@/components/SettingsDialog";

const DESKTOP_USER = {
  id: "desktop-user",
  name: "桌面用户",
  role: "admin",
};

export default function Home() {
  const [showSettings, setShowSettings] = useState(false);
  const { isAgentPanelOpen, toggleAgentPanel, setActiveConversation, activeConversationId, setMessages, setActiveTask } = useStore();

  const { data: convData } = trpc.conversation.list.useQuery(undefined, {
    enabled: true,
  });

  useEffect(() => {
    if (convData && convData.length > 0 && !activeConversationId) {
      setActiveConversation(convData[0].id);
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
    if (convData && convData.length === 0) {
      createConv.mutate({ title: "新对话" });
    }
  }, [convData]);

  return (
    <div className="h-screen w-screen bg-[#060b14] flex flex-col overflow-hidden relative">
      {/* ─── 自定义标题栏（可拖拽） ─── */}
      <header className="h-11 bg-[#0a0e18]/90 backdrop-blur-2xl flex items-center justify-between pl-3 pr-1.5 shrink-0 z-50 border-b border-white/[0.04]"
        style={{ WebkitAppRegion: "drag" } as React.CSSProperties}
      >
        {/* 左侧：Logo */}
        <div className="flex items-center gap-2.5" style={{ WebkitAppRegion: "no-drag" } as React.CSSProperties}>
          <img
            src="/logo-white.png"
            alt="弘天文档"
            className="w-[22px] h-[22px] object-contain"
          />
          <span className="text-[13px] font-semibold text-white/90 tracking-tight">弘天文档</span>
          <span className="text-[9px] text-white/20 font-medium ml-0.5">v4.0</span>
        </div>

        {/* 右侧：功能按钮 + 窗口控制 */}
        <div className="flex items-center gap-0.5" style={{ WebkitAppRegion: "no-drag" } as React.CSSProperties}>
          {!isAgentPanelOpen && (
            <button
              onClick={toggleAgentPanel}
              className="p-1.5 rounded-md hover:bg-white/[0.06] transition-colors"
              title="任务面板"
            >
              <PanelRight className="w-[14px] h-[14px] text-white/40" />
            </button>
          )}
          <button
            onClick={() => setShowSettings(true)}
            className="p-1.5 rounded-md hover:bg-white/[0.06] transition-colors"
            title="设置"
          >
            <Settings className="w-[14px] h-[14px] text-white/40" />
          </button>

          <div className="w-px h-3.5 bg-white/[0.06] mx-1.5" />

          {/* 窗口控制按钮 */}
          <button onClick={() => (window as any).electronAPI?.minimize()} className="w-[34px] h-[28px] flex items-center justify-center rounded hover:bg-white/[0.08] transition-colors">
            <Minus className="w-[14px] h-[14px] text-white/40" />
          </button>
          <button onClick={() => (window as any).electronAPI?.maximize()} className="w-[34px] h-[28px] flex items-center justify-center rounded hover:bg-white/[0.08] transition-colors">
            <Square className="w-[10px] h-[10px] text-white/40" />
          </button>
          <button onClick={() => (window as any).electronAPI?.close()} className="w-[34px] h-[28px] flex items-center justify-center rounded hover:bg-red-500/90 transition-colors group">
            <X className="w-[14px] h-[14px] text-white/40 group-hover:text-white" />
          </button>
        </div>
      </header>

      {/* ─── 主内容区 ─── */}
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        <main className="flex-1 flex flex-col min-w-0 relative">
          <ChatInterface />
        </main>
        <AgentPanel />
      </div>

      <SettingsDialog open={showSettings} onClose={() => setShowSettings(false)} />
    </div>
  );
}
