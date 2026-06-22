export type JobStatus = "ACTIVE" | "COMPLETED";
export type ExecutionStatus = "QUEUED" | "RUNNING" | "SUCCEEDED" | "FAILED";
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
