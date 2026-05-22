import { motion, AnimatePresence } from "framer-motion";
import {
  Bot,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  PanelRightClose,
  RotateCcw,
  X,
  Activity,
} from "lucide-react";
import { useStore } from "@/hooks/useStore";
import { trpc } from "@/providers/trpc";
import { useState, useEffect } from "react";

const AGENT_CONFIG: Record<string, { name: string; color: string; gradient: string }> = {
  coordinator: { name: "协调 Agent", color: "#3B82F6", gradient: "from-blue-500 to-blue-600" },
  parser: { name: "解析 Agent", color: "#06B6D4", gradient: "from-cyan-500 to-cyan-600" },
  analyzer: { name: "分析 Agent", color: "#8B5CF6", gradient: "from-violet-500 to-violet-600" },
  designer: { name: "设计 Agent", color: "#EC4899", gradient: "from-pink-500 to-pink-600" },
  renderer: { name: "渲染 Agent", color: "#F59E0B", gradient: "from-amber-500 to-amber-600" },
  fidelity: { name: "校验 Agent", color: "#10B981", gradient: "from-emerald-500 to-emerald-600" },
};

export default function AgentPanel() {
  const { isAgentPanelOpen, toggleAgentPanel, activeTask, setActiveTask } = useStore();
  const [expandedAgents, setExpandedAgents] = useState<Set<string>>(new Set());

  const { data: agentStatesData } = trpc.task.getAgentStates.useQuery(
    { taskId: activeTask?.id || 0 },
    { enabled: !!activeTask?.id && activeTask.status === "running", refetchInterval: 500 }
  );

  useEffect(() => {
    if (agentStatesData && activeTask) {
      const updatedAgents = activeTask.agentStates.map((agent) => {
        const backendState = agentStatesData.find((s) => s.agentType === agent.agentType);
        if (backendState) {
          return {
            ...agent,
            status: backendState.status as "pending" | "running" | "completed" | "error",
            progress: backendState.progress,
            logs: backendState.logs ? JSON.parse(backendState.logs) : [],
          };
        }
        return agent;
      });
      const taskProgress = Math.round(updatedAgents.reduce((sum, a) => sum + a.progress, 0) / updatedAgents.length);
      setActiveTask({ ...activeTask, agentStates: updatedAgents, progress: taskProgress });
    }
  }, [agentStatesData]);

  const toggleExpand = (agentType: string) => {
    setExpandedAgents((prev) => {
      const next = new Set(prev);
      if (next.has(agentType)) next.delete(agentType);
      else next.add(agentType);
      return next;
    });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "running": return <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400" />;
      case "completed": return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
      case "error": return <XCircle className="w-3.5 h-3.5 text-red-400" />;
      default: return <Clock className="w-3.5 h-3.5 text-slate-600" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case "running": return "执行中...";
      case "completed": return "已完成";
      case "error": return "执行出错";
      default: return "等待中";
    }
  };

  if (!isAgentPanelOpen) {
    return (
      <motion.button
        initial={{ x: 20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        onClick={toggleAgentPanel}
        className="fixed right-0 top-1/2 -translate-y-1/2 z-30 bg-[#0c1220]/90 backdrop-blur-md border border-white/[0.08] border-r-0 rounded-l-xl p-2.5 transition-all hover:bg-[#111827]/90 group"
      >
        <PanelRightClose className="w-4 h-4 text-slate-500 group-hover:text-slate-300 transition-colors" />
      </motion.button>
    );
  }

  return (
    <motion.div
      initial={{ width: 0, opacity: 0 }}
      animate={{ width: 316, opacity: 1 }}
      exit={{ width: 0, opacity: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="h-full bg-[#0a0f1c]/60 backdrop-blur-md border-l border-white/[0.05] flex flex-col shrink-0 overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.05]">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center ring-1 ring-white/[0.06]">
            <Activity className="w-3.5 h-3.5 text-blue-400" />
          </div>
          <span className="text-[13px] font-semibold text-slate-200">任务进程</span>
        </div>
        <div className="flex items-center gap-1.5">
          {activeTask && (
            <span className={`text-[10px] px-2 py-[3px] rounded-md font-medium ${
              activeTask.status === "running" ? "bg-blue-500/10 text-blue-400" :
              activeTask.status === "completed" ? "bg-emerald-500/10 text-emerald-400" :
              activeTask.status === "failed" ? "bg-red-500/10 text-red-400" :
              "bg-slate-500/10 text-slate-500"
            }`}>
              {activeTask.status === "running" ? "进行中" :
               activeTask.status === "completed" ? "已完成" :
               activeTask.status === "failed" ? "失败" : "待开始"}
            </span>
          )}
          <button onClick={toggleAgentPanel} className="p-1.5 rounded-lg hover:bg-white/[0.06] transition-colors">
            <X className="w-3.5 h-3.5 text-slate-500" />
          </button>
        </div>
      </div>

      {/* Overall Progress */}
      {activeTask && (
        <div className="px-4 py-3 border-b border-white/[0.05]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] text-slate-500 font-medium">总进度</span>
            <span className="text-[11px] font-semibold text-blue-400 tabular-nums">{activeTask.progress}%</span>
          </div>
          <div className="w-full h-[6px] bg-white/[0.04] rounded-full overflow-hidden">
            <motion.div
              className="h-full rounded-full progress-shimmer"
              style={{ background: "linear-gradient(90deg, #3B82F6, #8B5CF6, #3B82F6)", backgroundSize: "200% 100%" }}
              initial={{ width: 0 }}
              animate={{ width: `${activeTask.progress}%` }}
              transition={{ duration: 0.6, ease: "easeOut" }}
            />
          </div>
        </div>
      )}

      {/* Agent List */}
      <div className="flex-1 overflow-y-auto px-3 py-2.5 space-y-1.5">
        <AnimatePresence>
          {activeTask?.agentStates.map((agent) => {
            const config = AGENT_CONFIG[agent.agentType] || { name: agent.agentType, color: "#6B7280", gradient: "from-gray-500 to-gray-600" };
            const isExpanded = expandedAgents.has(agent.agentType);
            const isRunning = agent.status === "running";

            return (
              <motion.div
                key={agent.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className={`rounded-xl p-3 transition-all ${
                  isRunning ? "bg-white/[0.04] border border-white/[0.08]" : "bg-white/[0.02] border border-transparent"
                }`}
              >
                {/* Agent Header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className={`w-7 h-7 rounded-lg bg-gradient-to-br ${config.gradient} flex items-center justify-center shrink-0 shadow-lg ${isRunning ? "animate-pulse" : ""}`} style={{ boxShadow: `0 0 12px -2px ${config.color}40` }}>
                      <Bot className="w-3.5 h-3.5 text-white" />
                    </div>
                    <div>
                      <span className="text-[11px] font-medium text-slate-300">{config.name}</span>
                      <p className="text-[9px] text-slate-600 mt-0.5">{getStatusText(agent.status)}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    {getStatusIcon(agent.status)}
                    <button onClick={() => toggleExpand(agent.agentType)} className="p-1 rounded-md hover:bg-white/[0.06] transition-colors ml-0.5">
                      {isExpanded ? <ChevronUp className="w-3 h-3 text-slate-600" /> : <ChevronDown className="w-3 h-3 text-slate-600" />}
                    </button>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="mt-2.5">
                  <div className="w-full h-[4px] bg-white/[0.04] rounded-full overflow-hidden">
                    <motion.div
                      className="h-full rounded-full progress-shimmer"
                      style={{ backgroundColor: config.color, boxShadow: `0 0 8px ${config.color}40` }}
                      initial={{ width: 0 }}
                      animate={{ width: `${agent.progress}%` }}
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                </div>

                {/* Logs */}
                <AnimatePresence>
                  {isExpanded && agent.logs.length > 0 && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="mt-2.5 bg-[#060b14] rounded-lg p-2.5 max-h-[100px] overflow-y-auto border border-white/[0.04]">
                        {agent.logs.map((log, i) => (
                          <p key={i} className="text-[10px] font-mono text-slate-600 leading-relaxed">
                            <span className="text-slate-700 mr-1.5">{String(i + 1).padStart(2, "0")}</span>
                            {log}
                          </p>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {!activeTask && (
          <div className="flex flex-col items-center justify-center h-48 text-slate-700">
            <div className="w-14 h-14 rounded-2xl bg-white/[0.02] flex items-center justify-center mb-3 ring-1 ring-white/[0.04]">
              <Bot className="w-7 h-7 opacity-20" />
            </div>
            <p className="text-[12px] font-medium">暂无任务</p>
            <p className="text-[10px] mt-1 opacity-60">在左侧上传文件开始</p>
          </div>
        )}
      </div>

      {/* Bottom Actions */}
      {activeTask && (
        <div className="px-3 py-2.5 border-t border-white/[0.05] flex gap-2">
          {activeTask.status === "running" && (
            <button className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-red-500/[0.08] hover:bg-red-500/[0.12] text-red-400 rounded-xl text-[11px] font-medium transition-colors border border-red-500/[0.1]">
              <X className="w-3 h-3" />
              取消任务
            </button>
          )}
          {activeTask.status === "completed" && (
            <button className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-blue-500/[0.08] hover:bg-blue-500/[0.12] text-blue-400 rounded-xl text-[11px] font-medium transition-colors border border-blue-500/[0.1]">
              <RotateCcw className="w-3 h-3" />
              重新生成
            </button>
          )}
        </div>
      )}
    </motion.div>
  );
}
