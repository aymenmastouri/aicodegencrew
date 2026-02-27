import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface PhaseInfo {
  id: string;
  name: string;
  order: number;
  enabled: boolean;
  required: boolean;
  type: string;
  dependencies: string[];
}

export interface PhaseStatus {
  id: string;
  name: string;
  status: string;
  enabled: boolean;
  last_run?: string;
  duration_seconds?: number;
  output_exists: boolean;
  avg_duration_seconds?: number;
}

export interface PipelineStatus {
  phases: PhaseStatus[];
  active_preset?: string;
  is_running: boolean;
}

export interface PresetInfo {
  name: string;
  display_name: string;
  description: string;
  icon: string;
  phases: string[];
}

export interface KnowledgeFile {
  path: string;
  name: string;
  size_bytes: number;
  modified: string;
  type: string;
}

export interface KnowledgeSummary {
  total_files: number;
  total_size_bytes: number;
  files: KnowledgeFile[];
}

export interface MetricEvent {
  timestamp: string;
  event: string;
  data: Record<string, unknown>;
}

export interface MetricsSummary {
  total_events: number;
  events: MetricEvent[];
  run_ids: string[];
}

export interface ReportList {
  plans: Record<string, unknown>[];
  codegen_reports: Record<string, unknown>[];
  document_reports: Record<string, unknown>[];
}

export interface BranchInfo {
  name: string;
  task_id: string;
  file_count: number;
  has_report: boolean;
}

export interface BranchList {
  branches: BranchInfo[];
  repo_path: string;
}

export interface LogResponse {
  lines: string[];
  total_lines: number;
  file_path: string;
}

export interface DiagramInfo {
  name: string;
  path: string;
  type: string;
  size_bytes: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  knowledge_dir_exists: boolean;
  phases_config_exists: boolean;
}

export interface CollectorInfo {
  id: string;
  name: string;
  description: string;
  dimension: string;
  category: string;
  step: number;
  output_file: string;
  can_disable: boolean;
  enabled: boolean;
  fact_count: number | null;
  last_modified: string | null;
}

export interface CollectorListResponse {
  collectors: CollectorInfo[];
  total: number;
  enabled_count: number;
}

export interface SetupStatus {
  repo_configured: boolean;
  llm_configured: boolean;
  has_input_files: boolean;
  has_run_history: boolean;
}

export interface CollectorOutput {
  collector_id: string;
  data: unknown;
  fact_count: number;
  file_size_bytes: number;
}

export interface TaskPhaseSummary {
  status: 'not_started' | 'completed' | 'running' | 'failed';
  data: Record<string, unknown> | null;
  customer_md?: string;
  developer_md?: string;
  findings?: Record<string, unknown>;
}

export interface TaskSummary {
  task_id: string;
  classification_type?: string;
  risk_level?: string;
  phase_status: Record<string, string>;
  last_activity?: string;
}

export interface TaskLifecycle {
  task_id: string;
  has_input: boolean;
  phases: Record<string, TaskPhaseSummary>;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = '/api';

  constructor(private http: HttpClient) {}

  // Health
  health(): Observable<HealthResponse> {
    return this.http.get<HealthResponse>(`${this.base}/health`);
  }

  // Setup status (onboarding)
  getSetupStatus(): Observable<SetupStatus> {
    return this.http.get<SetupStatus>(`${this.base}/health/setup-status`);
  }

  // Phases
  getPhases(): Observable<PhaseInfo[]> {
    return this.http.get<PhaseInfo[]>(`${this.base}/phases`);
  }

  getPresets(): Observable<PresetInfo[]> {
    return this.http.get<PresetInfo[]>(`${this.base}/phases/presets`);
  }

  getPipelineStatus(): Observable<PipelineStatus> {
    return this.http.get<PipelineStatus>(`${this.base}/phases/status`);
  }

  // Knowledge
  getKnowledgeFiles(): Observable<KnowledgeSummary> {
    return this.http.get<KnowledgeSummary>(`${this.base}/knowledge`);
  }

  searchKnowledge(q: string): Observable<{ file: string; line: number; content: string }[]> {
    return this.http.get<{ file: string; line: number; content: string }[]>(`${this.base}/knowledge/search`, {
      params: new HttpParams().set('q', q),
    });
  }

