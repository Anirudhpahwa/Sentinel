"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { createJob, type JobType, type ScheduleType } from "@/lib/api";

const inputClass =
  "w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent";
const labelClass = "block text-sm font-medium text-text-primary mb-1";

export default function NewJobPage() {
  const router = useRouter();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [jobType, setJobType] = useState<JobType>("GENERATE_REPORT");
  const [scheduleType, setScheduleType] = useState<ScheduleType>("INTERVAL");
  const [runAt, setRunAt] = useState("");
  const [intervalSeconds, setIntervalSeconds] = useState(30);
  const [createdBy, setCreatedBy] = useState("anonymous");

  const [reportType, setReportType] = useState("daily");
  const [region, setRegion] = useState("global");
  const [dataset, setDataset] = useState("transactions");
  const [batchSize, setBatchSize] = useState(5000);
  const [channel, setChannel] = useState("email");

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (scheduleType === "ONCE" && !runAt) {
      setError("Please choose a run time for a one-time job.");
      return;
    }

    const payload =
      jobType === "GENERATE_REPORT"
        ? { report_type: reportType, region }
        : jobType === "PROCESS_DATA"
          ? { dataset, batch_size: batchSize }
          : { channel };

    const scheduleConfig =
      scheduleType === "ONCE" ? { run_at: new Date(runAt).toISOString() } : { interval_seconds: intervalSeconds };

    setSubmitting(true);
    try {
      const job = await createJob({
        name,
        description: description || undefined,
        job_type: jobType,
        payload,
        schedule_type: scheduleType,
        schedule_config: scheduleConfig,
        created_by: createdBy || "anonymous",
      });
      router.push(`/jobs/${job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-xl">
      <h1 className="text-lg font-semibold text-navy mb-6">New Job</h1>

      <form onSubmit={handleSubmit} className="bg-surface border border-border rounded-lg p-6 flex flex-col gap-5">
        <div>
          <label className={labelClass}>Name</label>
          <input
            className={inputClass}
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="Daily APAC Revenue Report"
          />
        </div>

        <div>
          <label className={labelClass}>Description</label>
          <textarea
            className={inputClass}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            placeholder="Optional context for what this job does"
          />
        </div>

        <div>
          <label className={labelClass}>Job Type</label>
          <select className={inputClass} value={jobType} onChange={(e) => setJobType(e.target.value as JobType)}>
            <option value="GENERATE_REPORT">Generate Report</option>
            <option value="PROCESS_DATA">Process Data</option>
            <option value="SEND_NOTIFICATION">Send Notification</option>
          </select>
        </div>

        {jobType === "GENERATE_REPORT" && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>Report Type</label>
              <input className={inputClass} value={reportType} onChange={(e) => setReportType(e.target.value)} />
            </div>
            <div>
              <label className={labelClass}>Region</label>
              <input className={inputClass} value={region} onChange={(e) => setRegion(e.target.value)} />
            </div>
          </div>
        )}

        {jobType === "PROCESS_DATA" && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>Dataset</label>
              <input className={inputClass} value={dataset} onChange={(e) => setDataset(e.target.value)} />
            </div>
            <div>
              <label className={labelClass}>Batch Size</label>
              <input
                type="number"
                className={inputClass}
                value={batchSize}
                onChange={(e) => setBatchSize(Number(e.target.value))}
                min={1}
              />
            </div>
          </div>
        )}

        {jobType === "SEND_NOTIFICATION" && (
          <div>
            <label className={labelClass}>Channel</label>
            <select className={inputClass} value={channel} onChange={(e) => setChannel(e.target.value)}>
              <option value="email">Email</option>
              <option value="sms">SMS</option>
            </select>
          </div>
        )}

        <hr className="border-border" />

        <div>
          <label className={labelClass}>Schedule</label>
          <select
            className={inputClass}
            value={scheduleType}
            onChange={(e) => setScheduleType(e.target.value as ScheduleType)}
          >
            <option value="INTERVAL">Run Every N Seconds</option>
            <option value="ONCE">Run Once</option>
          </select>
        </div>

        {scheduleType === "INTERVAL" ? (
          <div>
            <label className={labelClass}>Interval (seconds)</label>
            <input
              type="number"
              className={inputClass}
              value={intervalSeconds}
              onChange={(e) => setIntervalSeconds(Number(e.target.value))}
              min={5}
            />
          </div>
        ) : (
          <div>
            <label className={labelClass}>Run At</label>
            <input
              type="datetime-local"
              className={inputClass}
              value={runAt}
              onChange={(e) => setRunAt(e.target.value)}
              required
            />
          </div>
        )}

        <div>
          <label className={labelClass}>Created By</label>
          <input className={inputClass} value={createdBy} onChange={(e) => setCreatedBy(e.target.value)} />
        </div>

        {error && (
          <div className="bg-error-soft text-error text-sm rounded-md px-4 py-3 border border-error/20">{error}</div>
        )}

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={submitting}
            className="bg-navy text-white text-sm font-medium px-4 py-2 rounded-md hover:bg-navy-light transition-colors disabled:opacity-50"
          >
            {submitting ? "Creating…" : "Create Job"}
          </button>
        </div>
      </form>
    </div>
  );
}
