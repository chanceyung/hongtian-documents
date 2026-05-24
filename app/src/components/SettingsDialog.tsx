import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  Key,
  Sparkles,
  FileOutput,
  Check,
  AlertCircle,
  Loader2,
  Eye,
  EyeOff,
  Zap,
  Shield,
  Palette,
  Github,
} from "lucide-react";
import { trpc } from "@/providers/trpc";
import { useAuth } from "@/hooks/useAuth";

type Tab = "model" | "output" | "about";

interface SettingsDialogProps {
  open: boolean;
  onClose: () => void;
}

export default function SettingsDialog({ open, onClose }: SettingsDialogProps) {
  const [activeTab, setActiveTab] = useState<Tab>("model");
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [model, setModel] = useState("glm-4-flash");
  const [defaultFormat, setDefaultFormat] = useState<"pdf" | "pptx">("pdf");
  const [defaultTemplate, setDefaultTemplate] = useState("modern_tech");
  const [testStatus, setTestStatus] = useState<"idle" | "testing" | "success" | "error">("idle");
  const [testMessage, setTestMessage] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const { user } = useAuth();

  const utils = trpc.useUtils();
  const { data: settings } = trpc.settings.get.useQuery(undefined, { enabled: !!user && open });
  const saveSettings = trpc.settings.save.useMutation({
    onSuccess: (data: any) => {
      utils.settings.get.invalidate();
      setIsSaving(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
    onError: (err) => {
      setIsSaving(false);
      console.error("[Settings] Save failed:", err.message);
    },
  });
  const testKey = trpc.settings.testZhipuKey.useMutation({
    onSuccess: (data) => {
      setTestStatus(data.valid ? "success" : "error");
      setTestMessage(data.message);
    },
    onError: (err) => {
      setTestStatus("error");
      setTestMessage(err.message);
    },
  });

  useEffect(() => {
    if (settings) {
      if (settings.zhipuApiKey) setApiKey(settings.zhipuApiKey);
      if (settings.zhipuModel) setModel(settings.zhipuModel);
      if (settings.defaultFormat) setDefaultFormat(settings.defaultFormat as "pdf" | "pptx");
      if (settings.defaultTemplate) setDefaultTemplate(settings.defaultTemplate);
    }
  }, [settings]);

  const handleTestKey = () => {
    if (!apiKey.trim()) return;
    setTestStatus("testing");
    testKey.mutate({ apiKey: apiKey.trim() });
  };

  const handleSave = () => {
    setIsSaving(true);
    saveSettings.mutate({
      zhipuApiKey: apiKey.trim() || undefined,
      zhipuModel: model,
      defaultFormat,
      defaultTemplate,
    });
  };

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "model", label: "模型配置", icon: <Key className="w-3.5 h-3.5" /> },
    { id: "output", label: "导出设置", icon: <FileOutput className="w-3.5 h-3.5" /> },
    { id: "about", label: "关于", icon: <Sparkles className="w-3.5 h-3.5" /> },
  ];

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center"
          onClick={onClose}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />

          <motion.div
            initial={{ y: 24, opacity: 0, scale: 0.96 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ y: 24, opacity: 0, scale: 0.96 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            className="relative bg-[#0c1220] border border-white/[0.08] rounded-2xl shadow-2xl w-full max-w-[560px] mx-4 overflow-hidden"
            style={{ boxShadow: "0 32px 64px -16px rgba(0,0,0,0.6)" }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.05]">
              <h2 className="text-[15px] font-semibold text-slate-100">设置</h2>
              <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/[0.06] transition-colors">
                <X className="w-4 h-4 text-slate-500" />
              </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-white/[0.05] px-6">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-3 text-[12px] font-medium border-b-2 transition-all ${
                    activeTab === tab.id
                      ? "border-blue-500 text-blue-400"
                      : "border-transparent text-slate-500 hover:text-slate-300"
                  }`}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Content */}
            <div className="px-6 py-5 min-h-[300px]">
              {activeTab === "model" && (
                <div className="space-y-5">
                  {/* API Key */}
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Shield className="w-3.5 h-3.5 text-blue-400" />
                      <label className="text-[12px] font-medium text-slate-300">智谱 API Key</label>
                    </div>
                    <div className="relative">
                      <input
                        type={showKey ? "text" : "password"}
                        value={apiKey}
                        onChange={(e) => { setApiKey(e.target.value); setTestStatus("idle"); }}
                        placeholder="sk-xxxxxxxxxxxxxxxx"
                        className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-3.5 py-2.5 pr-24 text-[12px] text-slate-200 placeholder-slate-700 focus:outline-none focus:border-blue-500/30 focus:bg-white/[0.05] transition-all font-mono tracking-wide"
                      />
                      <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                        <button onClick={() => setShowKey(!showKey)} className="p-1.5 rounded-lg hover:bg-white/[0.06] transition-colors">
                          {showKey ? <EyeOff className="w-3.5 h-3.5 text-slate-600" /> : <Eye className="w-3.5 h-3.5 text-slate-600" />}
                        </button>
                        <button
                          onClick={handleTestKey}
                          disabled={!apiKey.trim() || testStatus === "testing"}
                          className="px-2.5 py-1 bg-blue-500/10 hover:bg-blue-500/15 disabled:opacity-30 text-blue-400 rounded-lg text-[11px] font-medium transition-colors border border-blue-500/10"
                        >
                          {testStatus === "testing" ? <Loader2 className="w-3 h-3 animate-spin" /> : "测试"}
                        </button>
                      </div>
                    </div>
                    {testStatus === "success" && (
                      <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-1.5 mt-2">
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                        <span className="text-[11px] text-emerald-400">{testMessage}</span>
                      </motion.div>
                    )}
                    {testStatus === "error" && (
                      <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-1.5 mt-2">
                        <AlertCircle className="w-3.5 h-3.5 text-red-400" />
                        <span className="text-[11px] text-red-400">{testMessage}</span>
                      </motion.div>
                    )}
                    <p className="text-[10px] text-slate-700 mt-2 leading-relaxed">
                      API Key 仅在本地加密存储，不会上传到任何第三方服务器
                    </p>
                  </div>

                  {/* Model Selection */}
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Zap className="w-3.5 h-3.5 text-amber-400" />
                      <label className="text-[12px] font-medium text-slate-300">模型选择</label>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      {[
                        { value: "glm-4-flash", label: "GLM-4-Flash", desc: "快速" },
                        { value: "glm-4", label: "GLM-4", desc: "标准" },
                        { value: "glm-4-plus", label: "GLM-4-Plus", desc: "增强" },
                      ].map((m) => (
                        <button
                          key={m.value}
                          onClick={() => setModel(m.value)}
                          className={`flex flex-col items-center gap-1 px-3 py-2.5 rounded-xl border text-center transition-all ${
                            model === m.value
                              ? "border-blue-500/30 bg-blue-500/[0.06] text-blue-400"
                              : "border-white/[0.06] bg-white/[0.02] text-slate-400 hover:border-white/[0.1]"
                          }`}
                        >
                          <span className="text-[11px] font-medium">{m.label}</span>
                          <span className="text-[9px] opacity-60">{m.desc}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "output" && (
                <div className="space-y-5">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <FileOutput className="w-3.5 h-3.5 text-emerald-400" />
                      <label className="text-[12px] font-medium text-slate-300">默认输出格式</label>
                    </div>
                    <div className="flex gap-2.5">
                      {(["pdf", "pptx"] as const).map((fmt) => (
                        <button
                          key={fmt}
                          onClick={() => setDefaultFormat(fmt)}
                          className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl border text-[12px] font-medium transition-all ${
                            defaultFormat === fmt
                              ? "border-blue-500/30 bg-blue-500/[0.06] text-blue-400"
                              : "border-white/[0.06] bg-white/[0.02] text-slate-400 hover:border-white/[0.1]"
                          }`}
                        >
                          <FileOutput className="w-4 h-4" />
                          {fmt.toUpperCase()}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Palette className="w-3.5 h-3.5 text-purple-400" />
                      <label className="text-[12px] font-medium text-slate-300">默认模板风格</label>
                    </div>
                    <select
                      value={defaultTemplate}
                      onChange={(e) => setDefaultTemplate(e.target.value)}
                      className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-3.5 py-2.5 text-[12px] text-slate-200 focus:outline-none focus:border-blue-500/30 transition-all appearance-none cursor-pointer"
                      style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236B7280' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`, backgroundRepeat: "no-repeat", backgroundPosition: "right 12px center" }}
                    >
                      <option value="modern_tech">现代科技</option>
                      <option value="business_professional">商务专业</option>
                      <option value="elegant_minimal">极简优雅</option>
                    </select>
                  </div>
                </div>
              )}

              {activeTab === "about" && (
                <div className="flex flex-col items-center py-6">
                  <div className="relative mb-5">
                    <div className="absolute inset-0 blur-2xl bg-gradient-to-br from-blue-500/15 to-purple-500/15 rounded-full" />
                    <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-br from-[#0f172a] to-[#1e293b] ring-1 ring-white/[0.08] flex items-center justify-center shadow-2xl">
                      <img src="/logo-white.png" alt="弘天文档" className="w-10 h-10 object-contain" />
                    </div>
                  </div>
                  <h3 className="text-[16px] font-bold text-slate-100 mb-0.5">弘天文档</h3>
                  <p className="text-[12px] text-slate-500 mb-6">杂志级文档重构智能体</p>
                  <div className="flex items-center gap-2 mb-6 px-3 py-1.5 rounded-full bg-white/[0.02] border border-white/[0.05]">
                    <Zap className="w-3 h-3 text-amber-400" />
                    <span className="text-[10px] text-slate-600">6 个 AI Agent 协作引擎</span>
                  </div>
                  <div className="text-[11px] text-slate-700 space-y-1 text-center">
                    <p>版本 1.0.0</p>
                    <p>支持 PDF / DOCX / XLSX / PPTX / MD</p>
                  </div>
                  <button className="flex items-center gap-1.5 mt-6 px-4 py-2 rounded-xl bg-white/[0.03] border border-white/[0.06] text-[11px] text-slate-500 hover:text-slate-300 hover:border-white/[0.1] transition-all">
                    <Github className="w-3.5 h-3.5" />
                    GitHub 开源项目
                  </button>
                </div>
              )}
            </div>

            {/* Footer */}
            {activeTab !== "about" && (
              <div className="flex justify-end gap-2.5 px-6 py-4 border-t border-white/[0.05]">
                <button onClick={onClose} className="px-4 py-2 text-[12px] text-slate-400 hover:text-slate-200 transition-colors rounded-lg hover:bg-white/[0.04]">
                  取消
                </button>
                <button
                  onClick={handleSave}
                  disabled={isSaving || saved}
                  className={`px-5 py-2 text-[12px] font-medium rounded-xl transition-all flex items-center gap-1.5 ${
                    saved
                      ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/20"
                      : "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/20"
                  }`}
                >
                  {saved ? <Check className="w-3.5 h-3.5" /> : isSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                  {saved ? "已保存" : isSaving ? "保存中" : "保存设置"}
                </button>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
