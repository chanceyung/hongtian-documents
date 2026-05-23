import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Paperclip,
  Bot,
  User,
  FileText,
  FileSpreadsheet,
  Presentation,
  X,
  Download,
  Sparkles,
  Loader2,
  Briefcase,
  Cpu,
  BarChart3,
  BookOpen,
  Palette,
  ArrowUp,
  Zap,
} from "lucide-react";
import { useStore } from "@/hooks/useStore";
import { trpc } from "@/providers/trpc";
import { useAuth } from "@/hooks/useAuth";

const FILE_COLORS: Record<string, string> = {
  pdf: "#EF4444",
  docx: "#3B82F6",
  xlsx: "#10B981",
  pptx: "#F59E0B",
  md: "#8B5CF6",
};

const FILE_ICONS: Record<string, React.ReactNode> = {
  pdf: <FileText className="w-4 h-4" />,
  docx: <FileText className="w-4 h-4" />,
  xlsx: <FileSpreadsheet className="w-4 h-4" />,
  pptx: <Presentation className="w-4 h-4" />,
  md: <FileText className="w-4 h-4" />,
};

const TEMPLATES = [
  { title: "商务报告", desc: "专业严谨，数据驱动", icon: Briefcase, color: "from-blue-500/80 to-indigo-600/80", glow: "hover:shadow-blue-500/10" },
  { title: "科技杂志", desc: "现代创新，视觉冲击", icon: Cpu, color: "from-cyan-500/80 to-blue-600/80", glow: "hover:shadow-cyan-500/10" },
  { title: "极简优雅", desc: "简洁留白，高级感", icon: Sparkles, color: "from-slate-400/80 to-gray-500/80", glow: "hover:shadow-slate-400/10" },
  { title: "数据看板", desc: "图表可视化，洞察力", icon: BarChart3, color: "from-emerald-500/80 to-green-600/80", glow: "hover:shadow-emerald-500/10" },
  { title: "学术论刊", desc: "规范引用，学术性", icon: BookOpen, color: "from-violet-500/80 to-purple-600/80", glow: "hover:shadow-violet-500/10" },
  { title: "品牌画册", desc: "品牌视觉，故事性", icon: Palette, color: "from-rose-500/80 to-pink-600/80", glow: "hover:shadow-rose-500/10" },
];

