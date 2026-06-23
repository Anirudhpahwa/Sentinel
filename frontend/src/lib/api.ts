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
export type SchedulerRole = "LEADER" | "FOLLOWER";
export type SchedulerInstanceStatus = "ACTIVE" | "STALE";
export type EntityView = "active" | "offline" | "archived";

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
  deleted_at: string | null;
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
  worker_serial: number | null;
  status: WorkerStatus;
  is_archived: boolean;
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

export interface SchedulerInstance {
  id: string;
  scheduler_name: string;
  role: SchedulerRole;
  status: SchedulerInstanceStatus;
  is_archived: boolean;
  started_at: string;
  last_seen_at: string;
  failed_election_attempts: number;
}

export interface SchedulerElection {
  id: string;
  term: number;
  leader_id: string;
  elected_at: string;
}

export interface SchedulerMetrics {
  current_leader: string | null;
  leader_since: string | null;
  leader_uptime_seconds: number | null;
  active_schedulers: number;
  leader_elections_total: number;
  leadership_changes_recent: number;
  failed_election_attempts_total: number;
}

export interface AdminAction {
  id: string;
  action: string;
  target_type: string;
  target_id: string | null;
  detail: string | null;
  performed_at: string;
}

export interface ResetSummary {
  jobs_deleted: number;
  executions_deleted: number;
  workers_archived: number;
  schedulers_archived: number;
  performed_at: string;
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

export function listWorkers(view: EntityView = "active"): Promise<Worker[]> {
  return request(`/workers?view=${view}`);
}

export function archiveWorker(workerId: string): Promise<Worker> {
  return request(`/workers/${workerId}/archive`, { method: "POST" });
}

export function restoreWorker(workerId: string): Promise<Worker> {
  return request(`/workers/${workerId}/restore`, { method: "POST" });
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

export function listSchedulers(view: EntityView = "active"): Promise<SchedulerInstance[]> {
  return request(`/schedulers?view=${view}`);
}

export function archiveScheduler(schedulerId: string): Promise<SchedulerInstance> {
  return request(`/schedulers/${schedulerId}/archive`, { method: "POST" });
}

export function restoreScheduler(schedulerId: string): Promise<SchedulerInstance> {
  return request(`/schedulers/${schedulerId}/restore`, { method: "POST" });
}

export function listElections(limit = 10): Promise<SchedulerElection[]> {
  return request(`/schedulers/elections?limit=${limit}`);
}

export function getSchedulerMetrics(): Promise<SchedulerMetrics> {
  return request("/metrics/scheduler");
}

export function deleteJob(jobId: string): Promise<Job> {
  return request(`/jobs/${jobId}`, { method: "DELETE" });
}

export function listAdminActions(limit = 20): Promise<AdminAction[]> {
  return request(`/admin/actions?limit=${limit}`);
}

export function resetDemoEnvironment(): Promise<ResetSummary> {
  return request("/admin/reset-demo-environment", {
    method: "POST",
    body: JSON.stringify({ confirm: "RESET" }),
  });
}
