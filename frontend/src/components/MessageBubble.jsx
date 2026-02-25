// MessageBubble.jsx – chat bubble with markdown, charts, and inline ad hoc analysis
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import ChartPanel from "./ChartPanel";
import { runAdhocAnalysis } from "../api";

const DIMENSIONS = [
    { value: "sector", label: "Sector" },
    { value: "owner", label: "Owner" },
    { value: "stage", label: "Deal Stage" },
    { value: "status", label: "Deal Status" },
    { value: "platform", label: "Platform" },
];

const METRICS = [
    { value: "deal_count", label: "Deal Count", group: "Deals" },
    { value: "deal_value", label: "Deal Value (₹)", group: "Deals" },
    { value: "win_rate", label: "Win Rate (%)", group: "Deals" },
    { value: "wo_count", label: "WO Count", group: "Ops" },
    { value: "billed", label: "Billed (₹)", group: "Revenue" },
    { value: "collected", label: "Collected (₹)", group: "Revenue" },
    { value: "ar", label: "Outstanding AR (₹)", group: "Revenue" },
];

function InlineAdhoc() {
    const [open, setOpen] = useState(false);
    const [dimension, setDimension] = useState("sector");
    const [metric, setMetric] = useState("deal_value");
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    const handleRun = async () => {
        setLoading(true);
        setError(null);
        setResult(null);
        try {
            const data = await runAdhocAnalysis(dimension, metric);
            setResult(data);
        } catch (err) {
            setError(err.message || "Analysis failed.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="inline-adhoc">
            <button
                className="adhoc-toggle-btn"
                onClick={() => { setOpen(o => !o); setResult(null); setError(null); }}
            >
                <span>📊</span>
                <span>{open ? "Hide" : "Explore Data"}</span>
                <span className="adhoc-chevron">{open ? "▲" : "▼"}</span>
            </button>

            {open && (
                <div className="inline-adhoc-panel">
                    <div className="inline-adhoc-controls">
                        <select
                            className="adhoc-select-sm"
                            value={dimension}
                            onChange={e => setDimension(e.target.value)}
                            aria-label="Group by dimension"
                        >
                            {DIMENSIONS.map(d => (
                                <option key={d.value} value={d.value}>{d.label}</option>
                            ))}
                        </select>

                        <span className="adhoc-by">×</span>

                        <select
                            className="adhoc-select-sm"
                            value={metric}
                            onChange={e => setMetric(e.target.value)}
                            aria-label="Metric"
                        >
                            {["Deals", "Ops", "Revenue"].map(g => (
                                <optgroup key={g} label={g}>
                                    {METRICS.filter(m => m.group === g).map(m => (
                                        <option key={m.value} value={m.value}>{m.label}</option>
                                    ))}
                                </optgroup>
                            ))}
                        </select>

                        <button
                            className="adhoc-run-sm"
                            onClick={handleRun}
                            disabled={loading}
                        >
                            {loading
                                ? <span className="loading-spinner" style={{ width: 14, height: 14 }} />
                                : "▶ Run"}
                        </button>
                    </div>

                    {error && (
                        <p className="adhoc-inline-error">⚠️ {error}</p>
                    )}

                    {result && (
                        <div className="adhoc-inline-result">
                            {/* Summary strip */}
                            <div className="adhoc-inline-summary">
                                <span>Total: <strong>{result.summary.total_formatted}</strong></span>
                                <span className="adhoc-dot">·</span>
                                <span>Top: <strong className="adhoc-top">{result.summary.top_name}</strong> — {result.summary.top_value_formatted}</span>
                            </div>

                            {/* Chart */}
                            <ChartPanel charts={[result.chart]} />

                            {/* AI Insight */}
                            <div className="adhoc-inline-insight">
                                <span className="insight-badge">🤖 AI</span>
                                <p>{result.insight}</p>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default function MessageBubble({ message }) {
    const isUser = message.role === "user";

    return (
        <div className={`message-row ${isUser ? "user-row" : "assistant-row"}`}>
            {!isUser && (
                <div className="avatar assistant-avatar">
                    <span>🦅</span>
                </div>
            )}
            <div className={`bubble-wrapper ${isUser ? "user-wrapper" : "assistant-wrapper"}`}>
                <div className={`bubble ${isUser ? "user-bubble" : "assistant-bubble"}`}>
                    {isUser ? (
                        <p className="user-text">{message.content}</p>
                    ) : (
                        <div className="markdown-body">
                            <ReactMarkdown>{message.content}</ReactMarkdown>
                        </div>
                    )}
                    {message.meta && (
                        <div className="bubble-meta">
                            {message.meta.boards_queried && (
                                <span className="meta-tag">
                                    📡 {message.meta.boards_queried.join(" + ")}
                                </span>
                            )}
                            {message.meta.data_counts && (
                                <span className="meta-tag">
                                    {Object.entries(message.meta.data_counts)
                                        .map(([k, v]) => `${v} ${k}`)
                                        .join(", ")}
                                </span>
                            )}
                        </div>
                    )}
                </div>

                {/* Charts rendered below the bubble */}
                {message.charts && message.charts.length > 0 && (
                    <ChartPanel charts={message.charts} />
                )}

                {/* Inline Ad Hoc Analysis — only on assistant messages */}
                {!isUser && <InlineAdhoc />}
            </div>

            {isUser && (
                <div className="avatar user-avatar">
                    <span>👤</span>
                </div>
            )}
        </div>
    );
}
