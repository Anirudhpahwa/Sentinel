"use client";

import { useState } from "react";
import { archiveWorker, listWorkers, restoreWorker, type EntityView } from "@/lib/api";
import { usePolling } from "@/lib/usePolling";
import { formatDateTime, formatRelative, formatRelativeFromIso } from "@/lib/format";
import StatusBadge from "@/components/StatusBadge";

const POLL_INTERVAL_MS = 5000;

const TABS: { label: string; value: EntityView }[] = [
  { label: "Active Workers", value: "active" },
  { label: "Offline Workers", value: "offline" },
  { label: "Archived Workers", value: "archived" },
];

export default function WorkersPage() {
  const [view, setView] = useState<EntityView>("active");
  const {
    data: workers,
    error,
    lastUpdatedAt,
    refetch,
  } = usePolling(() => listWorkers(view), POLL_INTERVAL_MS, [view]);
  const [actingId, setActingId] = useState<string | null>(null);

  async function handleToggleArchive(workerId: string, workerName: string, archived: boolean) {
    const verb = archived ? "restore" : "archive";
    if (!window.confirm(`Are you sure you want to ${verb} worker "${workerName}"?`)) {
      return;
    }
    setActingId(workerId);
    try {
      await (archived ? restoreWorker(workerId) : archiveWorker(workerId));
      refetch();
    } catch (err) {
      window.alert(err instanceof Error ? err.message : String(err));
    } finally {
      setActingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-lg font-semibold text-navy">Workers</h1>
        <p className="text-sm text-text-secondary mt-1">
          {workers ? `${workers.length} worker${workers.length === 1 ? "" : "s"}` : "Loading…"} · Updated{" "}
          {formatRelative(lastUpdatedAt)}
        </p>
      </div>

      <div className="flex gap-2">
        {TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setView(tab.value)}
            className={`text-sm px-3 py-1.5 rounded-md border transition-colors ${
              view === tab.value
                ? "bg-navy text-white border-navy"
                : "bg-surface text-text-secondary border-border hover:bg-surface-muted"
            }`}
          >
            {tab.label}
          </button>
        ))}
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
              <th className="text-left font-medium px-4 py-3"></th>
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
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => handleToggleArchive(worker.id, worker.worker_name, worker.is_archived)}
                    disabled={actingId === worker.id}
                    className="text-xs text-accent hover:underline disabled:opacity-50"
                  >
                    {actingId === worker.id ? "Working…" : worker.is_archived ? "Restore" : "Archive"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {workers?.length === 0 && (
          <div className="px-4 py-10 text-center text-text-secondary text-sm">No workers in this view.</div>
        )}
      </div>
    </div>
  );
}
