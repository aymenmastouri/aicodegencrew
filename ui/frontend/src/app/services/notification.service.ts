import { Injectable, OnDestroy } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { BehaviorSubject, Subscription, interval } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { PipelineService } from './pipeline.service';

export type PipelineState = 'idle' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface PipelineNotification {
  state: PipelineState;
  runId: string;
  fadingOut: boolean;
}

@Injectable({ providedIn: 'root' })
export class NotificationService implements OnDestroy {
  private state$ = new BehaviorSubject<PipelineNotification>({
    state: 'idle',
    runId: '',
    fadingOut: false,
  });

  readonly notification$ = this.state$.asObservable();

  private pollSub: Subscription | null = null;
  private fadeTimer: ReturnType<typeof setTimeout> | null = null;
  private previousState: PipelineState = 'idle';

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
    this.snackBar.open(msg, 'OK', { duration: 4000, panelClass: 'snack-success' });
  }

  error(msg: string): void {
    this.snackBar.open(msg, 'OK', { duration: 6000, panelClass: 'snack-error' });
  }

  info(msg: string): void {
    this.snackBar.open(msg, 'OK', { duration: 3000 });
  }

  dismiss(): void {
    this.state$.next({ state: 'idle', runId: '', fadingOut: false });
  }

  private startPolling(): void {
    this.pollSub = interval(5000)
      .pipe(switchMap(() => this.pipelineSvc.getStatus()))
      .subscribe({
        next: (status) => {
          const newState = (status.state || 'idle') as PipelineState;
          const runId = status.run_id || '';

          // Detect transitions
          if (this.previousState === 'running' && newState === 'completed') {
            this.success('Pipeline completed successfully');
            this.sendBrowserNotification('Pipeline Completed', 'Your pipeline run has finished successfully.');
          } else if (this.previousState === 'running' && newState === 'failed') {
            this.error('Pipeline failed');
            this.sendBrowserNotification('Pipeline Failed', 'Your pipeline run has failed.');
          }

          this.previousState = newState;

          // Auto-fade completed state after 10s
          if (this.fadeTimer) clearTimeout(this.fadeTimer);
          if (newState === 'completed') {
            this.fadeTimer = setTimeout(() => {
              this.state$.next({ state: 'idle', runId: '', fadingOut: false });
            }, 10000);
          }

          this.state$.next({ state: newState, runId, fadingOut: false });
        },
      });
  }

  private sendBrowserNotification(title: string, body: string): void {
    if (typeof Notification === 'undefined') return;
    if (Notification.permission === 'granted') {
      new Notification(title, { body, icon: 'assets/logos/Capgemini_Primary-logo_Capgemini-white.png' });
    } else if (Notification.permission !== 'denied') {
      Notification.requestPermission().then((perm) => {
        if (perm === 'granted') {
          new Notification(title, { body });
        }
      });
    }
  }
}
