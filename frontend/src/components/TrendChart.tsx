import { formatDateTime } from "@/lib/format";

const COLOR_CLASS: Record<string, string> = {
  accent: "bg-accent",
  error: "bg-error",
  warning: "bg-warning",
};

export default function TrendChart({
  label,
  values,
  bucketStarts,
  color = "accent",
}: {
  label: string;
  values: number[];
  bucketStarts: string[];
  color?: "accent" | "error" | "warning";
}) {
  const max = Math.max(1, ...values);
  const total = values.reduce((sum, v) => sum + v, 0);
  const barClass = COLOR_CLASS[color] ?? COLOR_CLASS.accent;

  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="flex items-baseline justify-between mb-3">
        <span className="text-xs text-text-secondary uppercase tracking-wide">{label}</span>
        <span className="text-sm font-medium text-text-primary">{total}</span>
      </div>
      <div className="flex items-end gap-px h-16">
        {values.map((value, i) => (
          <div
            key={i}
            title={`${formatDateTime(bucketStarts[i])}: ${value}`}
            className={`flex-1 rounded-sm ${value > 0 ? barClass : "bg-border"} opacity-80 hover:opacity-100 transition-opacity`}
            style={{ height: `${Math.max(4, (value / max) * 100)}%` }}
          />
        ))}
      </div>
    </div>
  );
}
