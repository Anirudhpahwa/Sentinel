"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getExecutionLogs, getJob, listJobExecutions, type ExecutionLog } from "@/lib/api";
import { usePolling } from "@/lib/usePolling";
import { formatDateTime, formatJobType, formatOutcome, formatRelative, formatSchedule } from "@/lib/format";
import StatusBadge from "@/components/StatusBadge";

const POLL_INTERVAL_MS = 5000;

const LOG_LEVEL_COLOR: Record<string, string> = {
  INFO: "text-text-secondary",
  WARNING: "text-amber-600",
  ERROR: "text-error",
};

export default function JobDetailPage() {
  const params = useParams<{ id: string }>();
  const jobId = params.id;

  const { data: job, error: jobError } = usePolling(() => getJob(jobId), POLL_INTERVAL_MS, [jobId]);
  const {
    data: executions,
    error: executionsError,
    lastUpdatedAt,
  } = usePolling(() => listJobExecutions(jobId), POLL_INTERVAL_MS, [jobId]);

  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [logsState, setLogsState] = useState<{ id: string; logs: ExecutionLog[] } | null>(null);

  // Derived rather than separate state: avoids a "loading" flicker on every
  // background poll, and stale logs from a previously expanded row never
  // leak into view since both are gated on matching the current expandedId.
  const logs = logsState?.id === expandedId ? logsState.logs : [];
  const logsLoading = expandedId !== null && logsState?.id !== expandedId;

  useEffect(() => {
    if (!expandedId) {
      return;
    }
    let cancelled = false;
    getExecutionLogs(expandedId)
      .then((data) => {
        if (!cancelled) setLogsState({ id: expandedId, logs: data });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
    // Refetch whenever the executions list refreshes, so an expanded row's
    // logs keep streaming in at the same cadence as everything else polls.
  }, [expandedId, executions]);

  if (jobError) {
    return <div className="text-error text-sm">Failed to load job: {jobError.message}</div>;
  }

  return (
    <div className="flex flex-col gap-6">
      {job && (
        <div className="bg-surface border border-border rounded-lg p-6">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-lg font-semibold text-navy">{job.name}</h1>
              {job.description && <p className="text-sm text-text-secondary mt-1">{job.description}</p>}
            </div>
            <StatusBadge status={job.status} />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-5 text-sm">
            <Detail label="Type" value={formatJobType(job.job_type)} />
            <Detail label="Schedule" value={formatSchedule(job)} />
            <Detail label="Next Run" value={job.status === "ACTIVE" ? formatDateTime(job.next_run_at) : "—"} mono />
            <Detail label="Created By" value={job.created_by} />
          </div>
        </div>
      )}

      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-navy uppercase tracking-wide">Execution History</h2>
          <p className="text-xs text-text-secondary">Updated {formatRelative(lastUpdatedAt)}</p>
        </div>

        {executionsError && (
          <div className="bg-error-soft text-error text-sm rounded-md px-4 py-3 border border-error/20 mb-3">
            Failed to load executions: {executionsError.message}
          </div>
        )}

        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-surface-muted text-text-secondary text-xs uppercase tracking-wide">
                <th className="text-left font-medium px-4 py-3">Status</th>
                <th className="text-left font-medium px-4 py-3">Attempt</th>
                <th className="text-left font-medium px-4 py-3">Queued</th>
                <th className="text-left font-medium px-4 py-3">Started</th>
                <th className="text-left font-medium px-4 py-3">Completed</th>
                <th className="text-left font-medium px-4 py-3">Worker</th>
                <th className="text-left font-medium px-4 py-3">Outcome</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {executions?.map((execution) => (
                <>
                  <tr
                    key={execution.id}
                    onClick={() => setExpandedId(expandedId === execution.id ? null : execution.id)}
                    className="hover:bg-surface-muted transition-colors cursor-pointer"
                  >
                    <td className="px-4 py-3">
                      <StatusBadge status={execution.status} />
                    </td>
                    <td className="px-4 py-3 text-text-secondary font-mono text-xs">
                      {execution.attempt_number} / {execution.max_attempts}
                    </td>
                    <td className="px-4 py-3 text-text-secondary font-mono text-xs">
                      {formatDateTime(execution.queued_at)}
                    </td>
                    <td className="px-4 py-3 text-text-secondary font-mono text-xs">
                      {formatDateTime(execution.started_at)}
                    </td>
                    <td className="px-4 py-3 text-text-secondary font-mono text-xs">
                      {formatDateTime(execution.completed_at)}
                    </td>
                    <td className="px-4 py-3 text-text-secondary text-xs">{execution.worker_id ?? "—"}</td>
                    <td
                      className={`px-4 py-3 text-xs ${
                        execution.status === "FAILED" || execution.status === "PERMANENTLY_FAILED"
                          ? "text-error"
                          : execution.status === "ABANDONED"
                            ? "text-warning"
                            : "text-text-secondary"
                      }`}
                    >
                      {formatOutcome(execution)}
                    </td>
                  </tr>
                  {expandedId === execution.id && (
                    <tr key={`${execution.id}-logs`}>
                      <td colSpan={7} className="bg-surface-muted px-4 py-3">
                        {logsLoading && logs.length === 0 ? (
                          <p className="text-xs text-text-secondary">Loading logs…</p>
                        ) : logs.length === 0 ? (
                          <p className="text-xs text-text-secondary">No logs yet.</p>
                        ) : (
                          <ul className="font-mono text-xs flex flex-col gap-1">
                            {logs.map((log) => (
                              <li key={log.id} className="flex gap-3">
                                <span className="text-text-secondary">{formatDateTime(log.timestamp)}</span>
                                <span className={`${LOG_LEVEL_COLOR[log.level] ?? "text-text-secondary"} w-16`}>
                                  {log.level}
                                </span>
                                <span className="text-text-primary">{log.message}</span>
                              </li>
                            ))}
                          </ul>
                        )}
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>

          {executions?.length === 0 && (
            <div className="px-4 py-10 text-center text-text-secondary text-sm">
              No executions yet. The scheduler will enqueue this job once it&apos;s due.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Detail({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="text-xs text-text-secondary uppercase tracking-wide">{label}</div>
      <div className={`mt-0.5 text-text-primary ${mono ? "font-mono text-xs" : ""}`}>{value}</div>
    </div>
  );
}
