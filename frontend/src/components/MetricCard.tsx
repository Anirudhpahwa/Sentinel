export default function MetricCard({
  label,
  value,
  subtitle,
  tone = "default",
}: {
  label: string;
  value: string;
  subtitle?: string;
  tone?: "default" | "success" | "warning" | "error";
}) {
  const toneClass =
    tone === "success"
      ? "text-success"
      : tone === "warning"
        ? "text-warning"
        : tone === "error"
          ? "text-error"
          : "text-navy";

  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="text-xs text-text-secondary uppercase tracking-wide">{label}</div>
      <div className={`mt-1 text-2xl font-semibold ${toneClass}`}>{value}</div>
      {subtitle && <div className="mt-0.5 text-xs text-text-secondary">{subtitle}</div>}
    </div>
  );
}
