import React, { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import ReactMarkdown from "react-markdown";
import { Bot, Plus, Trash2, Send, Loader2, ChevronDown, Wrench, ShieldAlert, Check, MessageSquare, Sparkles } from "lucide-react";

const SUGGESTIONS = {
  orchestrator: ["Give me a full operational health check across every department", "What needs my attention today? Coordinate all agents"],
  hr: ["Who has attendance below 80% and what should we do?", "Review the pending leave requests and recommend decisions"],
  finance: ["Run the anomaly scan and explain the riskiest invoices", "Which overdue invoices should we pay first?"],
  inventory: ["Which SKUs need reordering and how many units?", "Build a purchase plan for everything below threshold"],
  sales: ["Rank our pipeline by expected value and give next actions", "Which leads are stalled in negotiation?"],
  compliance: ["Which contracts expire in the next 90 days?", "What does the termination clause say in our supply contract?"],
};

function AgentPicker({ agents, value, onChange }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const current = agents.find((a) => a.key === value);
  useEffect(() => {
    const close = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);
  return (
    <div className="relative" ref={ref}>
      <button type="button" data-testid="agent-picker" onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-[#2a2a2e] bg-[#141416] hover:bg-[#1c1c1f] text-xs font-semibold text-[#f7f7f8] transition-colors">
        <Bot className="w-3.5 h-3.5 text-[#e2726f]" />
        {current?.name || "Select agent"}
        <ChevronDown className={`w-3.5 h-3.5 text-[#6f6f76] transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div data-testid="agent-picker-menu" className="absolute bottom-full mb-2 left-0 w-80 rounded-[14px] border border-[#2a2a2e] bg-[#0f0f11] shadow-2xl p-1.5 z-30">
          <div className="px-3 py-2 text-[10px] uppercase tracking-[0.25em] text-[#6f6f76] font-mono-i">Choose an agent</div>
          {agents.map((a) => (
            <button key={a.key} type="button" data-testid={`agent-option-${a.key}`} onClick={() => { onChange(a.key); setOpen(false); }}
              className={`w-full text-left px-3 py-2.5 rounded-[10px] flex items-start gap-3 transition-colors ${a.key === value ? "bg-[#29292d]" : "hover:bg-[#1c1c1f]"}`}>
              <div className="w-8 h-8 rounded-[8px] bg-gradient-to-br from-[#a8a8ad] to-[#e2726f] flex items-center justify-center shrink-0"><Bot className="w-4 h-4 text-black" /></div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold text-[#f7f7f8] flex items-center gap-2">{a.name}{a.key === value && <Check className="w-3.5 h-3.5 text-[#e2726f]" />}</div>
                <div className="text-[11px] text-[#8c8c93] truncate">{a.specialty}</div>
                <div className="text-[10px] text-[#6f6f76] font-mono-i mt-0.5">{(a.tools || []).length} tools</div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function ToolTrace({ calls }) {
  const [open, setOpen] = useState(false);
  if (!calls?.length) return null;
  return (
    <div className="mt-3 rounded-[10px] border border-[#2a2a2e] bg-[#0f0f11]">
      <button type="button" data-testid="tool-trace-toggle" onClick={() => setOpen((o) => !o)} className="w-full flex items-center gap-2 px-3 py-2 text-[11px] font-mono-i text-[#a8a8ad] hover:text-white">
        <Wrench className="w-3.5 h-3.5" /> {calls.length} tool call{calls.length > 1 ? "s" : ""} · {calls.map((c) => c.name).join(" → ")}
        <ChevronDown className={`w-3.5 h-3.5 ml-auto transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="border-t border-[#2a2a2e] divide-y divide-[#2a2a2e]">
          {calls.map((c, i) => (
            <div key={i} className="p-3 text-[11px] font-mono-i">
              <div className="text-[#e2726f] font-bold">{c.name}({Object.keys(c.input || {}).length ? JSON.stringify(c.input) : ""})</div>
              <pre className="mt-1 max-h-40 overflow-auto text-[#8c8c93] whitespace-pre-wrap">{JSON.stringify(c.output, null, 1)?.slice(0, 1500)}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Message({ m, agents }) {
  const agent = agents.find((a) => a.key === m.agent_key);
  if (m.role === "user") {
    return (
      <div className="flex justify-end" data-testid="chat-user-message">
        <div className="max-w-[75%] px-4 py-3 rounded-[16px] rounded-br-[4px] bg-[#29292d] text-sm text-[#f7f7f8] whitespace-pre-wrap">{m.content}</div>
      </div>
    );
  }
  return (
    <div className="flex gap-3" data-testid="chat-assistant-message">
      <div className="w-8 h-8 rounded-[8px] bg-gradient-to-br from-[#a8a8ad] to-[#e2726f] flex items-center justify-center shrink-0 mt-1"><Bot className="w-4 h-4 text-black" /></div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1 text-[10px] uppercase tracking-widest font-mono-i text-[#6f6f76]">
          <span className="text-[#a8a8ad]">{agent?.name || m.agent_key}</span>
          {m.confidence != null && <span>· confidence {m.confidence}%</span>}
          {m.escalate && <span className="inline-flex items-center gap-1 text-[#e2726f]"><ShieldAlert className="w-3 h-3" /> human review</span>}
          {m.approvals?.length > 0 && <a href="/approvals" className="text-[#e2726f] underline">{m.approvals.length} approval{m.approvals.length > 1 ? "s" : ""} queued</a>}
        </div>
        <div className="prose prose-invert prose-sm max-w-none text-sm text-[#f7f7f8] [&_h1]:text-lg [&_h2]:text-base [&_h3]:text-sm [&_p]:my-1.5 [&_ul]:my-1.5 [&_li]:my-0.5 [&_table]:text-xs">
          <ReactMarkdown>{m.content}</ReactMarkdown>
        </div>
        {m.next_action && <div className="mt-2 text-xs text-[#a8a8ad]"><span className="font-mono-i uppercase tracking-widest text-[10px] text-[#6f6f76]">Next action · </span>{m.next_action}</div>}
        <ToolTrace calls={m.tool_calls} />
      </div>
    </div>
  );
}

export default function Agents() {
  const [agents, setAgents] = useState([]);
  const [convs, setConvs] = useState([]);
  const [active, setActive] = useState(null);
  const [messages, setMessages] = useState([]);
  const [agentKey, setAgentKey] = useState("orchestrator");
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef(null);

  const loadConvs = () => api.get("/chat/conversations").then((r) => setConvs(r.data));
  useEffect(() => { api.get("/agents").then((r) => setAgents(r.data)); loadConvs(); }, []);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, busy]);

  const openConv = async (c) => {
    setActive(c);
    setAgentKey(c.agent_key);
    const { data } = await api.get(`/chat/conversations/${c.id}/messages`);
    setMessages(data);
  };

  const newChat = () => { setActive(null); setMessages([]); setInput(""); };

  const send = async (text) => {
    const content = (text ?? input).trim();
    if (!content || busy) return;
    setBusy(true);
    setInput("");
    const optimistic = { id: "tmp", role: "user", content, agent_key: agentKey };
    setMessages((m) => [...m, optimistic]);
    try {
      let conv = active;
      if (!conv) {
        conv = (await api.post("/chat/conversations", { agent_key: agentKey })).data;
        setActive(conv);
      }
      const { data } = await api.post(`/chat/conversations/${conv.id}/messages`, { content, agent_key: agentKey });
      setMessages((m) => [...m.filter((x) => x.id !== "tmp"), data.user_message, data.assistant_message]);
      loadConvs();
    } catch (e) {
      setMessages((m) => m.filter((x) => x.id !== "tmp"));
      toast.error(e?.response?.data?.detail || "Agent run failed");
    } finally { setBusy(false); }
  };

  const deleteConv = async (e, id) => {
    e.stopPropagation();
    await api.delete(`/chat/conversations/${id}`);
    if (active?.id === id) newChat();
    loadConvs();
  };

  const currentAgent = agents.find((a) => a.key === agentKey);

  return (
    <div className="flex h-[calc(100vh-7rem)] rounded-[14px] border border-[#2a2a2e] bg-[#0b0b0d] overflow-hidden" data-testid="agents-page">
      <aside className="w-64 border-r border-[#2a2a2e] flex flex-col bg-[#0f0f11] shrink-0">
        <div className="p-3">
          <button type="button" data-testid="new-chat-btn" onClick={newChat} className="w-full flex items-center gap-2 px-3 py-2.5 rounded-[10px] border border-[#2a2a2e] bg-[#141416] hover:bg-[#1c1c1f] text-sm font-semibold transition-colors">
            <Plus className="w-4 h-4" /> New chat
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-2 pb-3 space-y-0.5" data-testid="conversation-list">
          {convs.length === 0 && <div className="px-3 py-6 text-xs text-[#6f6f76] text-center">No conversations yet.</div>}
          {convs.map((c) => (
            <div key={c.id} role="button" tabIndex={0} data-testid={`conversation-${c.id}`} onClick={() => openConv(c)} onKeyDown={(e) => e.key === "Enter" && openConv(c)}
              className={`group flex items-center gap-2 px-3 py-2 rounded-[10px] cursor-pointer text-sm transition-colors ${active?.id === c.id ? "bg-[#29292d]" : "hover:bg-[#1c1c1f]"}`}>
              <MessageSquare className="w-3.5 h-3.5 text-[#6f6f76] shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="truncate text-[#f7f7f8]">{c.title}</div>
                <div className="text-[10px] text-[#6f6f76] font-mono-i uppercase tracking-wider">{agents.find((a) => a.key === c.agent_key)?.name || c.agent_key}</div>
              </div>
              <button type="button" onClick={(e) => deleteConv(e, c.id)} data-testid={`delete-conversation-${c.id}`} className="opacity-0 group-hover:opacity-100 p-1 text-[#6f6f76] hover:text-[#e2726f]"><Trash2 className="w-3.5 h-3.5" /></button>
            </div>
          ))}
        </div>
      </aside>

      <section className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {messages.length === 0 && !busy ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-xl mx-auto" data-testid="chat-empty-state">
              <div className="w-14 h-14 rounded-[14px] bg-gradient-to-br from-[#a8a8ad] to-[#e2726f] flex items-center justify-center mb-5"><Sparkles className="w-7 h-7 text-black" /></div>
              <h2 className="font-display text-3xl font-black tracking-tight">{currentAgent?.name || "Agents"}</h2>
              <p className="text-sm text-[#8c8c93] mt-2">{currentAgent?.specialty}. Uses {(currentAgent?.tools || []).length} tools, remembers across runs, and routes risky actions to your approval queue.</p>
              <div className="grid sm:grid-cols-2 gap-2 mt-8 w-full">
                {(SUGGESTIONS[agentKey] || []).map((s) => (
                  <button key={s} type="button" data-testid="suggestion-chip" onClick={() => send(s)} className="text-left px-4 py-3 rounded-[12px] border border-[#2a2a2e] bg-[#141416] hover:bg-[#1c1c1f] text-sm text-[#f7f7f8] transition-colors">{s}</button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-6">
              {messages.map((m) => <Message key={m.id} m={m} agents={agents} />)}
              {busy && (
                <div className="flex gap-3" data-testid="chat-thinking">
                  <div className="w-8 h-8 rounded-[8px] bg-gradient-to-br from-[#a8a8ad] to-[#e2726f] flex items-center justify-center shrink-0"><Bot className="w-4 h-4 text-black" /></div>
                  <div className="text-sm text-[#8c8c93] flex items-center gap-2 pt-1.5"><Loader2 className="w-4 h-4 animate-spin" /> {currentAgent?.name} is reasoning and calling tools…</div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <div className="border-t border-[#2a2a2e] p-4">
          <div className="max-w-3xl mx-auto rounded-[16px] border border-[#2a2a2e] bg-[#141416] focus-within:border-[#4a4a50] transition-colors">
            <textarea data-testid="chat-input" value={input} onChange={(e) => setInput(e.target.value)} rows={2}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder={`Message ${currentAgent?.name || "an agent"}… (Enter to send, Shift+Enter for newline)`}
              className="w-full bg-transparent px-4 pt-3 pb-2 outline-none text-sm resize-none placeholder:text-[#6f6f76]" />
            <div className="flex items-center justify-between px-3 pb-3">
              <AgentPicker agents={agents} value={agentKey} onChange={setAgentKey} />
              <button type="button" data-testid="chat-send-btn" onClick={() => send()} disabled={busy || !input.trim()}
                className="w-9 h-9 rounded-full bg-gradient-to-r from-[#a8a8ad] to-[#e2726f] text-black flex items-center justify-center disabled:opacity-40 transition-opacity">
                {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </button>
            </div>
          </div>
          <div className="max-w-3xl mx-auto mt-2 text-[10px] text-[#6f6f76] font-mono-i uppercase tracking-widest text-center">Agents can only propose payments, purchases and terminations — humans approve them.</div>
        </div>
      </section>
    </div>
  );
}
