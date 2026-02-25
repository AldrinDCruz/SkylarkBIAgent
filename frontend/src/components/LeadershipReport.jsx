// LeadershipReport.jsx – modal panel for leadership update briefing
import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { getLeadershipUpdate } from "../api";

export default function LeadershipReport({ onClose }) {
    const [content, setContent] = useState("");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function fetch() {
            try {
                const data = await getLeadershipUpdate();
                setContent(data.briefing);
            } catch (e) {
                setError(e.message);
            } finally {
                setLoading(false);
            }
        }
        fetch();
    }, []);

    const handleCopy = () => {
        navigator.clipboard.writeText(content);
    };

    return (
        <div className="report-overlay" onClick={onClose}>
            <div className="report-panel" onClick={(e) => e.stopPropagation()}>
                <div className="report-header">
                    <h2>📋 Leadership Update</h2>
                    <div className="report-actions">
                        {content && (
                            <button className="btn-secondary" onClick={handleCopy}>
                                📋 Copy
                            </button>
                        )}
                        <button className="btn-close" onClick={onClose}>✕</button>
                    </div>
                </div>
                <div className="report-body">
                    {loading && (
                        <div className="report-loading">
                            <div className="typing-indicator">
                                <span></span><span></span><span></span>
                            </div>
                            <p>Generating leadership briefing from live Monday.com data…</p>
                        </div>
                    )}
                    {error && (
                        <div className="report-error">
                            <p>⚠️ {error}</p>
                            <p className="error-hint">Make sure the backend is running and Monday.com credentials are configured.</p>
                        </div>
                    )}
                    {content && !loading && (
                        <div className="markdown-body report-markdown">
                            <ReactMarkdown>{content}</ReactMarkdown>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
