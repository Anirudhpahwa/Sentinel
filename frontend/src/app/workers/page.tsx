"use client";

import { listWorkers } from "@/lib/api";
import { usePolling } from "@/lib/usePolling";
import { formatDateTime, formatRelative, formatRelativeFromIso } from "@/lib/format";
import StatusBadge from "@/components/StatusBadge";

const POLL_INTERVAL_MS = 5000;

export default function WorkersPage() {
  const { data: workers, error, lastUpdatedAt } = usePolling(listWorkers, POLL_INTERVAL_MS);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-lg font-semibold text-navy">Workers</h1>
        <p className="text-sm text-text-secondary mt-1">
          {workers ? `${workers.length} worker${workers.length === 1 ? "" : "s"}` : "Loading…"} · Updated{" "}
          {formatRelative(lastUpdatedAt)}
        </p>
      </div>

      {error && (
        <div className="bg-error-soft text-error text-sm rounded-md px-4 py-3 border border-error/20">
          Failed to load workers: {error.message}
        </div>
      )}

      <div className="bg-surface border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-surface-muted text-text-secondary text-xs uppercase tracking-wide">
              <th className="text-left font-medium px-4 py-3">Worker ID</th>
              <th className="text-left font-medium px-4 py-3">Worker Name</th>
              <th className="text-left font-medium px-4 py-3">Status</th>
              <th className="text-left font-medium px-4 py-3">Last Heartbeat</th>
              <th className="text-left font-medium px-4 py-3">Started At</th>
              <th className="text-left font-medium px-4 py-3">Executions Completed</th>
              <th className="text-left font-medium px-4 py-3">Executions Failed</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {workers?.map((worker) => (
              <tr key={worker.id} className="hover:bg-surface-muted transition-colors">
                <td className="px-4 py-3 font-mono text-xs text-navy">
                  {worker.worker_serial !== null ? `docker-worker-${worker.worker_serial}` : "—"}
                </td>
                <td className="px-4 py-3 font-medium text-navy">{worker.worker_name}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={worker.status} />
                </td>
                <td className="px-4 py-3 text-text-secondary font-mono text-xs">
                  {formatRelativeFromIso(worker.last_heartbeat_at)}
                </td>
                <td className="px-4 py-3 text-text-secondary font-mono text-xs">
                  {formatDateTime(worker.started_at)}
                </td>
                <td className="px-4 py-3 text-text-secondary">{worker.executions_completed}</td>
                <td className="px-4 py-3 text-text-secondary">{worker.executions_failed}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {workers?.length === 0 && (
          <div className="px-4 py-10 text-center text-text-secondary text-sm">No workers have registered yet.</div>
        )}
      </div>
    </div>
  );
}
