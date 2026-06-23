"use client";

import { useMemo } from "react";
import Link from "next/link";
import {
  getOverviewMetrics,
  getWorkerMetrics,
  getExecutionMetrics,
  getRecoveryMetrics,
  getQueueMetrics,
  getSchedulerMetrics,
  getTrends,
  listElections,
  listSchedulers,
  listWorkers,
} from "@/lib/api";
import { usePolling } from "@/lib/usePolling";
import { formatPercent, formatSeconds, formatDateTime, formatRelative, formatRelativeFromIso } from "@/lib/format";
import MetricCard from "@/components/MetricCard";
import TrendChart from "@/components/TrendChart";
import StatusBadge from "@/components/StatusBadge";

// Aggregation queries are heavier than the simple row-fetches elsewhere in
// the app, and the underlying numbers don't meaningfully change faster than
// this -- so Operations polls slower than the 5s convention used elsewhere.
const POLL_INTERVAL_MS = 10000;
const TREND_WINDOW_HOURS = 24;

export default function OperationsPage() {
  const overview = usePolling(getOverviewMetrics, POLL_INTERVAL_MS);
  const workerMetrics = usePolling(getWorkerMetrics, POLL_INTERVAL_MS);
  const executionMetrics = usePolling(getExecutionMetrics, POLL_INTERVAL_MS);
  const recoveryMetrics = usePolling(getRecoveryMetrics, POLL_INTERVAL_MS);
  const queueMetrics = usePolling(getQueueMetrics, POLL_INTERVAL_MS);
  const schedulerMetrics = usePolling(getSchedulerMetrics, POLL_INTERVAL_MS);
  // "active" is the default view: archived, stale, and otherwise historical
  // scheduler instances never appear in this cluster-state table.
  const schedulers = usePolling(() => listSchedulers("active"), POLL_INTERVAL_MS);
  const elections = usePolling(() => listElections(5), POLL_INTERVAL_MS);
  const trends = usePolling(() => getTrends(TREND_WINDOW_HOURS), POLL_INTERVAL_MS);
  const workers = usePolling(listWorkers, POLL_INTERVAL_MS);

  const recentWorkers = useMemo(() => {
    if (!workers.data) return [];
    return [...workers.data]
      .sort((a, b) => new Date(b.last_heartbeat_at).getTime() - new Date(a.last_heartbeat_at).getTime())
      .slice(0, 5);
  }, [workers.data]);

  const o = overview.data;
  const w = workerMetrics.data;
  const e = executionMetrics.data;
  const r = recoveryMetrics.data;
  const q = queueMetrics.data;
  const sm = schedulerMetrics.data;
  const t = trends.data;

  const error =
    overview.error ||
    workerMetrics.error ||
    executionMetrics.error ||
    recoveryMetrics.error ||
    queueMetrics.error ||
    schedulers.error;

  const bucketStarts = t?.buckets.map((b) => b.bucket_start) ?? [];

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-navy">Operations</h1>
          <p className="text-sm text-text-secondary mt-1">Updated {formatRelative(overview.lastUpdatedAt)}</p>
        </div>
      </div>

      {error && (
        <div className="bg-error-soft text-error text-sm rounded-md px-4 py-3 border border-error/20">
          Failed to load metrics: {error.message}
        </div>
      )}

      <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <MetricCard label="Active Jobs" value={o ? String(o.active_jobs) : "—"} />
        <MetricCard
          label="Healthy Workers"
          value={o ? String(o.healthy_workers) : "—"}
          tone={o && o.healthy_workers === 0 ? "error" : "success"}
        />
        <MetricCard
          label="Queue Depth"
          value={o ? String(o.queue_depth) : "—"}
          tone={o && o.queue_depth > 10 ? "warning" : "default"}
        />
        <MetricCard label="Executions (24h)" value={o ? String(o.executions_recent) : "—"} />
        <MetricCard
          label="Success Rate"
          value={formatPercent(o?.success_rate_percent ?? null)}
          tone={o?.success_rate_percent != null && o.success_rate_percent < 90 ? "warning" : "success"}
        />
        <MetricCard
          label="Recovery Count (24h)"
          value={o ? String(o.recovery_count_recent) : "—"}
          tone={o && o.recovery_count_recent > 0 ? "warning" : "default"}
        />
      </section>

      <section>
        <h2 className="text-sm font-semibold text-navy uppercase tracking-wide mb-3">Worker Health</h2>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <MetricCard label="Healthy" value={w ? String(w.healthy_workers) : "—"} tone="success" />
          <MetricCard label="Unhealthy" value={w ? String(w.unhealthy_workers) : "—"} tone="warning" />
          <MetricCard label="Offline" value={w ? String(w.offline_workers) : "—"} tone="error" />
        </div>
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-surface-muted text-text-secondary text-xs uppercase tracking-wide">
                <th className="text-left font-medium px-4 py-2">Worker</th>
                <th className="text-left font-medium px-4 py-2">Status</th>
                <th className="text-left font-medium px-4 py-2">Last Heartbeat</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {recentWorkers.map((worker) => (
                <tr key={worker.id}>
                  <td className="px-4 py-2 text-text-primary">{worker.worker_name}</td>
                  <td className="px-4 py-2">
                    <StatusBadge status={worker.status} />
                  </td>
                  <td className="px-4 py-2 text-text-secondary font-mono text-xs">
                    {formatRelativeFromIso(worker.last_heartbeat_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {recentWorkers.length === 0 && (
            <div className="px-4 py-6 text-center text-text-secondary text-sm">No workers registered yet.</div>
          )}
        </div>
        <div className="mt-2 text-right">
          <Link href="/workers" className="text-xs text-accent hover:underline">
            View all workers →
          </Link>
        </div>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-navy uppercase tracking-wide mb-3">Execution Metrics</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <MetricCard
            label="Successful (24h)"
            value={e ? String(e.successful_executions_recent) : "—"}
            tone="success"
          />
          <MetricCard
            label="Failed (24h)"
            value={e ? String(e.failed_executions_recent) : "—"}
            tone={e && e.failed_executions_recent > 0 ? "error" : "default"}
          />
          <MetricCard label="Average Duration" value={e ? formatSeconds(e.average_duration_seconds) : "—"} />
          <MetricCard label="P95 Duration" value={e ? formatSeconds(e.p95_duration_seconds) : "—"} />
        </div>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-navy uppercase tracking-wide mb-3">Recovery</h2>
        <div className="grid grid-cols-3 gap-4">
          <MetricCard
            label="Abandoned Executions (24h)"
            value={r ? String(r.abandoned_executions_recent) : "—"}
            tone={r && r.abandoned_executions_recent > 0 ? "warning" : "default"}
          />
          <MetricCard
            label="Requeued Executions (24h)"
            value={r ? String(r.requeued_executions_recent) : "—"}
            tone={r && r.requeued_executions_recent > 0 ? "warning" : "default"}
          />
          <MetricCard label="Recovery Success Rate" value={formatPercent(r?.recovery_success_rate_percent ?? null)} />
        </div>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-navy uppercase tracking-wide mb-3">Queue</h2>
        <div className="grid grid-cols-3 gap-4">
          <MetricCard label="Queue Depth" value={q ? String(q.queue_depth) : "—"} />
          <MetricCard label="Oldest Pending" value={q ? formatSeconds(q.oldest_pending_age_seconds) : "—"} />
          <MetricCard label="Average Wait" value={q ? formatSeconds(q.average_wait_seconds) : "—"} />
        </div>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-navy uppercase tracking-wide mb-3">Scheduler</h2>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <MetricCard label="Current Leader" value={sm?.current_leader ?? "—"} />
          <MetricCard label="Scheduler Count" value={sm ? String(sm.active_schedulers) : "—"} />
          <MetricCard label="Leader Uptime" value={sm ? formatSeconds(sm.leader_uptime_seconds) : "—"} />
        </div>

        <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-2">Scheduler Status</h3>
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-surface-muted text-text-secondary text-xs uppercase tracking-wide">
                <th className="text-left font-medium px-4 py-2">Scheduler ID</th>
                <th className="text-left font-medium px-4 py-2">Role</th>
                <th className="text-left font-medium px-4 py-2">Status</th>
                <th className="text-left font-medium px-4 py-2">Leader Since</th>
                <th className="text-left font-medium px-4 py-2">Last Heartbeat</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {schedulers.data?.map((scheduler) => (
                <tr key={scheduler.id}>
                  <td className="px-4 py-2 text-text-primary font-mono text-xs">{scheduler.scheduler_name}</td>
                  <td className="px-4 py-2">
                    <StatusBadge status={scheduler.role} />
                  </td>
                  <td className="px-4 py-2">
                    <StatusBadge status={scheduler.status} />
                  </td>
                  <td className="px-4 py-2 text-text-secondary font-mono text-xs">
                    {scheduler.role === "LEADER" ? formatDateTime(sm?.leader_since ?? null) : "—"}
                  </td>
                  <td className="px-4 py-2 text-text-secondary font-mono text-xs">
                    {formatRelativeFromIso(scheduler.last_seen_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {schedulers.data?.length === 0 && (
            <div className="px-4 py-6 text-center text-text-secondary text-sm">No active schedulers.</div>
          )}
        </div>

        <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mt-5 mb-2">
          Recent Elections
        </h3>
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-surface-muted text-text-secondary text-xs uppercase tracking-wide">
                <th className="text-left font-medium px-4 py-2">Term</th>
                <th className="text-left font-medium px-4 py-2">Leader</th>
                <th className="text-left font-medium px-4 py-2">Elected At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {elections.data?.map((election) => (
                <tr key={election.id}>
                  <td className="px-4 py-2 text-text-secondary font-mono text-xs">{election.term}</td>
                  <td className="px-4 py-2 text-text-secondary font-mono text-xs">{election.leader_id}</td>
                  <td className="px-4 py-2 text-text-secondary font-mono text-xs">
                    {formatDateTime(election.elected_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {elections.data?.length === 0 && (
            <div className="px-4 py-6 text-center text-text-secondary text-sm">No elections recorded yet.</div>
          )}
        </div>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-navy uppercase tracking-wide mb-3">
          Historical Trends (last {TREND_WINDOW_HOURS}h)
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <TrendChart
            label="Executions"
            values={t?.buckets.map((b) => b.executions) ?? []}
            bucketStarts={bucketStarts}
            color="accent"
          />
          <TrendChart
            label="Failures"
            values={t?.buckets.map((b) => b.failures) ?? []}
            bucketStarts={bucketStarts}
            color="error"
          />
          <TrendChart
            label="Recoveries"
            values={t?.buckets.map((b) => b.recoveries) ?? []}
            bucketStarts={bucketStarts}
            color="warning"
          />
        </div>
      </section>
    </div>
  );
}