export default function ChatInterface() {
  const {
    messages,
    inputText,
    attachments,
    activeConversationId,
    activeTask,
    setInputText,
    setAttachments,
    addMessage,
    setActiveTask,
  } = useStore();
  const { user } = useAuth();
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const pendingFiles = useRef<File[]>([]);

  const utils = trpc.useUtils();
  const createMessage = trpc.message.create.useMutation();
  const createTask = trpc.task.create.useMutation();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [inputText]);

  const handleFileSelect = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setIsUploading(true);
    try {
      for (const file of Array.from(files)) {
        const ext = file.name.split(".").pop()?.toLowerCase() || "";
        const sizeKB = (file.size / 1024).toFixed(1);
        pendingFiles.current.push(file);
        useStore.getState().addAttachment({
          fileName: file.name,
          fileSize: `${sizeKB} KB`,
          fileType: ext,
          fileUrl: "",
        });
      }
    } catch (err) {
      console.error("File select error:", err);
    }
    setIsUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const handleSend = async () => {
    if (!inputText.trim() && attachments.length === 0) return;
    if (!activeConversationId) return;
    if (!user) return;
    setIsSending(true);

    const userContent = inputText.trim() || "请处理上传的文件";
    const currentAttachments = attachments.length > 0 ? [...attachments] : undefined;
    const filesToSend = [...pendingFiles.current];

    addMessage({
      id: `local-${Date.now()}`,
      role: "user",
      content: userContent,
      attachments: currentAttachments,
      createdAt: new Date(),
    });
    setInputText("");
    setAttachments([]);
    pendingFiles.current = [];

    try {
      await createMessage.mutateAsync({
        conversationId: activeConversationId,
        role: "user",
        content: userContent,
        attachments: currentAttachments ? JSON.stringify(currentAttachments) : undefined,
      });

      let pythonTaskId: string | undefined;
      const settings = await utils.settings.get.fetch();
      const outputFormat = settings?.defaultFormat || "pdf";

      // Upload files to Python backend
      if (filesToSend.length > 0) {
        const formData = new FormData();
        formData.append("file", filesToSend[0]);
        const uploadResp = await fetch(`/api/magazine/upload?session_id=desktop`, {
          method: "POST",
          body: formData,
        });
        if (!uploadResp.ok) {
          const errText = await uploadResp.text();
          throw new Error(`上传失败 (${uploadResp.status}): ${errText}`);
        }
        const uploadResult = await uploadResp.json();
        pythonTaskId = uploadResult.task_id;
      }

      // Create task in local DB for UI tracking
      const task = await createTask.mutateAsync({
        conversationId: activeConversationId,
        outputFormat: outputFormat as "pdf" | "pptx",
      });

      const agentStates = [
        { id: "", agentType: "parser", name: "解析 Agent", color: "#06B6D4", status: "pending" as const, progress: 0, logs: [], isExpanded: false },
        { id: "", agentType: "analyzer", name: "分析 Agent", color: "#8B5CF6", status: "pending" as const, progress: 0, logs: [], isExpanded: false },
        { id: "", agentType: "designer", name: "设计 Agent", color: "#EC4899", status: "pending" as const, progress: 0, logs: [], isExpanded: false },
        { id: "", agentType: "renderer", name: "渲染 Agent", color: "#F59E0B", status: "pending" as const, progress: 0, logs: [], isExpanded: false },
        { id: "", agentType: "fidelity", name: "校验 Agent", color: "#10B981", status: "pending" as const, progress: 0, logs: [], isExpanded: false },
      ];
      setActiveTask({
        id: task.id,
        status: "running",
        progress: 0,
        outputFormat: outputFormat as "pdf" | "pptx",
        pythonTaskId,
        agentStates,
      });

      // Start real pipeline via generate endpoint
      if (pythonTaskId) {
        await fetch(`/api/magazine/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            task_id: pythonTaskId,
            session_id: "desktop",
            output_format: outputFormat,
            template_id: settings?.defaultTemplate || "modern_tech",
          }),
        });
      }
    } catch (err) {
      console.error("Send error:", err);
      addMessage({
        id: `err-${Date.now()}`,
        role: "assistant",
        content: `操作失败: ${err instanceof Error ? err.message : "请稍后重试"}`,
        createdAt: new Date(),
      });
    }
    setIsSending(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleTemplateClick = (template: typeof TEMPLATES[0]) => {
    setInputText(`请使用「${template.title}」风格处理这份文件，输出 magazine 级别的精美排版`);
  };

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        <div className="flex-1 overflow-y-auto">
          <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
            {/* Logo with glow */}
            <motion.div
              initial={{ scale: 0.7, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              className="relative mb-6"
            >
              <div className="absolute inset-0 blur-2xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-full" />
              <div className="relative w-[72px] h-[72px] rounded-2xl bg-gradient-to-br from-[#0f172a] to-[#1e293b] ring-1 ring-white/[0.08] flex items-center justify-center shadow-2xl">
                <img src="/logo-white.png" alt="弘天文档" className="w-11 h-11 object-contain" />
              </div>
            </motion.div>

            {/* Title */}
            <motion.h1
              initial={{ y: 12, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.1, duration: 0.4 }}
              className="text-[26px] font-bold text-slate-100 tracking-tight mb-1.5"
            >
              弘天文档
            </motion.h1>
            <motion.p
              initial={{ y: 12, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.18, duration: 0.4 }}
              className="text-[13px] text-slate-500 mb-2 text-center"
            >
              杂志级文档重构智能体
            </motion.p>
            <motion.div
              initial={{ y: 12, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.24, duration: 0.4 }}
              className="flex items-center gap-1.5 mb-10 px-3 py-1 rounded-full bg-white/[0.03] border border-white/[0.05]"
            >
              <Zap className="w-3 h-3 text-amber-400" />
              <span className="text-[11px] text-slate-500">6 个 AI Agent 协作完成重构</span>
            </motion.div>

            {/* Template Cards */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.32, duration: 0.4 }}
              className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 max-w-[540px] w-full"
            >
              {TEMPLATES.map((template, i) => {
                const Icon = template.icon;
                return (
                  <motion.button
                    key={template.title}
                    initial={{ y: 16, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.38 + i * 0.06 }}
                    onClick={() => handleTemplateClick(template)}
                    className={`group relative flex flex-col items-start gap-2.5 p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:border-white/[0.12] transition-all text-left card-lift ${template.glow} hover:shadow-lg overflow-hidden`}
                  >
                    <div className={`absolute inset-0 bg-gradient-to-br ${template.color} opacity-0 group-hover:opacity-[0.07] transition-opacity duration-300`} />
                    <div className={`relative w-9 h-9 rounded-lg bg-gradient-to-br ${template.color} flex items-center justify-center shadow-lg`}>
                      <Icon className="w-4 h-4 text-white" />
                    </div>
                    <div className="relative">
                      <p className="text-[12px] font-medium text-slate-300 group-hover:text-slate-100 transition-colors">
                        {template.title}
                      </p>
                      <p className="text-[10px] text-slate-600 group-hover:text-slate-500 transition-colors mt-0.5">
                        {template.desc}
                      </p>
                    </div>
                  </motion.button>
                );
              })}
            </motion.div>

            {/* Bottom hint */}
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.8 }}
              className="text-[11px] text-slate-700 mt-8"
            >
              拖拽文件到下方输入框，或直接描述需求
            </motion.p>
          </div>
        </div>
        <InputArea {...{ inputText, attachments, isUploading, isSending, isDragging, setInputText, setIsDragging, handleFileSelect, handleSend, handleKeyDown, handleDrop, fileInputRef, textareaRef }} />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden relative">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 space-y-5">
        <AnimatePresence>
          {messages.map((msg, index) => (
            <motion.div
              key={msg.id}
              initial={{ y: 16, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.35, ease: "easeOut" }}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "assistant" && (
                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shrink-0 mr-3 mt-0.5 shadow-lg shadow-blue-500/15 ring-1 ring-white/10">
                  <Bot className="w-4 h-4 text-white" />
                </div>
              )}

              <div className={`max-w-[78%] ${msg.role === "user" ? "order-1" : "order-2"}`}>
                {/* User bubble */}
                {msg.role === "user" && (
                  <div className="bg-white/[0.06] border border-white/[0.08] rounded-2xl rounded-tr-md px-4 py-3 backdrop-blur-sm">
                    {msg.attachments && msg.attachments.length > 0 && (
                      <div className="flex flex-wrap gap-2 mb-2.5">
                        {msg.attachments.map((att, i) => {
                          const color = FILE_COLORS[att.fileType] || "#6B7280";
                          return (
                            <div key={i} className="flex items-center gap-2 bg-white/[0.04] border border-white/[0.06] rounded-lg px-2.5 py-1.5">
                              <div className="w-7 h-7 rounded-md flex items-center justify-center shrink-0" style={{ backgroundColor: `${color}18`, color }}>
                                {FILE_ICONS[att.fileType] || <FileText className="w-3.5 h-3.5" />}
                              </div>
                              <div className="min-w-0">
                                <p className="text-[11px] font-medium text-slate-300 truncate max-w-[160px]">{att.fileName}</p>
                                <p className="text-[9px] text-slate-600">{att.fileSize}</p>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                    <p className="text-[13px] text-slate-200 leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  </div>
                )}

                {/* AI message */}
                {msg.role === "assistant" && (
                  <div className="bg-transparent">
                    <p className="text-[13px] text-slate-300 leading-relaxed whitespace-pre-wrap">{msg.content}</p>

                    {/* Result card */}
                    {activeTask?.status === "completed" && index === messages.length - 1 && (
                      <motion.div
                        initial={{ scale: 0.96, opacity: 0, y: 8 }}
                        animate={{ scale: 1, opacity: 1, y: 0 }}
                        transition={{ duration: 0.4, delay: 0.15 }}
                        className="mt-4 bg-[#0c1220] border border-white/[0.08] rounded-2xl overflow-hidden shadow-xl shadow-black/20 gradient-border"
                      >
                        <div className="h-40 bg-gradient-to-br from-[#0a0f1c] to-[#0f172a] flex items-center justify-center relative overflow-hidden">
                          <div className="absolute inset-0 opacity-30">
                            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 rounded-full blur-3xl" style={{ background: activeTask.outputFormat === "pdf" ? "rgba(239,68,68,0.15)" : "rgba(245,158,11,0.15)" }} />
                          </div>
                          <div className="relative text-center">
                            <div className="w-14 h-14 mx-auto rounded-2xl flex items-center justify-center mb-3" style={{ backgroundColor: activeTask.outputFormat === "pdf" ? "rgba(239,68,68,0.12)" : "rgba(245,158,11,0.12)" }}>
                              {activeTask.outputFormat === "pdf" ? (
                                <FileText className="w-7 h-7 text-red-400" />
                              ) : (
                                <Presentation className="w-7 h-7 text-amber-400" />
                              )}
                            </div>
                            <p className="text-[12px] text-slate-500 font-medium">
                              {activeTask.outputFormat.toUpperCase()} 文件已生成
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center justify-between px-5 py-3.5 border-t border-white/[0.05]">
                          <div>
                            <p className="text-[13px] font-medium text-slate-200">
                              output_{activeTask.id}.{activeTask.outputFormat}
                            </p>
                            <span className="inline-block mt-1 text-[10px] px-2 py-[3px] rounded-md font-medium" style={{ backgroundColor: activeTask.outputFormat === "pdf" ? "rgba(239,68,68,0.1)" : "rgba(245,158,11,0.1)", color: activeTask.outputFormat === "pdf" ? "#f87171" : "#fbbf24" }}>
                              {activeTask.outputFormat.toUpperCase()}
                            </span>
                          </div>
                          <button
                            onClick={() => {
                              const pid = activeTask?.pythonTaskId;
                              if (pid) window.open(`/api/magazine/export/${pid}`, "_blank");
                            }}
                            className="flex items-center gap-1.5 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-[12px] font-medium rounded-xl transition-all shadow-lg shadow-blue-600/20 hover:shadow-blue-500/30"
                          >
                            <Download className="w-3.5 h-3.5" />
                            下载
                          </button>
                        </div>
                      </motion.div>
                    )}
                  </div>
                )}
              </div>

              {msg.role === "user" && (
                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-slate-600 to-slate-700 flex items-center justify-center shrink-0 ml-3 mt-0.5 order-2 ring-1 ring-white/10">
                  <User className="w-4 h-4 text-slate-300" />
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Typing indicator */}
        {isSending && messages[messages.length - 1]?.role === "user" && (
          <motion.div
            initial={{ y: 10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="flex items-start gap-3"
          >
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shrink-0 shadow-lg shadow-blue-500/15 ring-1 ring-white/10">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div className="bg-white/[0.04] border border-white/[0.06] rounded-2xl rounded-tl-md px-4 py-3 min-w-[64px]">
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 bg-slate-500 rounded-full typing-dot" />
                <div className="w-1.5 h-1.5 bg-slate-500 rounded-full typing-dot" />
                <div className="w-1.5 h-1.5 bg-slate-500 rounded-full typing-dot" />
              </div>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <InputArea {...{ inputText, attachments, isUploading, isSending, isDragging, setInputText, setIsDragging, handleFileSelect, handleSend, handleKeyDown, handleDrop, fileInputRef, textareaRef }} />
    </div>
  );
}

function InputArea({
  inputText, attachments, isUploading, isSending, isDragging,
  setInputText, setIsDragging, handleFileSelect, handleSend, handleKeyDown, handleDrop,
  fileInputRef, textareaRef,
}: {
  inputText: string;
  attachments: { fileName: string; fileSize: string; fileType: string; fileUrl: string }[];
  isUploading: boolean;
  isSending: boolean;
  isDragging: boolean;
  setInputText: (t: string) => void;
  setIsDragging: (d: boolean) => void;
  handleFileSelect: (files: FileList | null) => void;
  handleSend: () => void;
  handleKeyDown: (e: React.KeyboardEvent) => void;
  handleDrop: (e: React.DragEvent) => void;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
}) {
  const { removeAttachment } = useStore();
  const canSend = (inputText.trim() || attachments.length > 0) && !isSending;

  return (
    <div className="shrink-0 px-4 md:px-8 pb-5 pt-2 relative">
      <AnimatePresence>
        {attachments.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="flex flex-wrap gap-2 mb-2 px-1"
          >
            {attachments.map((att, i) => {
              const color = FILE_COLORS[att.fileType] || "#6B7280";
              return (
                <motion.div
                  key={i}
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.9, opacity: 0 }}
                  className="flex items-center gap-2 bg-white/[0.04] border border-white/[0.08] rounded-lg px-2.5 py-1.5 backdrop-blur-sm"
                >
                  <div className="w-6 h-6 rounded-md flex items-center justify-center" style={{ backgroundColor: `${color}18`, color }}>
                    {FILE_ICONS[att.fileType] || <FileText className="w-3 h-3" />}
                  </div>
                  <span className="text-[11px] text-slate-400 max-w-[140px] truncate">{att.fileName}</span>
                  <button onClick={() => removeAttachment(i)} className="p-0.5 rounded hover:bg-white/[0.06] transition-colors">
                    <X className="w-3 h-3 text-slate-600 hover:text-red-400 transition-colors" />
                  </button>
                </motion.div>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>

      <div
        className={`relative bg-[#0c1220]/80 border rounded-2xl transition-all duration-200 backdrop-blur-xl ${
          isDragging ? "border-blue-500/50 shadow-lg shadow-blue-500/10" : "border-white/[0.08] focus-within:border-white/[0.14] focus-within:shadow-lg focus-within:shadow-black/20"
        }`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        <div className="flex items-end gap-1.5 px-3 py-2.5">
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="p-2.5 rounded-xl hover:bg-white/[0.06] transition-colors shrink-0 self-end"
          >
            {isUploading ? <Loader2 className="w-[18px] h-[18px] text-slate-500 animate-spin" /> : <Paperclip className="w-[18px] h-[18px] text-slate-500 hover:text-slate-300 transition-colors" />}
          </button>
          <input ref={fileInputRef} type="file" multiple accept=".pdf,.docx,.xlsx,.pptx,.md" className="hidden" onChange={(e) => handleFileSelect(e.target.files)} />
          <textarea
            ref={textareaRef}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="描述你想要的排版风格，或上传文件开始..."
            rows={1}
            className="flex-1 bg-transparent text-[13px] text-slate-200 placeholder-slate-600 resize-none focus:outline-none py-2.5 min-h-[40px] max-h-[160px] leading-relaxed"
          />
          <button
            onClick={handleSend}
            disabled={!canSend}
            className={`p-2.5 rounded-xl shrink-0 self-end transition-all ${
              canSend ? "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/20 hover:shadow-blue-500/30 hover:scale-105 active:scale-95" : "bg-white/[0.04] text-slate-700 cursor-not-allowed"
            }`}
          >
            {isSending ? <Loader2 className="w-[18px] h-[18px] animate-spin" /> : <ArrowUp className="w-[18px] h-[18px]" />}
          </button>
        </div>

        {isDragging && (
          <div className="absolute inset-0 bg-blue-500/[0.03] border-2 border-dashed border-blue-500/40 rounded-2xl flex items-center justify-center backdrop-blur-sm">
            <p className="text-[13px] text-blue-400 font-medium flex items-center gap-2">
              <Paperclip className="w-4 h-4" />
              释放以上传文件
            </p>
          </div>
        )}
      </div>

      <p className="text-[10px] text-slate-800 mt-2 text-center tracking-wide">
        支持 PDF、Word、Excel、PPT、Markdown
      </p>
    </div>
  );
}
