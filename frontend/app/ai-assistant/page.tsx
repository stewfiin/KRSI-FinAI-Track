"use client";

import { useState, useRef, useEffect } from "react";
import {
  Bot,
  User as UserIcon,
  Sparkles,
  Send,
  Mic,
  Square,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Receipt,
  Wallet,
  Sliders,
  Save,
} from "lucide-react";
import { api } from "@/lib/api";

interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  transaction?: any;
  budgetAlert?: any;
  time: string;
}

export default function AIAssistantPage() {
  const [activeTab, setActiveTab] = useState<"chat" | "budget">("chat");

  // ===========================================================================
  // Chat State
  // ===========================================================================
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "initial",
      sender: "assistant",
      text: "Halo! Saya asisten FinAI Track. Anda bisa langsung mengetik atau mengirim rekaman suara untuk mencatat transaksi (contoh: *'Beli kopi 25rb pakai Tunai'*), atau menanyakan kondisi keuangan Anda!",
      time: new Date().toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [inputText, setInputText] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Voice recording timer
  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => setRecordSeconds((p) => p + 1), 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      setRecordSeconds(0);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isRecording]);

  const handleSendMessage = async () => {
    if (!inputText.trim() || isChatLoading) return;
    const userText = inputText.trim();
    setInputText("");

    const newMsg: ChatMessage = {
      id: String(Date.now()),
      sender: "user",
      text: userText,
      time: new Date().toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages((prev) => [...prev, newMsg]);
    setIsChatLoading(true);

    try {
      const res = await api.post("/api/ai/chat", {
        message: userText,
        platform: "web",
      });

      const assistantMsg: ChatMessage = {
        id: String(Date.now() + 1),
        sender: "assistant",
        text: res.data.reply,
        transaction: res.data.transaction,
        budgetAlert: res.data.budget_alert,
        time: new Date().toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: String(Date.now() + 1),
          sender: "assistant",
          text: err.response?.data?.detail || "Maaf, terjadi kendala saat memproses permintaan Anda.",
          time: new Date().toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const startVoiceRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        stream.getTracks().forEach((track) => track.stop());
        await sendVoiceBlob(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      alert("Akses mikrofon ditolak atau perangkat tidak mendukung perekaman audio.");
    }
  };

  const stopVoiceRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const sendVoiceBlob = async (blob: Blob) => {
    setIsChatLoading(true);
    const formData = new FormData();
    formData.append("file", blob, "assistant_voice.webm");
    formData.append("platform", "web");

    try {
      const res = await api.post("/api/ai/voice", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      // Tambahkan pesan User transkrip
      setMessages((prev) => [
        ...prev,
        {
          id: String(Date.now()),
          sender: "user",
          text: `🎙️ "${res.data.transcript}"`,
          time: new Date().toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }),
        },
        {
          id: String(Date.now() + 1),
          sender: "assistant",
          text: res.data.chat_result.reply,
          transaction: res.data.chat_result.transaction,
          budgetAlert: res.data.chat_result.budget_alert,
          time: new Date().toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: String(Date.now() + 1),
          sender: "assistant",
          text: err.response?.data?.detail || "Gagal memproses rekaman suara Anda.",
          time: new Date().toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setIsChatLoading(false);
    }
  };

  // ===========================================================================
  // Smart Budget State
  // ===========================================================================
  const [budgetPrompt, setBudgetPrompt] = useState(
    "Gaji saya 6 juta per bulan, saya ingin mengalokasikan tabungan 1.5 juta, dan tolong hemat di pos makanan & hiburan."
  );
  const [isBudgetLoading, setIsBudgetLoading] = useState(false);
  const [budgetPlan, setBudgetPlan] = useState<any | null>(null);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  const handleGenerateBudget = async () => {
    if (!budgetPrompt.trim() || isBudgetLoading) return;
    setIsBudgetLoading(true);
    setSaveSuccessMsg(null);

    try {
      const res = await api.post("/api/ai/budget", {
        prompt: budgetPrompt.trim(),
        apply_to_database: false,
      });
      setBudgetPlan(res.data);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Gagal membuat rekomendasi anggaran.");
    } finally {
      setIsBudgetLoading(false);
    }
  };

  const handleSaveBudgetToDb = async () => {
    if (!budgetPlan || isBudgetLoading) return;
    setIsBudgetLoading(true);
    setSaveSuccessMsg(null);

    try {
      await api.post("/api/ai/budget", {
        prompt: budgetPrompt.trim(),
        apply_to_database: true,
      });
      setSaveSuccessMsg("✅ Alokasi anggaran bulanan berhasil disimpan ke database!");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Gagal menyimpan anggaran ke database.");
    } finally {
      setIsBudgetLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header & Tabs Navigation */}
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-[#C8F526] animate-pulse" />
          <h1 className="text-xl font-black tracking-tight text-espresso flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-espresso" />
            AI Finance Assistant
          </h1>
        </div>

        {/* Tab Toggle */}
        <div className="flex rounded-2xl bg-white p-1 border border-surface-border shadow-xs text-xs font-bold">
          <button
            type="button"
            onClick={() => setActiveTab("chat")}
            className={`rounded-xl px-4 py-2 transition ${
              activeTab === "chat"
                ? "bg-[#0D0F17] text-[#C8F526] shadow-sm font-black"
                : "text-espresso-muted hover:text-espresso"
            }`}
          >
            Obrolan AI
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("budget")}
            className={`rounded-xl px-4 py-2 transition ${
              activeTab === "budget"
                ? "bg-[#0D0F17] text-[#C8F526] shadow-sm font-black"
                : "text-espresso-muted hover:text-espresso"
            }`}
          >
            Smart Budgeting
          </button>
        </div>
      </div>

      {/* ===================================================================== */}
      {/* TAB 1: AI CHAT ASSISTANT */}
      {/* ===================================================================== */}
      {activeTab === "chat" && (
        <div className="flex h-[75vh] flex-col rounded-3xl border border-surface-border bg-white shadow-xs overflow-hidden">
          {/* Chat Messages Scrollable Box */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.sender === "assistant" && (
                  <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-2xl bg-[#0D0F17] text-[#C8F526] shadow-xs">
                    <Bot className="h-4 w-4" />
                  </div>
                )}

                <div className={`max-w-[85%] sm:max-w-md space-y-2`}>
                  <div
                    className={`rounded-2xl px-4 py-3 text-xs leading-relaxed ${
                      msg.sender === "user"
                        ? "bg-[#0D0F17] text-white shadow-md rounded-tr-none font-medium"
                        : "border border-surface-border bg-surface-card text-espresso rounded-tl-none font-medium shadow-2xs"
                    }`}
                  >
                    <p className="whitespace-pre-line">{msg.text}</p>
                    <span className="mt-1 block text-right text-[10px] opacity-60">
                      {msg.time}
                    </span>
                  </div>

                  {/* Transaction Preview Card (Jika ada transaksi tercatat) */}
                  {msg.transaction && (
                    <div className="rounded-2xl border border-income/30 bg-income/10 p-3.5 text-xs shadow-xs space-y-2">
                      <div className="flex items-center gap-1.5 text-income font-bold">
                        <CheckCircle2 className="h-4 w-4" />
                        <span>Transaksi Berhasil Disimpan</span>
                      </div>
                      <div className="space-y-1 text-espresso">
                        <div className="flex justify-between">
                          <span className="text-espresso-muted">Deskripsi:</span>
                          <span className="font-semibold">{msg.transaction.description}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-espresso-muted">Nominal:</span>
                          <span className="font-bold text-income">
                            Rp{parseFloat(msg.transaction.amount).toLocaleString("id-ID")}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-espresso-muted">Kategori / Dompet:</span>
                          <span className="font-medium">
                            {msg.transaction.category_name} ({msg.transaction.wallet_name})
                          </span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Budget Alert Card */}
                  {msg.budgetAlert && (
                    <div className="flex items-center gap-2 rounded-2xl border border-amber-400/40 bg-amber-400/10 p-3 text-xs text-espresso">
                      <AlertTriangle className="h-4 w-4 flex-shrink-0 text-amber-600" />
                      <span>{msg.budgetAlert.message}</span>
                    </div>
                  )}
                </div>

                {msg.sender === "user" && (
                  <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-2xl bg-[#0D0F17] text-white shadow-xs">
                    <UserIcon className="h-4 w-4" />
                  </div>
                )}
              </div>
            ))}
            {isChatLoading && (
              <div className="flex items-center gap-2 text-xs text-espresso-muted">
                <Loader2 className="h-4 w-4 animate-spin text-[#0D0F17]" />
                <span>FinAI sedang menganalisis pesan Anda...</span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Chat Input Bar */}
          <div className="border-t border-surface-border bg-surface-card p-3">
            {isRecording ? (
              <div className="flex items-center justify-between rounded-2xl bg-rose-500/10 border border-rose-500/30 px-4 py-2.5">
                <div className="flex items-center gap-2 text-xs font-bold text-rose-600">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-500 opacity-75"></span>
                    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-rose-500"></span>
                  </span>
                  <span>Merekam pesan suara... {recordSeconds} detik</span>
                </div>
                <button
                  type="button"
                  onClick={stopVoiceRecording}
                  className="flex items-center gap-1.5 rounded-xl bg-rose-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-rose-700 transition active:scale-95"
                >
                  <Square className="h-3.5 w-3.5 fill-current" />
                  Kirim Suara
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={startVoiceRecording}
                  disabled={isChatLoading}
                  className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-2xl border border-surface-border bg-white text-espresso hover:bg-surface-card transition active:scale-95 shadow-xs"
                  title="Rekam Voice Note"
                >
                  <Mic className="h-4 w-4" />
                </button>

                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
                  placeholder="Ketik transaksi (mis: Beli kopi 25rb) atau tanya kondisi kas..."
                  disabled={isChatLoading}
                  className="flex-1 rounded-2xl border border-surface-border bg-white px-4 py-3 text-xs text-espresso placeholder:text-espresso-muted/40 focus:border-[#0D0F17] focus:outline-none"
                />

                <button
                  type="button"
                  onClick={handleSendMessage}
                  disabled={!inputText.trim() || isChatLoading}
                  className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-2xl bg-[#0D0F17] text-[#C8F526] hover:bg-[#161A26] disabled:opacity-40 transition shadow-xs active:scale-95"
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* TAB 2: SMART AI DYNAMIC BUDGETING */}
      {/* ===================================================================== */}
      {activeTab === "budget" && (
        <div className="space-y-6">
          <div className="rounded-3xl border border-surface-border bg-white p-6 shadow-xs space-y-4">
            <h3 className="text-sm font-black text-espresso flex items-center gap-2">
              <Sliders className="h-4 w-4 text-espresso" />
              Parameter Keinginan & Batasan Finansial Anda
            </h3>

            <textarea
              rows={3}
              value={budgetPrompt}
              onChange={(e) => setBudgetPrompt(e.target.value)}
              placeholder="Contoh: Pemasukan 5 juta, ingin menabung 1 juta untuk dana darurat, kurangi pos belanja dan hiburan."
              className="w-full rounded-2xl border border-surface-border bg-surface-card p-3 text-xs text-espresso placeholder:text-espresso-muted/40 focus:border-[#0D0F17] focus:outline-none"
            />

            <button
              type="button"
              onClick={handleGenerateBudget}
              disabled={isBudgetLoading || !budgetPrompt.trim()}
              className="flex items-center gap-2 rounded-2xl bg-[#0D0F17] px-5 py-3 text-xs font-black text-[#C8F526] shadow-md transition hover:bg-[#161A26] disabled:opacity-50 active:scale-98"
            >
              {isBudgetLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              {isBudgetLoading ? "AI Sedang Menganalisis..." : "Rancang Anggaran Otomatis"}
            </button>
          </div>

          {/* Hasil Draf Anggaran */}
          {budgetPlan && (
            <div className="rounded-3xl border border-surface-border bg-white p-6 shadow-xs space-y-6">
              <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center border-b border-surface-border pb-4">
                <div>
                  <h3 className="text-base font-black text-espresso">Rekomendasi Anggaran Bulanan</h3>
                  <p className="text-xs text-espresso-muted mt-0.5">
                    Strategi: <span className="text-espresso font-semibold">{budgetPlan.strategy_summary}</span>
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <div className="rounded-2xl border border-surface-border bg-surface-card px-3.5 py-2 text-right">
                    <span className="block text-[10px] text-espresso-muted font-bold uppercase">Total Plafon</span>
                    <span className="text-sm font-black text-espresso">
                      Rp{parseFloat(budgetPlan.total_budget).toLocaleString("id-ID")}
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={handleSaveBudgetToDb}
                    disabled={isBudgetLoading}
                    className="flex items-center gap-1.5 rounded-2xl bg-[#C8F526] px-4 py-2.5 text-xs font-black text-black hover:bg-[#b8e51b] transition shadow-md disabled:opacity-50 active:scale-95"
                  >
                    <Save className="h-3.5 w-3.5" />
                    Terapkan ke Database
                  </button>
                </div>
              </div>

              {saveSuccessMsg && (
                <div className="rounded-2xl border border-income/30 bg-income/10 p-3 text-xs text-income font-medium">
                  {saveSuccessMsg}
                </div>
              )}

              {/* Grid Kartu Kategori Anggaran */}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {budgetPlan.allocations.map((item: any, idx: number) => (
                  <div
                    key={idx}
                    className="rounded-2xl border border-surface-border bg-surface-card p-4 space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-bold text-espresso">{item.category_name}</span>
                      <span className="rounded-full bg-[#0D0F17] px-2.5 py-0.5 text-xs font-black text-[#C8F526]">
                        Rp{parseFloat(item.suggested_limit).toLocaleString("id-ID")}
                      </span>
                    </div>

                    <p className="text-xs text-espresso-muted leading-relaxed">
                      💡 {item.reasoning}
                    </p>

                    <div className="text-[11px] text-espresso-muted/80">
                      Rata-rata pengeluaran historis: Rp
                      {parseFloat(item.historical_average || "0").toLocaleString("id-ID")}/bln
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

