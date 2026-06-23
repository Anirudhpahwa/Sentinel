"use client";

import { useState } from "react";
import {
  archiveScheduler,
  listAdminActions,
  listSchedulers,
  resetDemoEnvironment,
  restoreScheduler,
  type EntityView,
  type ResetSummary,
} from "@/lib/api";
import { usePolling } from "@/lib/usePolling";
import { formatDateTime, formatRelative } from "@/lib/format";
import StatusBadge from "@/components/StatusBadge";

const POLL_INTERVAL_MS = 10000;

const TABS: { label: string; value: EntityView }[] = [
  { label: "Active Schedulers", value: "active" },
  { label: "Offline Schedulers", value: "offline" },
  { label: "Archived Schedulers", value: "archived" },
];

export default function AdminPage() {
  const [view, setView] = useState<EntityView>("active");
  const {
    data: schedulers,
    error: schedulersError,
    refetch: refetchSchedulers,
  } = usePolling(() => listSchedulers(view), POLL_INTERVAL_MS, [view]);
  const { data: actions, refetch: refetchActions } = usePolling(() => listAdminActions(20), POLL_INTERVAL_MS);

  const [actingId, setActingId] = useState<string | null>(null);
  const [resetting, setResetting] = useState(false);
  const [resetSummary, setResetSummary] = useState<ResetSummary | null>(null);

  async function handleToggleArchive(id: string, name: string, archived: boolean) {
    const verb = archived ? "restore" : "archive";
    if (!window.confirm(`Are you sure you want to ${verb} scheduler "${name}"?`)) return;
    setActingId(id);
    try {
      await (archived ? restoreScheduler(id) : archiveScheduler(id));
      refetchSchedulers();
      refetchActions();
    } catch (err) {
      window.alert(err instanceof Error ? err.message : String(err));
    } finally {
      setActingId(null);
    }
  }

  async function handleReset() {
    const typed = window.prompt(
      'This permanently deletes all jobs, executions, and logs, and archives offline workers/schedulers. This cannot be undone.\n\nType RESET to confirm.'
    );
    if (typed !== "RESET") return;
    setResetting(true);
    try {
      const summary = await resetDemoEnvironment();
      setResetSummary(summary);
      refetchSchedulers();
      refetchActions();
    } catch (err) {
      window.alert(err instanceof Error ? err.message : String(err));
    } finally {
      setResetting(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-lg font-semibold text-navy">Administration</h1>
        <p className="text-sm text-text-secondary mt-1">Maintenance tools for development and testing.</p>
      </div>

      <section>
        <h2 className="text-sm font-semibold text-navy uppercase tracking-wide mb-3">Scheduler Management</h2>
        <div className="flex gap-2 mb-3">
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

        {schedulersError && (
          <div className="bg-error-soft text-error text-sm rounded-md px-4 py-3 border border-error/20 mb-3">
            Failed to load schedulers: {schedulersError.message}
          </div>
        )}

        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-surface-muted text-text-secondary text-xs uppercase tracking-wide">
                <th className="text-left font-medium px-4 py-2">Scheduler</th>
                <th className="text-left font-medium px-4 py-2">Role</th>
                <th className="text-left font-medium px-4 py-2">Status</th>
                <th className="text-left font-medium px-4 py-2">Failed Attempts</th>
                <th className="text-left font-medium px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {schedulers?.map((scheduler) => (
                <tr key={scheduler.id}>
                  <td className="px-4 py-2 text-text-primary">{scheduler.scheduler_name}</td>
                  <td className="px-4 py-2">
                    <StatusBadge status={scheduler.role} />
                  </td>
                  <td className="px-4 py-2">
                    <StatusBadge status={scheduler.status} />
                  </td>
                  <td className="px-4 py-2 text-text-secondary">{scheduler.failed_election_attempts}</td>
                  <td className="px-4 py-2 text-right">
                    <button
                      onClick={() =>
                        handleToggleArchive(scheduler.id, scheduler.scheduler_name, scheduler.is_archived)
                      }
                      disabled={actingId === scheduler.id}
                      className="text-xs text-accent hover:underline disabled:opacity-50"
                    >
                      {actingId === scheduler.id ? "Working…" : scheduler.is_archived ? "Restore" : "Archive"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {schedulers?.length === 0 && (
            <div className="px-4 py-6 text-center text-text-secondary text-sm">No schedulers in this view.</div>
          )}
        </div>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-navy uppercase tracking-wide mb-3">Development Environment Reset</h2>
        <div className="bg-surface border border-error/30 rounded-lg p-4">
          <p className="text-sm text-text-secondary mb-3">
            Permanently deletes all jobs, executions, and logs. Archives workers and schedulers that are currently
            offline (active ones are left untouched). Database schema, configuration, and settings are unaffected.
            This is a development tool and cannot be undone.
          </p>
          <button
            onClick={handleReset}
            disabled={resetting}
            className="bg-error text-white text-sm font-medium px-4 py-2 rounded-md hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {resetting ? "Resetting…" : "Reset Demo Environment"}
          </button>
          {resetSummary && (
            <p className="text-xs text-text-secondary mt-3">
              Deleted {resetSummary.jobs_deleted} job(s) and {resetSummary.executions_deleted} execution(s); archived{" "}
              {resetSummary.workers_archived} worker(s) and {resetSummary.schedulers_archived} scheduler(s) at{" "}
              {formatDateTime(resetSummary.performed_at)}.
            </p>
          )}
        </div>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-navy uppercase tracking-wide mb-3">Recent Admin Actions</h2>
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-surface-muted text-text-secondary text-xs uppercase tracking-wide">
                <th className="text-left font-medium px-4 py-2">Action</th>
                <th className="text-left font-medium px-4 py-2">Target</th>
                <th className="text-left font-medium px-4 py-2">Detail</th>
                <th className="text-left font-medium px-4 py-2">When</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {actions?.map((action) => (
                <tr key={action.id}>
                  <td className="px-4 py-2 text-text-primary font-mono text-xs">{action.action}</td>
                  <td className="px-4 py-2 text-text-secondary text-xs">
                    {action.target_type}
                    {action.target_id ? ` (${action.target_id.slice(0, 8)})` : ""}
                  </td>
                  <td className="px-4 py-2 text-text-secondary text-xs">{action.detail ?? "—"}</td>
                  <td className="px-4 py-2 text-text-secondary font-mono text-xs">
                    {formatRelative(new Date(action.performed_at))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {actions?.length === 0 && (
            <div className="px-4 py-6 text-center text-text-secondary text-sm">No admin actions yet.</div>
          )}
        </div>
      </section>
    </div>
  );
}
