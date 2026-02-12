import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface PhaseInfo {
  id: string;
  name: string;
  order: number;
  enabled: boolean;
  required: boolean;
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

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = '/api';

  constructor(private http: HttpClient) {}

  // Health
  health(): Observable<HealthResponse> {
    return this.http.get<HealthResponse>(`${this.base}/health`);
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

  getLogs(filename = 'aicodegencrew.log', tail = 200): Observable<LogResponse> {
    const params = new HttpParams().set('filename', filename).set('tail', tail.toString());
    return this.http.get<LogResponse>(`${this.base}/logs`, { params });
  }

  // Diagrams
  getDiagrams(): Observable<{ diagrams: DiagramInfo[] }> {
    return this.http.get<{ diagrams: DiagramInfo[] }>(`${this.base}/diagrams`);
  }
}
