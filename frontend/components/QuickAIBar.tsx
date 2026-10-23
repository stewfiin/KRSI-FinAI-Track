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
      <div className="relative flex items-center rounded-2xl border border-surface-border bg-surface p-1.5 shadow-sm transition-all focus-within:border-terracotta focus-within:ring-2 focus-within:ring-terracotta/25">
        <div className="pl-3 pr-2 text-terracotta">
          <Sparkles className="h-5 w-5 animate-pulse" />
        </div>

        {isRecording ? (
          <div className="flex flex-1 items-center gap-3 px-2 py-1">
            <span className="relative flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-terracotta opacity-75"></span>
              <span className="relative inline-flex h-3 w-3 rounded-full bg-terracotta"></span>
            </span>
            <span className="text-sm font-medium text-terracotta">
              Merekam suara... {formatTimer(recordSeconds)}
            </span>
            <div className="flex-1" />
            <button
              onClick={stopRecording}
              className="flex items-center gap-1.5 rounded-xl bg-terracotta/15 px-3 py-1.5 text-xs font-semibold text-terracotta hover:bg-terracotta/25"
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
              className="flex-1 bg-transparent px-2 py-2 text-sm text-espresso placeholder:text-espresso-muted/60 focus:outline-none disabled:opacity-50"
            />

            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={startRecording}
                disabled={isLoading}
                title="Tekan untuk rekam suara"
                className="flex h-9 w-9 items-center justify-center rounded-xl bg-cream-dark/60 text-espresso transition hover:bg-cream-dark hover:text-espresso"
              >
                <Mic className="h-4 w-4" />
              </button>

              <button
                type="button"
                onClick={handleSendText}
                disabled={!text.trim() || isLoading}
                className="flex h-9 w-9 items-center justify-center rounded-xl bg-terracotta text-white shadow-sm shadow-terracotta/20 transition hover:bg-terracotta-hover disabled:opacity-40"
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
          className={`flex flex-col gap-1 rounded-xl border p-3 text-xs leading-relaxed transition shadow-sm ${
            feedback.type === "success"
              ? "border-income/30 bg-income/10 text-income font-medium"
              : "border-expense/30 bg-expense/10 text-expense font-medium"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="font-bold flex items-center gap-1.5">
              {feedback.type === "success" ? (
                <CheckCircle2 className="h-3.5 w-3.5" />
              ) : (
                <AlertTriangle className="h-3.5 w-3.5" />
              )}
              {feedback.type === "success" ? "FinAI Response" : "Perhatian"}
            </span>
            <button
              onClick={() => setFeedback(null)}
              className="text-espresso-muted hover:text-espresso"
            >
              ✕
            </button>
          </div>
          <p className="whitespace-pre-line text-espresso">{feedback.message}</p>
          {feedback.alert && (
            <div className="mt-1 flex items-center gap-1.5 rounded-lg border border-amber/40 bg-amber/15 p-2 text-espresso">
              <AlertTriangle className="h-4 w-4 flex-shrink-0 text-terracotta" />
              <span>{feedback.alert}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

