// QuickChips.jsx – grouped starter question chips
const CHIP_GROUPS = [
    {
        label: "PIPELINE & GROWTH",
        icon: "🚀",
        chips: [
            {
                icon: "📈",
                label: "How's the pipeline looking this week?",
                query: "Give me a complete pipeline summary — total open deals, key sectors and top opportunities.",
            },
            {
                icon: "⚡",
                label: "Energy sector performance summary",
                query: "How's our pipeline looking for the energy sector (Renewables + Powerline) this quarter?",
            },
        ],
    },
    {
        label: "FINANCE & COLLECTIONS",
        icon: "💰",
        chips: [
            {
                icon: "🏛️",
                label: "Detailed billing & collections status",
                query: "Give me a billing and collections summary — contracted, billed, collected, and outstanding AR.",
            },
            {
                icon: "⚠️",
                label: "Identify all at-risk deals above 50L",
                query: "What deals above ₹50L are overdue or at risk of slipping? Flag low probability and late-stage deals.",
            },
        ],
    },
    {
        label: "OPERATIONS",
        icon: "⚙️",
        chips: [
            {
                icon: "✅",
                label: "Active work orders by priority",
                query: "How many active work orders do we have and which are stuck or paused? Break down by sector.",
            },
            {
                icon: "🏆",
                label: "Top BD performers this quarter",
                query: "Who is our top performing BD/KAM owner? Break it down by deal value and win rate.",
            },
        ],
    },
];

export default function QuickChips({ onSelect }) {
    return (
        <div className="chips-wrapper">
            <p className="chips-header-label">Ask a question or pick a starting point</p>
            {CHIP_GROUPS.map((group) => (
                <div key={group.label} className="chip-group">
                    <div className="chip-group-label">
                        <span>{group.icon}</span>
                        <span>{group.label}</span>
                    </div>
                    <div className="chip-group-grid">
                        {group.chips.map((chip) => (
                            <button
                                key={chip.label}
                                className="chip-card"
                                onClick={() => onSelect(chip.query)}
                            >
                                <span className="chip-card-icon">{chip.icon}</span>
                                <span className="chip-card-label">{chip.label}</span>
                            </button>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
}
