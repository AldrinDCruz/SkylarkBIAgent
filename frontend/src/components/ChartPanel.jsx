// ChartPanel.jsx – renders bar, donut, and area charts from structured chart_data
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell, Legend, AreaChart, Area, CartesianGrid,
} from "recharts";

const COLORS = [
    "#3b82f6", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b",
    "#ef4444", "#ec4899", "#14b8a6", "#6366f1", "#84cc16",
];

const formatINR = (val) => {
    if (val >= 1e7) return `₹${(val / 1e7).toFixed(1)}Cr`;
    if (val >= 1e5) return `₹${(val / 1e5).toFixed(1)}L`;
    if (val >= 1e3) return `₹${(val / 1e3).toFixed(0)}K`;
    return `₹${val}`;
};

const CustomTooltip = ({ active, payload, label, isAmount }) => {
    if (active && payload && payload.length) {
        return (
            <div className="chart-tooltip">
                {label && <p className="tooltip-label">{label}</p>}
                {payload.map((p, i) => (
                    <p key={i} style={{ color: p.color || "#60a5fa" }}>
                        {p.name}: <strong>{isAmount ? formatINR(p.value) : p.value}</strong>
                    </p>
                ))}
            </div>
        );
    }
    return null;
};

const CustomPieLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
    if (percent < 0.05) return null;
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);
    return (
        <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight={600}>
            {`${(percent * 100).toFixed(0)}%`}
        </text>
    );
};

function BarChartCard({ chart }) {
    const isAmount = chart.isAmount;
    return (
        <div className="chart-card">
            <h4 className="chart-title">{chart.title}</h4>
            <ResponsiveContainer width="100%" height={220}>
                <BarChart data={chart.data} margin={{ top: 4, right: 12, left: isAmount ? 20 : 0, bottom: 40 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2b44" />
                    <XAxis
                        dataKey="name"
                        tick={{ fill: "#94a3b8", fontSize: 11 }}
                        angle={-35}
                        textAnchor="end"
                        interval={0}
                    />
                    <YAxis
                        tick={{ fill: "#94a3b8", fontSize: 11 }}
                        tickFormatter={isAmount ? formatINR : undefined}
                        width={isAmount ? 60 : 35}
                    />
                    <Tooltip content={<CustomTooltip isAmount={isAmount} />} />
                    {(chart.bars || [{ key: "value", color: COLORS[0] }]).map((b, i) => (
                        <Bar key={b.key} dataKey={b.key} name={b.label || b.key} fill={b.color || COLORS[i]} radius={[4, 4, 0, 0]} />
                    ))}
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}

function DonutChartCard({ chart }) {
    return (
        <div className="chart-card">
            <h4 className="chart-title">{chart.title}</h4>
            <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                    <Pie
                        data={chart.data}
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={85}
                        dataKey="value"
                        nameKey="name"
                        labelLine={false}
                        label={CustomPieLabel}
                    >
                        {chart.data.map((_, i) => (
                            <Cell key={i} fill={COLORS[i % COLORS.length]} />
                        ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip isAmount={chart.isAmount} />} />
                    <Legend
                        wrapperStyle={{ fontSize: "11px", color: "#94a3b8", paddingTop: "8px" }}
                        formatter={(val) => <span style={{ color: "#94a3b8" }}>{val}</span>}
                    />
                </PieChart>
            </ResponsiveContainer>
        </div>
    );
}

function AreaChartCard({ chart }) {
    return (
        <div className="chart-card">
            <h4 className="chart-title">{chart.title}</h4>
            <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={chart.data} margin={{ top: 4, right: 12, left: 20, bottom: 4 }}>
                    <defs>
                        {(chart.areas || [{ key: "value" }]).map((a, i) => (
                            <linearGradient key={a.key} id={`grad${i}`} x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={COLORS[i]} stopOpacity={0.4} />
                                <stop offset="95%" stopColor={COLORS[i]} stopOpacity={0} />
                            </linearGradient>
                        ))}
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2b44" />
                    <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                    <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} tickFormatter={chart.isAmount ? formatINR : undefined} width={60} />
                    <Tooltip content={<CustomTooltip isAmount={chart.isAmount} />} />
                    {(chart.areas || [{ key: "value", label: "Value" }]).map((a, i) => (
                        <Area
                            key={a.key}
                            type="monotone"
                            dataKey={a.key}
                            name={a.label || a.key}
                            stroke={COLORS[i]}
                            fill={`url(#grad${i})`}
                            strokeWidth={2}
                        />
                    ))}
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}

export default function ChartPanel({ charts }) {
    if (!charts || charts.length === 0) return null;

    return (
        <div className="chart-panel">
            {charts.map((chart, i) => {
                if (chart.type === "donut" || chart.type === "pie") return <DonutChartCard key={i} chart={chart} />;
                if (chart.type === "area") return <AreaChartCard key={i} chart={chart} />;
                return <BarChartCard key={i} chart={chart} />;
            })}
        </div>
    );
}
