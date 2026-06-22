export type JobStatus = "ACTIVE" | "COMPLETED";
export type ExecutionStatus =
  | "QUEUED"
  | "REQUEUED"
  | "RUNNING"
  | "SUCCEEDED"
  | "FAILED"
  | "ABANDONED"
  | "PERMANENTLY_FAILED";
export type ScheduleType = "ONCE" | "INTERVAL";
export type JobType = "GENERATE_REPORT" | "PROCESS_DATA" | "SEND_NOTIFICATION";
export type LogLevel = "INFO" | "WARNING" | "ERROR";
export type WorkerStatus = "HEALTHY" | "UNHEALTHY" | "OFFLINE";

export interface Job {
  id: string;
  name: string;
  description: string | null;
  job_type: JobType;
  payload: Record<string, unknown>;
  schedule_type: ScheduleType;
  schedule_config: Record<string, unknown>;
  next_run_at: string;
  status: JobStatus;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface JobExecution {
  id: string;
  job_id: string;
  status: ExecutionStatus;
  queued_at: string;
  started_at: string | null;
  completed_at: string | null;
  result: Record<string, unknown> | null;
  worker_id: string | null;
  attempt_number: number;
  max_attempts: number;
  root_execution_id: string | null;
  abandoned_reason: string | null;
}

export interface ExecutionLog {
  id: number;
  execution_id: string;
  timestamp: string;
  level: LogLevel;
  message: string;
}

export interface Worker {
  id: string;
  worker_name: string;
  status: WorkerStatus;
  started_at: string;
  last_heartbeat_at: string;
  last_seen_at: string;
  executions_completed: number;
  executions_failed: number;
}

export interface JobMetrics {
  total_jobs: number;
  active_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  jobs_created_recent: number;
}

export interface ExecutionMetrics {
  executions_recent: number;
  executions_last_hour: number;
  successful_executions_recent: number;
  failed_executions_recent: number;
  average_duration_seconds: number | null;
  p95_duration_seconds: number | null;
  current_running: number;
}

export interface WorkerMetrics {
  total_workers: number;
  healthy_workers: number;
  unhealthy_workers: number;
  offline_workers: number;
  utilization_percent: number;
}

export interface RecoveryMetrics {
  recovery_attempts_recent: number;
  recovery_successes_recent: number;
  recovery_failures_recent: number;
  abandoned_executions_recent: number;
  requeued_executions_recent: number;
  recovery_success_rate_percent: number | null;
}

export interface QueueMetrics {
  queue_depth: number;
  oldest_pending_age_seconds: number | null;
  average_wait_seconds: number | null;
}

export interface OverviewMetrics {
  active_jobs: number;
  healthy_workers: number;
  queue_depth: number;
  executions_recent: number;
  success_rate_percent: number | null;
  recovery_count_recent: number;
}

export interface TrendBucket {
  bucket_start: string;
  executions: number;
  failures: number;
  recoveries: number;
}

export interface TrendsResponse {
  window_hours: number;
  buckets: TrendBucket[];
}

export interface CreateJobInput {
  name: string;
  description?: string;
  job_type: JobType;
  payload?: Record<string, unknown>;
  schedule_type: ScheduleType;
  schedule_config: Record<string, unknown>;
  created_by?: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export function listJobs(): Promise<Job[]> {
  return request("/jobs");
}

export function getJob(jobId: string): Promise<Job> {
  return request(`/jobs/${jobId}`);
}

export function createJob(input: CreateJobInput): Promise<Job> {
  return request("/jobs", { method: "POST", body: JSON.stringify(input) });
}

export function listJobExecutions(jobId: string): Promise<JobExecution[]> {
  return request(`/jobs/${jobId}/executions`);
}

export function getExecutionLogs(executionId: string): Promise<ExecutionLog[]> {
  return request(`/executions/${executionId}/logs`);
}

export function listWorkers(): Promise<Worker[]> {
  return request("/workers");
}

export function getOverviewMetrics(): Promise<OverviewMetrics> {
  return request("/metrics/overview");
}

export function getJobMetrics(): Promise<JobMetrics> {
  return request("/metrics/jobs");
}

export function getExecutionMetrics(): Promise<ExecutionMetrics> {
  return request("/metrics/executions");
}

export function getWorkerMetrics(): Promise<WorkerMetrics> {
  return request("/metrics/workers");
}

export function getRecoveryMetrics(): Promise<RecoveryMetrics> {
  return request("/metrics/recovery");
}

export function getQueueMetrics(): Promise<QueueMetrics> {
  return request("/metrics/queue");
}

export function getTrends(hours = 24): Promise<TrendsResponse> {
  return request(`/metrics/trends?hours=${hours}`);
}
