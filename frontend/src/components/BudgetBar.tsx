interface BudgetBarProps {
  budgetSpent: number;
  budgetTotal: number;
}

export default function BudgetBar({ budgetSpent, budgetTotal }: BudgetBarProps) {
  const remaining = budgetTotal - budgetSpent;
  const pct = budgetTotal > 0 ? (budgetSpent / budgetTotal) * 100 : 0;
  const clampedPct = Math.min(pct, 100);

  const barColor =
    pct > 100
      ? "bg-red-500"
      : pct >= 80
        ? "bg-yellow-500"
        : "bg-green-500";

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">
          Общо: &euro;{budgetSpent.toFixed(2)} от &euro;{budgetTotal.toFixed(2)} бюджет
        </span>
        <span className="text-sm text-gray-500">
          Остатък: &euro;{remaining.toFixed(2)}
        </span>
      </div>

      <div className="w-full bg-gray-200 rounded-full h-3">
        <div
          className={`h-3 rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${clampedPct}%` }}
        />
      </div>

      <div className="flex justify-between mt-1">
        <span className="text-sm text-gray-500">{pct.toFixed(0)}%</span>
      </div>
    </div>
  );
}
