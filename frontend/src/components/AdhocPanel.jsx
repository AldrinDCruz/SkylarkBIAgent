// AdhocPanel.jsx — Ad Hoc Analysis panel with dimension/metric pickers + chart + AI insight
import { useState } from "react";
import { runAdhocAnalysis } from "../api";
import ChartPanel from "./ChartPanel";

const DIMENSIONS = [
    { value: "sector", label: "Sector" },
    { value: "owner", label: "BD/KAM Owner" },
    { value: "stage", label: "Deal Stage" },
    { value: "status", label: "Deal Status" },
    { value: "platform", label: "Product / Platform" },
];

const METRICS = [
    { value: "deal_count", label: "Deal Count", group: "Deals" },
    { value: "deal_value", label: "Open Deal Value (₹)", group: "Deals" },
    { value: "win_rate", label: "Win Rate (%)", group: "Deals" },
    { value: "wo_count", label: "Work Order Count", group: "Operations" },
    { value: "billed", label: "Billed Value (₹)", group: "Revenue" },
    { value: "collected", label: "Collected (₹)", group: "Revenue" },
    { value: "ar", label: "Outstanding AR (₹)", group: "Revenue" },
];

export default function AdhocPanel({ onClose }) {
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
            setError(err.message || "Analysis failed. Is the backend running?");
        } finally {
            setLoading(false);
        }
    };

    const dimLabel = DIMENSIONS.find(d => d.value === dimension)?.label ?? dimension;
    const metricLabel = METRICS.find(m => m.value === metric)?.label ?? metric;

    return (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className="adhoc-modal">
                {/* Header */}
                <div className="adhoc-header">
                    <div className="adhoc-title">
                        <span className="adhoc-icon">📊</span>
                        <div>
                            <h2>Ad Hoc Analysis</h2>
                            <p>Pivot any metric by any dimension — get a chart + AI insight instantly</p>
                        </div>
                    </div>
                    <button className="close-btn" onClick={onClose} title="Close">×</button>
                </div>

                {/* Controls */}
                <div className="adhoc-controls">
                    <div className="adhoc-select-group">
                        <label className="adhoc-label">Group By (Dimension)</label>
                        <select
                            className="adhoc-select"
                            value={dimension}
                            onChange={e => setDimension(e.target.value)}
                        >
                            {DIMENSIONS.map(d => (
                                <option key={d.value} value={d.value}>{d.label}</option>
                            ))}
                        </select>
                    </div>

                    <div className="adhoc-select-group">
                        <label className="adhoc-label">Measure (Metric)</label>
                        <select
                            className="adhoc-select"
                            value={metric}
                            onChange={e => setMetric(e.target.value)}
                        >
                            {["Deals", "Operations", "Revenue"].map(group => (
                                <optgroup key={group} label={group}>
                                    {METRICS.filter(m => m.group === group).map(m => (
                                        <option key={m.value} value={m.value}>{m.label}</option>
                                    ))}
                                </optgroup>
                            ))}
                        </select>
                    </div>

                    <button
                        className="adhoc-run-btn"
                        onClick={handleRun}
                        disabled={loading}
                    >
                        {loading ? <span className="loading-spinner" /> : "▶ Run Analysis"}
                    </button>
                </div>

                {/* Results */}
                <div className="adhoc-results">
                    {error && (
                        <div className="adhoc-error">
                            ⚠️ {error}
                        </div>
                    )}

                    {!result && !error && !loading && (
                        <div className="adhoc-empty">
                            <span className="adhoc-empty-icon">🔍</span>
                            <p>Select a dimension and metric above, then click <strong>Run Analysis</strong></p>
                            <div className="adhoc-suggestions">
                                <span>Try:</span>
                                {[
                                    ["Sector", "Deal Value"],
                                    ["Owner", "Win Rate"],
                                    ["Status", "Deal Count"],
                                    ["Sector", "AR"],
                                ].map(([d, m]) => (
                                    <button
                                        key={d + m}
                                        className="adhoc-suggestion-chip"
                                        onClick={() => {
                                            const dv = DIMENSIONS.find(x => x.label === d)?.value;
                                            const mv = METRICS.find(x => x.label.startsWith(m))?.value;
                                            if (dv) setDimension(dv);
                                            if (mv) setMetric(mv);
                                        }}
                                    >
                                        {d} × {m}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {loading && (
                        <div className="adhoc-loading">
                            <span className="loading-spinner large-spinner" />
                            <p>Fetching live data and running AI analysis…</p>
                        </div>
                    )}

                    {result && (
                        <div className="adhoc-result-body">
                            {/* Summary bar */}
                            <div className="adhoc-summary-bar">
                                <div className="adhoc-summary-stat">
                                    <span className="stat-label">Total</span>
                                    <span className="stat-value">{result.summary.total_formatted}</span>
                                </div>
                                <div className="adhoc-summary-divider" />
                                <div className="adhoc-summary-stat">
                                    <span className="stat-label">Top — {result.summary.top_name}</span>
                                    <span className="stat-value highlight">{result.summary.top_value_formatted}</span>
                                </div>
                                <div className="adhoc-summary-divider" />
                                <div className="adhoc-summary-stat">
                                    <span className="stat-label">Records</span>
                                    <span className="stat-value">{result.summary.record_count}</span>
                                </div>
                            </div>

                            {/* Chart */}
                            <ChartPanel charts={[result.chart]} />

                            {/* AI Insight */}
                            <div className="adhoc-insight">
                                <div className="insight-header">
                                    <span className="insight-icon">🤖</span>
                                    <span className="insight-label">AI Insight — {dimLabel} × {metricLabel}</span>
                                </div>
                                <p className="insight-text">{result.insight}</p>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
