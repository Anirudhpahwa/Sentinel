"use client";

import { useState } from "react";
import Link from "next/link";
import { deleteJob, listJobs } from "@/lib/api";
import { usePolling } from "@/lib/usePolling";
import { formatDateTime, formatJobType, formatRelative, formatSchedule } from "@/lib/format";
import StatusBadge from "@/components/StatusBadge";

const POLL_INTERVAL_MS = 5000;

export default function JobsPage() {
  const { data: jobs, error, isLoading, lastUpdatedAt, refetch } = usePolling(listJobs, POLL_INTERVAL_MS);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function handleDelete(jobId: string, jobName: string) {
    if (!window.confirm(`Are you sure you want to delete "${jobName}"? Future scheduling will stop, but historical execution records will remain.`)) {
      return;
    }
    setDeletingId(jobId);
    try {
      await deleteJob(jobId);
      refetch();
    } catch (err) {
      window.alert(err instanceof Error ? err.message : String(err));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-navy">Jobs</h1>
          <p className="text-sm text-text-secondary mt-1">
            {jobs ? `${jobs.length} job${jobs.length === 1 ? "" : "s"}` : "Loading…"} · Updated{" "}
            {formatRelative(lastUpdatedAt)}
          </p>
        </div>
        <Link
          href="/jobs/new"
          className="bg-navy text-white text-sm font-medium px-4 py-2 rounded-md hover:bg-navy-light transition-colors"
        >
          New Job
        </Link>
      </div>

      {error && (
        <div className="bg-error-soft text-error text-sm rounded-md px-4 py-3 border border-error/20">
          Failed to load jobs: {error.message}
        </div>
      )}

      <div className="bg-surface border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-surface-muted text-text-secondary text-xs uppercase tracking-wide">
              <th className="text-left font-medium px-4 py-3">Name</th>
              <th className="text-left font-medium px-4 py-3">Type</th>
              <th className="text-left font-medium px-4 py-3">Schedule</th>
              <th className="text-left font-medium px-4 py-3">Status</th>
              <th className="text-left font-medium px-4 py-3">Next Run</th>
              <th className="text-left font-medium px-4 py-3">Created By</th>
              <th className="text-left font-medium px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {jobs?.map((job) => (
              <tr key={job.id} className="hover:bg-surface-muted transition-colors">
                <td className="px-4 py-3">
                  <Link href={`/jobs/${job.id}`} className="font-medium text-navy hover:underline">
                    {job.name}
                  </Link>
                  {job.description && (
                    <div className="text-text-secondary text-xs mt-0.5 truncate max-w-xs">{job.description}</div>
                  )}
                </td>
                <td className="px-4 py-3 text-text-secondary">{formatJobType(job.job_type)}</td>
                <td className="px-4 py-3 text-text-secondary">{formatSchedule(job)}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={job.status} />
                </td>
                <td className="px-4 py-3 text-text-secondary font-mono text-xs">
                  {job.status === "ACTIVE" ? formatDateTime(job.next_run_at) : "—"}
                </td>
                <td className="px-4 py-3 text-text-secondary">{job.created_by}</td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => handleDelete(job.id, job.name)}
                    disabled={deletingId === job.id}
                    className="text-xs text-error hover:underline disabled:opacity-50"
                  >
                    {deletingId === job.id ? "Deleting…" : "Delete"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {!isLoading && jobs?.length === 0 && (
          <div className="px-4 py-10 text-center text-text-secondary text-sm">
            No jobs yet.{" "}
            <Link href="/jobs/new" className="text-accent hover:underline">
              Create your first job
            </Link>
            .
          </div>
        )}
      </div>
    </div>
  );
}
