import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

export interface PhaseActionDialogData {
  phaseId: string;
  phaseName: string;
  status: string;
  lastRun?: string;
  durationSeconds?: number;
  pipelineRunning: boolean;
}

/** Result: 'start' navigates to run page, 'view' navigates to phase details. */
export type PhaseActionResult = 'start' | 'view' | null;

const PHASE_ICONS: Record<string, string> = {
  discover: 'search',
  extract: 'architecture',
  analyze: 'analytics',
  document: 'description',
  triage: 'assignment_turned_in',
  plan: 'map',
  implement: 'code',
  verify: 'verified',
  deliver: 'rocket_launch',
};

const PHASE_DESCRIPTIONS: Record<string, string> = {
  discover: 'Scan repository structure and build the knowledge index.',
  extract: 'Extract architecture facts, components, and relations from codebase.',
  analyze: 'Deep architecture quality analysis and pattern detection.',
  document: 'Generate C4 diagrams and Arc42 documentation.',
  triage: 'Classify issues and analyze context with LLM synthesis.',
  plan: 'Create evidence-based implementation plans.',
  implement: 'Generate code changes based on the plan.',
  verify: 'Run tests and quality checks on generated code.',
  deliver: 'Package results and prepare delivery artifacts.',
};

@Component({
  selector: 'app-phase-action-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule],
  template: `
    <div class="dialog-header">
      <div class="phase-icon-wrap" [class]="'icon-' + statusCategory()">
        <mat-icon>{{ phaseIcon() }}</mat-icon>
      </div>
      <div class="header-text">
        <h2 class="phase-title">{{ data.phaseName }}</h2>
        <div class="status-row">
          <span class="status-dot" [class]="'dot-' + data.status"></span>
          <span class="status-text">{{ statusText() }}</span>
          @if (data.durationSeconds) {
            <span class="duration-chip">{{ formatDuration(data.durationSeconds) }}</span>
          }
        </div>
      </div>
      <button class="close-btn" (click)="dialogRef.close(null)">
        <mat-icon>close</mat-icon>
      </button>
    </div>

    <mat-dialog-content>
      <p class="phase-desc">{{ phaseDescription() }}</p>

      @if (data.lastRun) {
        <div class="meta-row">
          <mat-icon class="meta-icon">schedule</mat-icon>
          <span class="meta-text">Last run: {{ data.lastRun | date: 'medium' }}</span>
        </div>
      }

      @if (data.pipelineRunning) {
        <div class="meta-row warning-row">
          <mat-icon class="meta-icon">info</mat-icon>
          <span class="meta-text">Pipeline is currently running</span>
        </div>
      }
    </mat-dialog-content>

    <mat-dialog-actions class="actions">
      @switch (statusCategory()) {
        @case ('ready') {
          <button mat-button (click)="dialogRef.close(null)">Cancel</button>
          <span class="spacer"></span>
          <button mat-flat-button color="primary" (click)="dialogRef.close('start')" [disabled]="data.pipelineRunning">
            <mat-icon>play_arrow</mat-icon>
            Start Phase
          </button>
        }
        @case ('done') {
          <button mat-button (click)="dialogRef.close(null)">Cancel</button>
          <span class="spacer"></span>
          <button mat-stroked-button (click)="dialogRef.close('start')" [disabled]="data.pipelineRunning">
            <mat-icon>replay</mat-icon>
            Re-run
          </button>
          <button mat-flat-button color="primary" (click)="dialogRef.close('view')">
            <mat-icon>visibility</mat-icon>
            View Results
          </button>
        }
        @case ('error') {
          <button mat-button (click)="dialogRef.close(null)">Cancel</button>
          <span class="spacer"></span>
          <button mat-stroked-button (click)="dialogRef.close('view')">
            <mat-icon>bug_report</mat-icon>
            View Details
          </button>
          <button mat-flat-button color="warn" (click)="dialogRef.close('start')" [disabled]="data.pipelineRunning">
            <mat-icon>refresh</mat-icon>
            Retry
          </button>
        }
        @default {
          <button mat-button (click)="dialogRef.close(null)">Cancel</button>
          <span class="spacer"></span>
          <button mat-flat-button color="primary" (click)="dialogRef.close('view')">
            <mat-icon>visibility</mat-icon>
            View Details
          </button>
        }
      }
    </mat-dialog-actions>
  `,
  styles: [
    `
      .dialog-header {
        display: flex;
        align-items: flex-start;
        gap: 14px;
        padding: 20px 24px 8px;
      }
      .phase-icon-wrap {
        width: 44px;
        height: 44px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
      }
      .phase-icon-wrap .mat-icon {
        font-size: 24px;
        width: 24px;
        height: 24px;
        color: #fff;
      }
      .icon-ready {
        background: var(--cg-blue, #0070ad);
      }
      .icon-done {
        background: var(--cg-success, #28a745);
      }
      .icon-error {
        background: var(--cg-error, #dc3545);
      }
      .icon-other {
        background: var(--cg-gray-400, #999);
      }
      .header-text {
        flex: 1;
        min-width: 0;
      }
      .phase-title {
        font-size: 18px;
        font-weight: 600;
        margin: 0 0 4px;
        color: var(--cg-gray-900, #1a1a1a);
      }
      .status-row {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
      }
      .dot-completed {
        background: var(--cg-success, #28a745);
      }
      .dot-partial {
        background: var(--cg-warning, #f0ad4e);
      }
      .dot-failed {
        background: var(--cg-error, #dc3545);
      }
      .dot-running {
        background: var(--cg-blue, #0070ad);
        animation: pulse 1.2s infinite;
      }
      .dot-pending,
      .dot-ready {
        background: var(--cg-gray-300, #ccc);
      }
      .dot-skipped {
        background: var(--cg-success, #28a745);
        opacity: 0.5;
      }
      .dot-cancelled {
        background: var(--cg-warning, #f0ad4e);
      }
      .status-text {
        font-size: 13px;
        font-weight: 500;
        color: var(--cg-gray-600, #666);
        text-transform: capitalize;
      }
      .duration-chip {
        font-size: 11px;
        padding: 1px 8px;
        border-radius: 10px;
        background: var(--cg-gray-100, #f0f0f0);
        color: var(--cg-gray-600, #666);
        font-weight: 500;
      }
      .close-btn {
        background: none;
        border: none;
        cursor: pointer;
        padding: 4px;
        color: var(--cg-gray-400, #999);
        border-radius: 50%;
        display: flex;
        transition: background 0.15s;
      }
      .close-btn:hover {
        background: var(--cg-gray-100, #f0f0f0);
      }
      .close-btn .mat-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
      }
      .phase-desc {
        font-size: 14px;
        color: var(--cg-gray-600, #555);
        line-height: 1.5;
        margin: 4px 0 12px;
      }
      .meta-row {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 6px;
      }
      .meta-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
        color: var(--cg-gray-400, #999);
      }
      .meta-text {
        font-size: 12px;
        color: var(--cg-gray-500, #777);
      }
      .warning-row .meta-icon {
        color: var(--cg-warning, #f0ad4e);
      }
      .warning-row .meta-text {
        color: var(--cg-warning, #f0ad4e);
        font-weight: 500;
      }
      .actions {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px 16px;
      }
      .spacer {
        flex: 1;
      }
      .actions .mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
        margin-right: 4px;
      }
      @keyframes pulse {
        0%,
        100% {
          opacity: 1;
        }
        50% {
          opacity: 0.4;
        }
      }
    `,
  ],
})
export class PhaseActionDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<PhaseActionDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: PhaseActionDialogData,
  ) {}

  phaseIcon(): string {
    return PHASE_ICONS[this.data.phaseId] || 'settings';
  }

  phaseDescription(): string {
    return PHASE_DESCRIPTIONS[this.data.phaseId] || `Run the ${this.data.phaseName} phase.`;
  }

  statusCategory(): 'ready' | 'done' | 'error' | 'other' {
    switch (this.data.status) {
      case 'pending':
      case 'ready':
      case 'skipped':
        return 'ready';
      case 'completed':
      case 'partial':
        return 'done';
      case 'failed':
      case 'cancelled':
        return 'error';
      default:
        return 'other';
    }
  }

  statusText(): string {
    const labels: Record<string, string> = {
      pending: 'Ready to run',
      ready: 'Ready to run',
      completed: 'Completed',
      partial: 'Partially completed',
      failed: 'Failed',
      cancelled: 'Cancelled',
      running: 'Running',
      skipped: 'Skipped',
    };
    return labels[this.data.status] || this.data.status;
  }

  formatDuration(seconds: number): string {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const min = Math.floor(seconds / 60);
    const sec = Math.round(seconds % 60);
    return sec > 0 ? `${min}m ${sec}s` : `${min}m`;
  }
}
