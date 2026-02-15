import { Injectable, NgZone } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface RunRequest {
  preset?: string;
  phases?: string[];
  env_overrides?: Record<string, string>;
}

export interface RunResponse {
  run_id: string;
  status: string;
  message: string;
}

export interface SubPhaseProgress {
  name: string;
  status: string;
  duration_seconds?: number;
  total_tokens: number;
  tasks: string[];
}

export interface LiveMetrics {
  total_tokens: number;
  crew_completions: number;
}

export interface PhaseProgress {
  phase_id: string;
  name: string;
  status: string;
  started_at?: string;
  duration_seconds?: number;
  sub_phases?: SubPhaseProgress[];
  total_tokens?: number;
}

export interface ExecutionStatus {
  state: string;
  run_id?: string;
  preset?: string;
  phases: string[];
  started_at?: string;
  elapsed_seconds?: number;
  phase_progress: PhaseProgress[];
  progress_percent?: number;
  completed_phase_count?: number;
  total_phase_count?: number;
  eta_seconds?: number;
  live_metrics?: LiveMetrics;
}

export interface RunHistoryEntry {
  run_id: string;
  status: string;
  preset?: string;
  phases: string[];
  started_at?: string;
  completed_at?: string;
  duration?: string;
  duration_seconds?: number;
  trigger?: string; // "pipeline" | "reset"
  phase_results: Record<string, unknown>[];
  deleted_count?: number;
  total_tokens?: number;
}

export interface PhaseResultEntry {
  phase_id?: string;
  name?: string;
  status?: string;
  duration?: string;
  duration_seconds?: number;
  output_files?: string[];
  error?: string;
  [key: string]: unknown;
}

export interface MetricEventEntry {
  event?: string;
  timestamp?: string;
  [key: string]: unknown;
}

export interface HistoryStats {
  total_runs: number;
  total_resets: number;
  success_count: number;
  failed_count: number;
  success_rate: number;
  avg_duration_seconds: number;
  total_tokens: number;
  total_deleted_files: number;
  most_used_preset?: string;
  last_run_at?: string;
  phase_frequency: Record<string, number>;
}

export interface RunDetail {
  run_id: string;
  status: string;
  preset?: string;
  phases: string[];
  started_at?: string;
  completed_at?: string;
  duration?: string;
  duration_seconds?: number;
  trigger: string;
  phase_results: PhaseResultEntry[];
  metrics_events: MetricEventEntry[];
  environment: Record<string, unknown>;
}

export interface ResetPreview {
  phases_to_reset: string[];
  files_to_delete: string[];
}

export interface ResetResult {
  reset_phases: string[];
  deleted_count: number;
  timestamp: string;
}

export interface EnvVariable {
  name: string;
  value: string;
  description: string;
  group: string;
  required: boolean;
}

export interface SSEEvent {
  type: string;
  data: unknown;
}

@Injectable({ providedIn: 'root' })
export class PipelineService {
  private base = '/api';

  constructor(
    private http: HttpClient,
    private zone: NgZone,
  ) {}

  // Pipeline execution
  startPipeline(request: RunRequest): Observable<RunResponse> {
    return this.http.post<RunResponse>(`${this.base}/pipeline/run`, request);
  }

  cancelPipeline(): Observable<{ success: boolean; message: string }> {
    return this.http.post<{ success: boolean; message: string }>(`${this.base}/pipeline/cancel`, {});
  }

  getStatus(): Observable<ExecutionStatus> {
    return this.http.get<ExecutionStatus>(`${this.base}/pipeline/status`);
  }

  getHistory(): Observable<RunHistoryEntry[]> {
    return this.http.get<RunHistoryEntry[]>(`${this.base}/pipeline/history`);
  }

  getHistoryStats(): Observable<HistoryStats> {
    return this.http.get<HistoryStats>(`${this.base}/pipeline/history/stats`);
  }

  getRunDetail(runId: string): Observable<RunDetail> {
    return this.http.get<RunDetail>(`${this.base}/pipeline/history/${runId}`);
  }

  // Reset
  previewReset(phaseIds: string[], cascade = true): Observable<ResetPreview> {
    return this.http.post<ResetPreview>(`${this.base}/reset/preview`, {
      phase_ids: phaseIds,
      cascade,
    });
  }

  executeReset(phaseIds: string[], cascade = true): Observable<ResetResult> {
    return this.http.post<ResetResult>(`${this.base}/reset/execute`, {
      phase_ids: phaseIds,
      cascade,
    });
  }

  resetAll(): Observable<ResetResult> {
    return this.http.post<ResetResult>(`${this.base}/reset/all`, {});
  }

  clearPhaseState(phaseIds: string[]): Observable<{ cleared: string[] }> {
    return this.http.post<{ cleared: string[] }>(`${this.base}/reset/clear-state`, {
      phase_ids: phaseIds,
    });
  }

  // SSE stream
  connectSSE(): Observable<SSEEvent> {
    return new Observable<SSEEvent>((observer) => {
      const eventSource = new EventSource(`${this.base}/pipeline/stream`);

      eventSource.onmessage = (event) => {
        this.zone.run(() => {
          try {
            const parsed = JSON.parse(event.data) as SSEEvent;
            observer.next(parsed);

            if (parsed.type === 'pipeline_complete') {
              eventSource.close();
              observer.complete();
            }
          } catch {
            // Ignore parse errors
          }
        });
      };

      eventSource.onerror = () => {
        this.zone.run(() => {
          eventSource.close();
          observer.complete();
        });
      };

      return () => {
        eventSource.close();
      };
    });
  }

  // Environment config
  getEnv(): Observable<EnvVariable[]> {
    return this.http.get<EnvVariable[]>(`${this.base}/env`);
  }

  updateEnv(values: Record<string, string>): Observable<{ success: boolean }> {
    return this.http.put<{ success: boolean }>(`${this.base}/env`, { values });
  }

  getEnvSchema(): Observable<EnvVariable[]> {
    return this.http.get<EnvVariable[]>(`${this.base}/env/schema`);
  }
}
