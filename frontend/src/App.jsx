import { useEffect, useRef, useState } from "react";
import Sidebar from "./Sidebar.jsx";
import MarkdownLite from "./markdownLite.jsx";
import { getDataQuality, getHealth, refreshData, resetSession, sendChatMessage } from "./api.js";
import "./App.css";

const SESSION_STORAGE_KEY = "skylark-bi-session-id";

const EXAMPLE_QUESTIONS = [
  "How's our pipeline looking for the energy sector this quarter?",
  "Which work orders are overdue right now?",
  "Prepare a leadership update for Mining.",
  "What data quality issues should I know about?",
];

export default function App() {
  const [health, setHealth] = useState(null);
  const [quality, setQuality] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(() => sessionStorage.getItem(SESSION_STORAGE_KEY));
  const bottomRef = useRef(null);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth({ monday_mode: "mock", llm_ready: false, llm_error: "unreachable" }));
    getDataQuality().then(setQuality).catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await refreshData();
      const q = await getDataQuality();
      setQuality(q);
    } finally {
      setRefreshing(false);
    }
  }

  async function handleSend(question) {
    const text = (question ?? input).trim();
    if (!text || sending) return;

    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setSending(true);

    try {
      const res = await sendChatMessage(text, sessionId);
      setSessionId(res.session_id);
      sessionStorage.setItem(SESSION_STORAGE_KEY, res.session_id);
      setMessages((prev) => [...prev, { role: "assistant", content: res.answer }]);
    } catch (err) {
      setError(err.message ?? "Something went wrong talking to the agent.");
    } finally {
      setSending(false);
    }
  }

  function handleNewConversation() {
    resetSession(sessionId).catch(() => {});
    sessionStorage.removeItem(SESSION_STORAGE_KEY);
    setSessionId(null);
    setMessages([]);
    setError(null);
  }

  const llmBlocked = health && !health.llm_ready;

  return (
    <div className="app-shell">
      <Sidebar health={health} quality={quality} onRefresh={handleRefresh} refreshing={refreshing} />

      <main className="chat-pane">
        <header className="chat-header">
          <div>
            <h1>Skylark Drones — Business Intelligence Agent</h1>
            <p>Ask about pipeline health, delivery status, revenue, or sector performance.</p>
          </div>
          <button className="new-chat-button" onClick={handleNewConversation}>
            New conversation
          </button>
        </header>

        {llmBlocked && (
          <div className="banner banner-error">
            LLM not configured ({health.llm_error}). Set <code>ANTHROPIC_API_KEY</code> on the backend to enable
            the chat agent.
          </div>
        )}

        <div className="messages">
          {messages.length === 0 && !llmBlocked && (
            <div className="empty-state">
              <p>Try asking:</p>
              <div className="example-chips">
                {EXAMPLE_QUESTIONS.map((q) => (
                  <button key={q} onClick={() => handleSend(q)}>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`message message-${m.role}`}>
              <div className="message-bubble">
                <MarkdownLite text={m.content} />
              </div>
            </div>
          ))}

          {sending && (
            <div className="message message-assistant">
              <div className="message-bubble message-pending">Checking the boards…</div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {error && <div className="banner banner-error">{error}</div>}

        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="e.g. How's our pipeline looking for the energy sector this quarter?"
            disabled={llmBlocked}
          />
          <button type="submit" disabled={llmBlocked || sending || !input.trim()}>
            Send
          </button>
        </form>
      </main>
    </div>
  );
}
