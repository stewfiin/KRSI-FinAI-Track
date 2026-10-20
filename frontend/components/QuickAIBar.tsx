"use client";

import { useState, useRef, useEffect } from "react";
import { Mic, Send, Square, Loader2, Sparkles, AlertTriangle, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";

interface QuickAIBarProps {
  onSuccess?: () => void;
}

export function QuickAIBar({ onSuccess }: QuickAIBarProps) {
  const [text, setText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
    alert?: string;
  } | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Timer rekaman suara
  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => {
        setRecordSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      setRecordSeconds(0);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isRecording]);

  // Kirim input teks ke AI Chat
  const handleSendText = async () => {
    if (!text.trim() || isLoading) return;
    setIsLoading(true);
    setFeedback(null);

    try {
      const res = await api.post("/api/ai/chat", {
        message: text.trim(),
        platform: "web",
      });
      setText("");
      setFeedback({
        type: "success",
        message: res.data.reply,
        alert: res.data.budget_alert?.message,
      });
      if (onSuccess) onSuccess();
    } catch (err: any) {
      setFeedback({
        type: "error",
        message: err.response?.data?.detail || "Gagal memproses pesan AI.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Mulai merekam audio (MediaRecorder API)
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        stream.getTracks().forEach((track) => track.stop());
        await sendAudioBlob(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
      setFeedback(null);
    } catch (err) {
      alert("Akses mikrofon ditolak atau perangkat tidak mendukung perekaman audio.");
    }
  };

  // Hentikan rekaman
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  // Kirim audio blob ke /api/ai/voice
  const sendAudioBlob = async (blob: Blob) => {
    setIsLoading(true);
    const formData = new FormData();
    formData.append("file", blob, "quick_voice.webm");
    formData.append("platform", "web");

    try {
      const res = await api.post("/api/ai/voice", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const chatRes = res.data.chat_result;
      setFeedback({
        type: "success",
        message: `🎙️ "${res.data.transcript}"\n\n${chatRes.reply}`,
        alert: chatRes.budget_alert?.message,
      });
      if (onSuccess) onSuccess();
    } catch (err: any) {
      setFeedback({
        type: "error",
        message: err.response?.data?.detail || "Gagal memproses rekaman suara.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const formatTimer = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="w-full space-y-2">
      {/* Container Input Quick AI */}
      <div className="relative flex items-center rounded-2xl border border-surface-border bg-surface-card p-1.5 shadow-lg transition-all focus-within:border-blue-500/50 focus-within:ring-2 focus-within:ring-blue-500/20">
        <div className="pl-3 pr-2 text-blue-400">
          <Sparkles className="h-5 w-5 animate-pulse" />
        </div>

        {isRecording ? (
          <div className="flex flex-1 items-center gap-3 px-2 py-1">
            <span className="relative flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex h-3 w-3 rounded-full bg-red-500"></span>
            </span>
            <span className="text-sm font-medium text-red-400">
              Merekam suara... {formatTimer(recordSeconds)}
            </span>
            <div className="flex-1" />
            <button
              onClick={stopRecording}
              className="flex items-center gap-1.5 rounded-xl bg-red-500/20 px-3 py-1.5 text-xs font-semibold text-red-400 hover:bg-red-500/30"
            >
              <Square className="h-3.5 w-3.5 fill-current" />
              Selesai
            </button>
          </div>
        ) : (
          <>
            <input
              type="text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSendText()}
              placeholder="Ketik transaksi masuk/keluar (misal: 'beli kopi 5rb, dapet uang saku 10rb')..."
              disabled={isLoading}
              className="flex-1 bg-transparent px-2 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none disabled:opacity-50"
            />

            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={startRecording}
                disabled={isLoading}
                title="Tekan untuk rekam suara"
                className="flex h-9 w-9 items-center justify-center rounded-xl bg-surface-border text-slate-300 transition hover:bg-surface-border/80 hover:text-white"
              >
                <Mic className="h-4 w-4" />
              </button>

              <button
                type="button"
                onClick={handleSendText}
                disabled={!text.trim() || isLoading}
                className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-white transition hover:bg-blue-500 disabled:opacity-40"
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </button>
            </div>
          </>
        )}
      </div>

      {/* Feedback Toast / Alert Card */}
      {feedback && (
        <div
          className={`flex flex-col gap-1 rounded-xl border p-3 text-xs leading-relaxed transition ${
            feedback.type === "success"
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
              : "border-red-500/30 bg-red-500/10 text-red-300"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="font-semibold flex items-center gap-1.5">
              {feedback.type === "success" ? (
                <CheckCircle2 className="h-3.5 w-3.5" />
              ) : (
                <AlertTriangle className="h-3.5 w-3.5" />
              )}
              {feedback.type === "success" ? "FinAI Response" : "Perhatian"}
            </span>
            <button
              onClick={() => setFeedback(null)}
              className="text-slate-400 hover:text-white"
            >
              ✕
            </button>
          </div>
          <p className="whitespace-pre-line">{feedback.message}</p>
          {feedback.alert && (
            <div className="mt-1 flex items-center gap-1.5 rounded-lg border border-amber-500/30 bg-amber-500/20 p-2 text-amber-200">
              <AlertTriangle className="h-4 w-4 flex-shrink-0 text-amber-400" />
              <span>{feedback.alert}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

