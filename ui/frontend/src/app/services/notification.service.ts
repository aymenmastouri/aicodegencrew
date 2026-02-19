import { Injectable, OnDestroy } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { BehaviorSubject, Subscription, timer, of } from 'rxjs';
import { switchMap, catchError } from 'rxjs/operators';
import { PipelineService } from './pipeline.service';

export type PipelineState = 'idle' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface PipelineNotification {
  state: PipelineState;
  runId: string;
  progressPercent: number;
  completedPhases: number;
  totalPhases: number;
  elapsedSeconds: number;
  etaSeconds: number | null;
}

@Injectable({ providedIn: 'root' })
export class NotificationService implements OnDestroy {
  private state$ = new BehaviorSubject<PipelineNotification>({
    state: 'idle',
    runId: '',
    progressPercent: 0,
    completedPhases: 0,
    totalPhases: 0,
    elapsedSeconds: 0,
    etaSeconds: null,
  });

  readonly notification$ = this.state$.asObservable();

  private pollSub: Subscription | null = null;
  private fadeTimer: ReturnType<typeof setTimeout> | null = null;
  private previousState: PipelineState = 'idle';
  private pollInterval = 5000;
  private dismissedRunId: string | null = null;

  constructor(
    private pipelineSvc: PipelineService,
    private snackBar: MatSnackBar,
  ) {
    this.startPolling();
  }

  ngOnDestroy(): void {
    this.pollSub?.unsubscribe();
    if (this.fadeTimer) clearTimeout(this.fadeTimer);
  }

  success(msg: string): void {
    this.snackBar.open(msg, 'OK', { duration: 4000 });
  }

  error(msg: string): void {
    this.snackBar.open(msg, 'OK', { duration: 6000 });
  }

  info(msg: string): void {
    this.snackBar.open(msg, 'OK', { duration: 3000 });
  }

  /** Force an immediate status poll (call after starting/cancelling a pipeline). */
  refreshNow(): void {
    this.dismissedRunId = null;
    this.restartPoll(3000);
  }

  dismiss(): void {
    // Remember which run was dismissed so polling doesn't resurrect it
    const current = this.state$.value;
    if (current.runId) {
      this.dismissedRunId = current.runId;
    }
    this.state$.next({
      state: 'idle',
      runId: '',
      progressPercent: 0,
      completedPhases: 0,
      totalPhases: 0,
      elapsedSeconds: 0,
      etaSeconds: null,
    });
  }

  private startPolling(): void {
    this.restartPoll(5000);
  }

  private restartPoll(interval: number): void {
    if (interval === this.pollInterval && this.pollSub) return;
    this.pollInterval = interval;
    this.pollSub?.unsubscribe();

    this.pollSub = timer(0, interval)
      .pipe(
        switchMap(() =>
          this.pipelineSvc.getStatus().pipe(
            catchError(() =>
              of({
                state: 'idle',
                run_id: undefined,
                phases: [] as string[],
                phase_progress: [],
                progress_percent: 0,
                completed_phase_count: 0,
                total_phase_count: 0,
                elapsed_seconds: 0,
                eta_seconds: undefined,
              }),
            ),
          ),
        ),
      )
      .subscribe({
        next: (status) => {
          const newState = (status.state || 'idle') as PipelineState;
          const runId = status.run_id || '';

          // Clear dismissed flag when a new run starts
          if (newState === 'running' && runId !== this.dismissedRunId) {
            this.dismissedRunId = null;
          }

          // Skip terminal states for dismissed runs
          if (this.dismissedRunId && runId === this.dismissedRunId && newState !== 'running') {
            return;
          }

          // Detect transitions (must run BEFORE restartPoll which re-subscribes)
          if (this.previousState === 'running' && newState === 'completed') {
            this.success('Pipeline completed successfully');
            this.sendBrowserNotification('Pipeline Completed', 'Your pipeline run has finished successfully.');
          } else if (this.previousState === 'running' && newState === 'failed') {
            this.error('Pipeline failed');
            this.sendBrowserNotification('Pipeline Failed', 'Your pipeline run has failed.');
          } else if (this.previousState === 'running' && newState === 'cancelled') {
            this.info('Pipeline cancelled');
          }

          this.previousState = newState;

          // Auto-fade terminal states
          if (this.fadeTimer) clearTimeout(this.fadeTimer);
          if (newState === 'completed') {
            this.fadeTimer = setTimeout(() => this.dismiss(), 10000);
          } else if (newState === 'failed') {
            this.fadeTimer = setTimeout(() => this.dismiss(), 30000);
          } else if (newState === 'cancelled') {
            this.fadeTimer = setTimeout(() => this.dismiss(), 5000);
          }

          this.state$.next({
            state: newState,
            runId,
            progressPercent: status.progress_percent ?? 0,
            completedPhases: status.completed_phase_count ?? 0,
            totalPhases: status.total_phase_count ?? 0,
            elapsedSeconds: status.elapsed_seconds ?? 0,
            etaSeconds: status.eta_seconds ?? null,
          });

          // Adjust poll frequency: 3s when running, 5s otherwise.
          // Done AFTER processing so transitions/fade/state are never skipped.
          const targetInterval = newState === 'running' ? 3000 : 5000;
          if (targetInterval !== this.pollInterval) {
            this.restartPoll(targetInterval);
          }
        },
      });
  }

  private sendBrowserNotification(title: string, body: string): void {
    if (typeof Notification === 'undefined') return;
    if (Notification.permission === 'granted') {
      new Notification(title, { body });
    } else if (Notification.permission !== 'denied') {
      Notification.requestPermission().then((perm) => {
        if (perm === 'granted') {
          new Notification(title, { body });
        }
      });
    }
  }
}
