import type { Job } from "./api";

const JOB_TYPE_LABELS: Record<string, string> = {
  GENERATE_REPORT: "Generate Report",
  PROCESS_DATA: "Process Data",
  SEND_NOTIFICATION: "Send Notification",
};

export function formatJobType(jobType: string): string {
  return JOB_TYPE_LABELS[jobType] ?? jobType;
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function formatRelative(date: Date | null): string {
  if (!date) return "never";
  const seconds = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000));
  if (seconds < 5) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  return `${Math.round(seconds / 60)}m ago`;
}

export function formatRelativeFromIso(iso: string | null): string {
  if (!iso) return "never";
  return formatRelative(new Date(iso));
}

export function formatSchedule(job: Job): string {
  if (job.schedule_type === "ONCE") {
    const runAt = job.schedule_config["run_at"];
    return `Once at ${formatDateTime(typeof runAt === "string" ? runAt : null)}`;
  }
  if (job.schedule_type === "INTERVAL") {
    return `Every ${job.schedule_config["interval_seconds"]}s`;
  }
  return job.schedule_type;
}

export function formatResultSummary(result: Record<string, unknown> | null): string {
  if (!result) return "—";
  if (typeof result.error === "string") return result.error;
  return Object.entries(result)
    .map(([key, value]) => `${key}: ${value}`)
    .join("  ·  ");
}
