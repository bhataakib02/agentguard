"use client";

import React, { useState } from "react";
import { fetchApi } from "@/lib/api";
import { Brain, Send, Bot, Sparkles } from "lucide-react";

export default function AssistantPage() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    const userMsg = { sender: "USER", text: question };
    setMessages((prev) => [...prev, userMsg]);
    const currentQ = question;
    setQuestion("");
    setLoading(true);

    try {
      const res = await fetchApi("/assistant/query", {
        method: "POST",
        body: JSON.stringify({ question: currentQ }),
      });

      const botMsg = {
        sender: "ASSISTANT",
        answer: res.answer,
        data: res.data,
        recommendations: res.recommendations,
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { sender: "ASSISTANT", answer: `Assistant Error: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-[#E8E8E4] pb-5">
        <h1 className="text-[24px] font-bold text-[#1F1F1F]">AI Governance Copilot</h1>
        <p className="text-[13px] text-[#666666]">
          Natural Language Database Intelligence & Security Assistant
        </p>
      </div>

      {/* Chat Messages Window */}
      <div className="bg-[#FFFFFF] border border-[#E8E8E4] rounded-[12px] p-6 h-[500px] flex flex-col shadow-sm">
        <div className="flex-1 overflow-y-auto space-y-4 pr-2">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center space-y-3">
              <Brain className="w-12 h-12 text-[#2E9D50] opacity-50" />
              <h3 className="text-[16px] font-bold text-[#1F1F1F]">Ask AgentGuard Assistant</h3>
              <p className="text-[12px] text-[#666666] max-w-sm">
                Try asking: &quot;Which agents exhibit high risk scores?&quot; or &quot;Why were recent decisions blocked?&quot;
              </p>
            </div>
          ) : (
            messages.map((m, idx) => (
              <div
                key={idx}
                className={`flex gap-3 ${m.sender === "USER" ? "justify-end" : "justify-start"}`}
              >
                {m.sender === "ASSISTANT" && (
                  <div className="w-8 h-8 rounded-full bg-[#EAF7EE] flex items-center justify-center text-[#2E9D50] border border-[#2E9D50]/30 shrink-0">
                    <Bot className="w-4 h-4" />
                  </div>
                )}
                <div
                  className={`p-4 rounded-[12px] max-w-xl text-[13px] space-y-2 ${
                    m.sender === "USER"
                      ? "bg-[#2E9D50] text-white font-bold"
                      : "bg-[#FCFCFA] border border-[#E8E8E4] text-[#1F1F1F]"
                  }`}
                >
                  <p>{m.text || m.answer}</p>

                  {m.recommendations && m.recommendations.length > 0 && (
                    <div className="pt-2 border-t border-[#E8E8E4] text-[11px] space-y-1">
                      <span className="font-bold text-[#2E9D50] block flex items-center gap-1">
                        <Sparkles className="w-3 h-3" />
                        <span>Recommended Actions:</span>
                      </span>
                      <ul className="list-disc pl-4 text-[#666666]">
                        {m.recommendations.map((r: string, rIdx: number) => (
                          <li key={rIdx}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Input Form */}
        <form onSubmit={handleSend} className="mt-4 pt-4 border-t border-[#E8E8E4] flex gap-3">
          <input
            type="text"
            required
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question about your AI employees, policies, or decisions..."
            className="flex-1 px-4 py-2.5 text-[13px] bg-[#FCFCFA] border border-[#E8E8E4] rounded-[8px] focus:outline-none focus:border-[#2E9D50]"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2.5 bg-[#2E9D50] hover:bg-[#237A3C] text-white rounded-[8px] text-[13px] font-bold flex items-center gap-2 transition-colors disabled:opacity-50"
          >
            <span>{loading ? "Thinking..." : "Send"}</span>
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
