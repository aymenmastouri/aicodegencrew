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

export interface PhaseProgress {
  phase_id: string;
  name: string;
  status: string;
  started_at?: string;
  duration_seconds?: number;
}

export interface ExecutionStatus {
  state: string;
  run_id?: string;
  preset?: string;
  phases: string[];
  started_at?: string;
  elapsed_seconds?: number;
  phase_progress: PhaseProgress[];
}

export interface RunHistoryEntry {
  run_id: string;
  status: string;
  preset?: string;
  phases: string[];
  started_at?: string;
  duration?: string;
  phase_results: Record<string, unknown>[];
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
