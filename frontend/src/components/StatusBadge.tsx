const STATUS_STYLES: Record<string, string> = {
  ACTIVE: "bg-accent-soft text-accent",
  COMPLETED: "bg-queued-soft text-queued",
  QUEUED: "bg-queued-soft text-queued",
  RUNNING: "bg-accent-soft text-accent",
  SUCCEEDED: "bg-success-soft text-success",
  FAILED: "bg-error-soft text-error",
  HEALTHY: "bg-success-soft text-success",
  UNHEALTHY: "bg-warning-soft text-warning",
  OFFLINE: "bg-error-soft text-error",
  REQUEUED: "bg-warning-soft text-warning",
  ABANDONED: "bg-warning-soft text-warning",
  PERMANENTLY_FAILED: "bg-error-soft text-error",
};

export default function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? "bg-queued-soft text-queued";
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${style}`}>
      {status}
    </span>
  );
}
