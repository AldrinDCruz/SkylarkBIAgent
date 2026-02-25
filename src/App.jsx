// App.jsx – root component with sidebar layout
import { useState, useRef } from "react";
import ChatWindow from "./components/ChatWindow";
import QuickChips from "./components/QuickChips";
import LeadershipReport from "./components/LeadershipReport";
import DashboardView from "./components/DashboardView";
import { sendMessage, refreshCache } from "./api";

const WELCOME_MESSAGE = {
  role: "assistant",
  content: `**Welcome to Skylark Drones BI Agent** 🦅

I have real-time access to your Monday.com ecosystems, including the **Deals Pipeline** and **Work Orders Tracker**. I'm ready to analyze your business performance instantly.

*Data is fetched live and analyzed with AI. Numbers are in Indian format (Cr/L).*`,
};

export default function App() {
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const [cacheRefreshing, setCacheRefreshing] = useState(false);
  const [activeNav, setActiveNav] = useState("agent");
  const inputRef = useRef(null);

  const isConversationEmpty = messages.length === 1 && messages[0].role === "assistant";

  const submitMessage = async (text) => {
    const userMsg = text || input.trim();
    if (!userMsg || isLoading) return;
    setInput("");
    const outgoingHistory = [...messages].filter((m) => m.role !== "system");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setIsLoading(true);
    try {
      const data = await sendMessage(
        userMsg,
        outgoingHistory.map((m) => ({ role: m.role, content: m.content }))
      );
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.response,
          charts: data.charts || [],
          meta: { boards_queried: data.boards_queried, data_counts: data.data_counts },
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `⚠️ **Error:** ${err.message}\n\nMake sure the backend server is running.`,
        },
      ]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitMessage();
    }
  };

  const handleRefreshCache = async () => {
    setCacheRefreshing(true);
    try {
      await refreshCache();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "✅ Cache cleared. Next query will fetch fresh data from Monday.com." },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "⚠️ Cache refresh failed. Is the backend running?" },
      ]);
    } finally {
      setCacheRefreshing(false);
    }
  };

  return (
    <div className="app-shell">
      {/* ── Sidebar ─────────────────────────────── */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">
            <span>🦅</span>
          </div>
          <span className="sidebar-logo-text">Skylark BI</span>
        </div>

        <nav className="sidebar-nav">
          <p className="sidebar-section-label">MAIN</p>
          <button
            className={`sidebar-nav-item ${activeNav === "agent" ? "active" : ""}`}
            onClick={() => setActiveNav("agent")}
          >
            <span className="nav-icon">🤖</span> AI Agent
          </button>
          <button
            className={`sidebar-nav-item ${activeNav === "dashboards" ? "active" : ""}`}
            onClick={() => setActiveNav("dashboards")}
          >
            <span className="nav-icon">📊</span> Dashboards
          </button>


        </nav>

        <div className="sidebar-user">
          <div className="sidebar-avatar">AH</div>
          <div className="sidebar-user-info">
            <span className="sidebar-user-name">Alex Henderson</span>
            <span className="sidebar-user-role">Leadership Team</span>
          </div>
          <button className="sidebar-settings-btn" title="Settings">⚙️</button>
        </div>
      </aside>

      {/* ── Main area ────────────────────────────── */}
      <div className="workspace">
        {/* Top header */}
        <header className="workspace-header">
          <div>
            <h1 className="workspace-title">
              {activeNav === "dashboards" ? "Ad Hoc Dashboard" : "BI Workspace"}
            </h1>
            <p className="workspace-subtitle">
              {activeNav === "dashboards"
                ? "Live data from all Monday.com boards"
                : "Live data from Monday.com • Powered by Gemini AI"}
            </p>
          </div>
          <div className="workspace-header-actions">
            <button
              className="btn-sync"
              onClick={handleRefreshCache}
              disabled={cacheRefreshing}
            >
              {cacheRefreshing ? "⏳" : "🔄"} Sync
            </button>
            {activeNav !== "dashboards" && (
              <button className="btn-leadership-new" onClick={() => setShowReport(true)}>
                ✶ Generate Leadership Update
              </button>
            )}
          </div>
        </header>

        {/* Dashboard or Chat */}
        {activeNav === "dashboards" ? (
          <main className="workspace-main">
            <DashboardView />
          </main>
        ) : (
          <>
            <main className="workspace-main">
              <div className="chat-container">
                <ChatWindow messages={messages} isLoading={isLoading} />
                {isConversationEmpty && (
                  <QuickChips onSelect={(q) => submitMessage(q)} />
                )}
              </div>
            </main>

            <footer className="workspace-footer">
              <div className="input-bar-new">
                <span className="input-icon">📎</span>
                <span className="input-icon">🎤</span>
                <span className="input-icon">✶</span>
                <textarea
                  ref={inputRef}
                  className="chat-input-new"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask anything about your pipeline, revenue, or work orders…"
                  rows={1}
                  disabled={isLoading}
                />
                <span className="input-hint">Shift + Enter for new line</span>
                <button
                  className="send-btn-new"
                  onClick={() => submitMessage()}
                  disabled={isLoading || !input.trim()}
                  aria-label="Send"
                >
                  {isLoading ? (
                    <span className="loading-spinner" />
                  ) : (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <line x1="22" y1="2" x2="11" y2="13" />
                      <polygon points="22 2 15 22 11 13 2 9 22 2" />
                    </svg>
                  )}
                </button>
              </div>
              <p className="workspace-status">
                DATA CACHED 5 MIN AGO &nbsp;•&nbsp; POWERED BY GEMINI 2.5 FLASH
              </p>
            </footer>
          </>
        )}
      </div>

      {showReport && <LeadershipReport onClose={() => setShowReport(false)} />}
    </div>
  );
}
