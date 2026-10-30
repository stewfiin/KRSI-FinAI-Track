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
        <div>
          <h1 className="text-xl font-bold tracking-tight text-espresso flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-terracotta" />
            AI Finance Assistant
          </h1>
        </div>

        {/* Tab Toggle */}
        <div className="flex rounded-xl bg-surface-card p-1 border border-surface-border">
          <button
            type="button"
            onClick={() => setActiveTab("chat")}
            className={`rounded-lg px-4 py-1.5 text-xs font-bold transition ${
              activeTab === "chat"
                ? "bg-terracotta text-white shadow-md shadow-terracotta/20"
                : "text-espresso-muted hover:text-espresso"
            }`}
          >
            Obrolan AI
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("budget")}
            className={`rounded-lg px-4 py-1.5 text-xs font-bold transition ${
              activeTab === "budget"
                ? "bg-terracotta text-white shadow-md shadow-terracotta/20"
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
        <div className="flex h-[75vh] flex-col rounded-3xl border border-surface-border bg-surface shadow-md">
          {/* Chat Messages Scrollable Box */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.sender === "assistant" && (
                  <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl bg-terracotta text-white shadow-sm">
                    <Bot className="h-4 w-4" />
                  </div>
                )}

                <div className={`max-w-[85%] sm:max-w-md space-y-2`}>
                  <div
                    className={`rounded-2xl px-4 py-2.5 text-xs leading-relaxed ${
                      msg.sender === "user"
                        ? "bg-terracotta text-white shadow-md shadow-terracotta/20 rounded-tr-none font-medium"
                        : "border border-surface-border bg-surface-card text-espresso rounded-tl-none font-medium"
                    }`}
                  >
                    <p className="whitespace-pre-line">{msg.text}</p>
                    <span className="mt-1 block text-right text-[10px] opacity-60">
                      {msg.time}
                    </span>
                  </div>

                  {/* Transaction Preview Card (Jika ada transaksi tercatat) */}
                  {msg.transaction && (
                    <div className="rounded-2xl border border-income/30 bg-income/10 p-3 text-xs shadow-sm">
                      <div className="flex items-center gap-1.5 text-income font-bold mb-1.5">
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
                    <div className="flex items-center gap-2 rounded-xl border border-amber/40 bg-amber/15 p-2.5 text-xs text-espresso">
                      <AlertTriangle className="h-4 w-4 flex-shrink-0 text-terracotta" />
                      <span>{msg.budgetAlert.message}</span>
                    </div>
                  )}
                </div>

                {msg.sender === "user" && (
                  <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl bg-amber/20 text-terracotta">
                    <UserIcon className="h-4 w-4" />
                  </div>
                )}
              </div>
            ))}
            {isChatLoading && (
              <div className="flex items-center gap-2 text-xs text-espresso-muted">
                <Loader2 className="h-4 w-4 animate-spin text-terracotta" />
                <span>FinAI sedang berpikir...</span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Chat Input Bar */}
          <div className="border-t border-surface-border bg-surface-card p-3">
            {isRecording ? (
              <div className="flex items-center justify-between rounded-2xl bg-terracotta/10 border border-terracotta/30 px-4 py-2.5">
                <div className="flex items-center gap-2 text-xs font-semibold text-terracotta">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-terracotta opacity-75"></span>
                    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-terracotta"></span>
                  </span>
                  <span>Merekam pesan suara... {recordSeconds} detik</span>
                </div>
                <button
                  onClick={stopVoiceRecording}
                  className="flex items-center gap-1.5 rounded-xl bg-terracotta px-3 py-1.5 text-xs font-semibold text-white hover:bg-terracotta-hover"
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
                  className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-2xl border border-surface-border bg-surface text-espresso-muted hover:text-terracotta transition hover:bg-surface-card"
                  title="Rekam Voice Note"
                >
                  <Mic className="h-4 w-4" />
                </button>

                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
                  placeholder="Ketik pengeluaran / pertanyaan keuangan..."
                  disabled={isChatLoading}
                  className="flex-1 rounded-2xl border border-surface-border bg-surface px-4 py-2.5 text-xs text-espresso placeholder:text-espresso-muted/40 focus:border-terracotta focus:outline-none"
                />

                <button
                  type="button"
                  onClick={handleSendMessage}
                  disabled={!inputText.trim() || isChatLoading}
                  className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-2xl bg-terracotta text-white hover:bg-terracotta-hover disabled:opacity-40 transition shadow-sm"
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
          <div className="rounded-3xl border border-surface-border bg-surface p-6 shadow-sm space-y-4">
            <div>
              <h3 className="text-sm font-bold text-espresso flex items-center gap-2">
                <Sliders className="h-4 w-4 text-terracotta" />
                Parameter Keinginan & Batasan Finansial Anda
              </h3>
              <p className="text-xs text-espresso-muted mt-1">
                Tuliskan kondisi pemasukan dan target tabungan Anda dalam bahasa santai. AI akan membaca
                histori rata-rata pengeluaran Anda dan menghitung rekomendasi plafon per kategori.
              </p>
            </div>

            <textarea
              rows={3}
              value={budgetPrompt}
              onChange={(e) => setBudgetPrompt(e.target.value)}
              placeholder="Contoh: Pemasukan 5 juta, ingin menabung 1 juta untuk dana darurat, kurangi pos belanja dan hiburan."
              className="w-full rounded-2xl border border-surface-border bg-surface-card p-3 text-xs text-espresso placeholder:text-espresso-muted/40 focus:border-terracotta focus:outline-none"
            />

            <button
              type="button"
              onClick={handleGenerateBudget}
              disabled={isBudgetLoading || !budgetPrompt.trim()}
              className="flex items-center gap-2 rounded-xl bg-terracotta px-5 py-2.5 text-xs font-semibold text-white shadow-md shadow-terracotta/20 transition hover:bg-terracotta-hover disabled:opacity-50"
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
            <div className="rounded-3xl border border-surface-border bg-surface p-6 shadow-sm space-y-6">
              <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center border-b border-surface-border pb-4">
                <div>
                  <h3 className="text-base font-bold text-espresso">Rekomendasi Anggaran Bulanan</h3>
                  <p className="text-xs text-espresso-muted mt-0.5">
                    Strategi: <span className="text-espresso font-semibold">{budgetPlan.strategy_summary}</span>
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <div className="rounded-xl border border-amber/30 bg-amber/15 px-3 py-1.5 text-right">
                    <span className="block text-[10px] text-terracotta font-bold uppercase">Total Plafon</span>
                    <span className="text-sm font-bold text-espresso">
                      Rp{parseFloat(budgetPlan.total_budget).toLocaleString("id-ID")}
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={handleSaveBudgetToDb}
                    disabled={isBudgetLoading}
                    className="flex items-center gap-1.5 rounded-xl bg-income px-4 py-2 text-xs font-semibold text-white hover:bg-income-hover transition shadow-sm disabled:opacity-50"
                  >
                    <Save className="h-3.5 w-3.5" />
                    Terapkan ke Database
                  </button>
                </div>
              </div>

              {saveSuccessMsg && (
                <div className="rounded-xl border border-income/30 bg-income/10 p-3 text-xs text-income font-medium">
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
                      <span className="rounded-md bg-amber/20 px-2 py-0.5 text-xs font-bold text-terracotta">
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

