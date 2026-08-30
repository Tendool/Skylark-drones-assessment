import { useEffect, useRef, useState } from "react";
import Sidebar from "./Sidebar.jsx";
import Message from "./Message.jsx";
import { BotIcon, MoonIcon, SendIcon, SparkleIcon, SunIcon } from "./icons.jsx";
import { getDataQuality, getHealth, refreshData, resetSession, sendChatMessage } from "./api.js";
import "./App.css";

const SESSION_STORAGE_KEY = "skylark-bi-session-id";
const THEME_STORAGE_KEY = "skylark-bi-theme";

const EXAMPLE_QUESTIONS = [
  "How's our pipeline looking for the energy sector this quarter?",
  "Which work orders are overdue right now?",
  "Prepare a leadership update for Mining.",
  "What data quality issues should I know about?",
];

function useTheme() {
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem(THEME_STORAGE_KEY);
    if (saved) return saved;
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  return [theme, () => setTheme((t) => (t === "dark" ? "light" : "dark"))];
}

function autosize(el) {
  if (!el) return;
  el.style.height = "auto";
  el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
}

export default function App() {
  const [theme, toggleTheme] = useTheme();
  const [health, setHealth] = useState(null);
  const [quality, setQuality] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(() => sessionStorage.getItem(SESSION_STORAGE_KEY));
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

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
    requestAnimationFrame(() => autosize(textareaRef.current));
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

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const llmBlocked = health && !health.llm_ready;

  return (
    <div className="app-shell">
      <Sidebar health={health} quality={quality} onRefresh={handleRefresh} refreshing={refreshing} />

      <main className="chat-pane">
        <header className="chat-header">
          <div>
            <h1>Business Intelligence Agent</h1>
            <p>Ask about pipeline health, delivery status, revenue, or sector performance.</p>
          </div>
          <div className="header-actions">
            <button className="icon-button" onClick={toggleTheme} title="Toggle theme" aria-label="Toggle color theme">
              {theme === "dark" ? <SunIcon /> : <MoonIcon />}
            </button>
            <button className="new-chat-button" onClick={handleNewConversation}>
              New conversation
            </button>
          </div>
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
              <div className="empty-icon">
                <SparkleIcon />
              </div>
              <h2>What would you like to know?</h2>
              <p>Try one of these, or ask your own question about the boards.</p>
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
            <Message key={i} role={m.role} content={m.content} />
          ))}

          {sending && (
            <div className="message-row message-assistant">
              <div className="avatar avatar-assistant">
                <BotIcon />
              </div>
              <div className="message-bubble-wrap">
                <div className="message-bubble">
                  <span className="typing-dots">
                    <span />
                    <span />
                    <span />
                  </span>
                </div>
              </div>
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
          <div className="composer-input-wrap">
            <textarea
              ref={textareaRef}
              rows={1}
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                autosize(e.target);
              }}
              onKeyDown={handleKeyDown}
              placeholder="e.g. How's our pipeline looking for the energy sector this quarter?"
              disabled={llmBlocked}
            />
          </div>
          <button type="submit" className="send-button" disabled={llmBlocked || sending || !input.trim()} aria-label="Send message">
            <SendIcon />
          </button>
        </form>
        <div className="composer-hint">Enter to send · Shift + Enter for a new line</div>
      </main>
    </div>
  );
}