  getKnowledgeFile(path: string): Observable<unknown> {
    return this.http.get(`${this.base}/knowledge/file`, {
      params: new HttpParams().set('path', path),
    });
  }

  // Metrics
  getMetrics(limit = 200, event?: string): Observable<MetricsSummary> {
    let params = new HttpParams().set('limit', limit.toString());
    if (event) params = params.set('event', event);
    return this.http.get<MetricsSummary>(`${this.base}/metrics`, { params });
  }

  // Reports
  getReports(): Observable<ReportList> {
    return this.http.get<ReportList>(`${this.base}/reports`);
  }

  getReport(type: string, taskId: string): Observable<unknown> {
    return this.http.get(`${this.base}/reports/${type}/${taskId}`);
  }

  // Branches
  getBranches(): Observable<BranchList> {
    return this.http.get<BranchList>(`${this.base}/reports/branches`);
  }

  deleteBranch(taskId: string): Observable<{ status: string }> {
    return this.http.delete<{ status: string }>(`${this.base}/reports/branches/${taskId}`);
  }

  // Logs
  getLogFiles(): Observable<string[]> {
    return this.http.get<string[]>(`${this.base}/logs/files`);
  }

  getLogs(filename = 'current.log', tail = 200): Observable<LogResponse> {
    const params = new HttpParams().set('filename', filename).set('tail', tail.toString());
    return this.http.get<LogResponse>(`${this.base}/logs`, { params });
  }

  // Architecture diagram
  getArchitectureDiagram(): Observable<{ mermaid: string }> {
    return this.http.get<{ mermaid: string }>(`${this.base}/knowledge/architecture/diagram`);
  }

  // Diagrams
  getDiagrams(): Observable<{ diagrams: DiagramInfo[] }> {
    return this.http.get<{ diagrams: DiagramInfo[] }>(`${this.base}/diagrams`);
  }

  // Collectors
  getCollectors(): Observable<CollectorListResponse> {
    return this.http.get<CollectorListResponse>(`${this.base}/collectors`);
  }

  toggleCollector(id: string, enabled: boolean): Observable<CollectorInfo> {
    return this.http.put<CollectorInfo>(`${this.base}/collectors/${id}/toggle`, { enabled });
  }

  getCollectorOutput(id: string): Observable<CollectorOutput> {
    return this.http.get<CollectorOutput>(`${this.base}/collectors/${id}/output`);
  }

  // Triage
  runFullTriage(body: {
    issue_id: string;
    title: string;
    description: string;
    task_file?: string;
    supplementary_files?: Record<string, string[]>;
  }): Observable<unknown> {
    return this.http.post(`${this.base}/triage`, body);
  }

  runQuickTriage(body: { title: string; description: string }): Observable<unknown> {
    return this.http.post(`${this.base}/triage/quick`, body);
  }

  getTriageResults(): Observable<{
    results: {
      issue_id: string;
      classification: Record<string, unknown>;
      risk_level?: string;
      entry_points_count?: number;
      blast_radius_count?: number;
      file: string;
    }[];
  }> {
    return this.http.get<{
      results: {
        issue_id: string;
        classification: Record<string, unknown>;
        risk_level?: string;
        entry_points_count?: number;
        blast_radius_count?: number;
        file: string;
      }[];
    }>(`${this.base}/triage/results`);
  }

  getTriageResult(issueId: string): Observable<{
    triage: Record<string, unknown>;
    customer_md?: string;
    developer_md?: string;
    findings?: Record<string, unknown>;
  }> {
    return this.http.get<{
      triage: Record<string, unknown>;
      customer_md?: string;
      developer_md?: string;
      findings?: Record<string, unknown>;
    }>(`${this.base}/triage/results/${issueId}`);
  }

  // Tasks (Lifecycle)
  getTasks(): Observable<{ tasks: TaskSummary[] }> {
    return this.http.get<{ tasks: TaskSummary[] }>(`${this.base}/tasks`);
  }

  getTaskLifecycle(taskId: string): Observable<TaskLifecycle> {
    return this.http.get<TaskLifecycle>(`${this.base}/tasks/${taskId}`);
  }
}
