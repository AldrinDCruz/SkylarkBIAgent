// DashboardView.jsx – Redesigned Executive Dashboard
import { useState, useEffect, useCallback } from "react";
import ChartPanel from "./ChartPanel";
import { fetchDashboardData } from "../api";

export default function DashboardView() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [useMock, setUseMock] = useState(false);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetchDashboardData(useMock);
            setData(res);
        } catch (e) {
            setError(e.message || "Failed to load dashboard data");
        } finally {
            setLoading(false);
        }
    }, [useMock]);

    useEffect(() => {
        load();
    }, [load]);

    if (loading) {
        return (
            <div className="db-loading-full">
                <span className="loading-spinner-lg" />
                <p>Loading business intelligence dashboard...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="db-error-full">
                <h2>⚠️ Dashboard Error</h2>
                <p>{error}</p>
                <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                    <button className="btn-retry" onClick={load}>Try Again</button>
                    {!useMock && (
                        <button className="btn-retry" onClick={() => setUseMock(true)} style={{ background: 'var(--accent-purple)' }}>
                            View Mock Data
                        </button>
                    )}
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard-container">
            {/* ── Dashboard Header ───────────────────────── */}
            <div className="db-header-new">
                <div className="db-title-group">
                    <h1>📊 Business Dashboard</h1>
                    <p className="db-subtitle">
                        {useMock ? "Showing Sample Executive Data" : "Live data from Monday.com"} • Updated {data.summary?.last_updated}
                    </p>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <label className="mock-toggle" style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontSize: '0.8rem',
                        color: 'var(--text-muted)',
                        cursor: 'pointer'
                    }}>
                        <input
                            type="checkbox"
                            checked={useMock}
                            onChange={(e) => setUseMock(e.target.checked)}
                        />
                        Mock Mode
                    </label>

                    {data.summary?.missing_data_hint && (
                        <div className="db-alert">
                            ⚠️ {data.summary.missing_data_hint}
                        </div>
                    )}
                </div>
            </div>

            {/* ── KPI Cards Grid ─────────────────────────── */}
            <div className="kpi-grid">
                {data.kpis?.map((kpi) => (
                    <div key={kpi.id} className="kpi-card" style={{ "--accent": kpi.color }}>
                        <div className="kpi-header">
                            <span className="kpi-icon">{kpi.icon}</span>
                        </div>
                        <div className="kpi-body">
                            <h2 className="kpi-value">{kpi.value}</h2>
                            <p className="kpi-label">{kpi.label}</p>
                            <p className="kpi-sub">{kpi.sub}</p>
                        </div>
                        <div className="kpi-border" />
                    </div>
                ))}
            </div>

            {/* ── Sales & Operations Sections ──────────────── */}
            <div className="db-sections-grid">
                {/* Sales Section */}
                <div className="db-section-box">
                    <h3 className="section-group-title">📈 SALES PIPELINE ANALYSIS</h3>
                    <div className="db-charts-subgrid">
                        {data.charts?.filter(c => c.id !== 'billing_status_ops').map((chart) => (
                            <div key={chart.id} className="db-chart-tile">
                                <h4 className="chart-label-sm">{chart.title}</h4>
                                <div className="chart-content">
                                    <ChartPanel charts={[chart]} />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Operations Section */}
                <div className="db-section-box">
                    <h3 className="section-group-title">🛠️ OPERATIONS & BILLING</h3>
                    <div className="db-charts-subgrid">
                        {data.charts?.filter(c => c.id === 'billing_status_ops').map((chart) => (
                            <div key={chart.id} className="db-chart-tile">
                                <h4 className="chart-label-sm">{chart.title}</h4>
                                <div className="chart-content">
                                    <ChartPanel charts={[chart]} />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* ── Performance Table ───────────────────────── */}
            <div className="db-table-section">
                <h3 className="section-title">TOP ACTIVE PROJECTS & BILLING STATUS</h3>
                <div className="table-wrapper">
                    <table className="db-table">
                        <thead>
                            <tr>
                                <th>PROJECT / WORK ORDER</th>
                                <th>SECTOR</th>
                                <th>STATUS</th>
                                <th className="text-right">CONTRACT VALUE</th>
                                <th className="text-right">RECEIVABLE</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.top_work_orders?.map((wo, idx) => (
                                <tr key={idx}>
                                    <td className="font-semibold">{wo.work_order}</td>
                                    <td>
                                        <span className="badge-sector">{wo.sector}</span>
                                    </td>
                                    <td>
                                        <span className={`status-badge ${wo.status.toLowerCase().replace(/ /g, "-")}`}>
                                            {wo.status}
                                        </span>
                                    </td>
                                    <td className="text-right font-mono">{wo.contract_value}</td>
                                    <td className={`text-right font-mono ${wo.is_ar_high ? "text-danger" : ""}`}>
                                        {wo.receivable}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
