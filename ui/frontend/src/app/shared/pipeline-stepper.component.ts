import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { PhaseProgress } from '../services/pipeline.service';
import { humanizePhaseId, formatDuration } from './phase-utils';

@Component({
  selector: 'app-pipeline-stepper',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatProgressSpinnerModule],
  template: `
    <div
      class="stepper-track"
      [style.--circle-size.px]="circleSize"
      [style.--step-min-width.px]="stepMinWidth"
      [style.padding]="padding"
    >
      @for (step of steps; track step.phase_id; let i = $index; let last = $last) {
        <div class="stepper-step" [class]="'step-' + step.status">
          <div class="step-circle">
            @if (step.status === 'completed') {
              <mat-icon class="step-check">check</mat-icon>
            } @else if (step.status === 'partial') {
              <mat-icon class="step-warn">warning</mat-icon>
            } @else if (step.status === 'running') {
              <mat-spinner diameter="22" class="step-spinner"></mat-spinner>
            } @else if (step.status === 'failed') {
              <mat-icon class="step-fail">close</mat-icon>
            } @else if (step.status === 'cancelled') {
              <mat-icon class="step-cancel">stop</mat-icon>
            } @else if (step.status === 'skipped') {
              <mat-icon class="step-check-alt">check_circle</mat-icon>
            } @else {
              <span class="step-num">{{ i + 1 }}</span>
            }
          </div>
          <div class="step-label">{{ step.name || humanize(step.phase_id) }}</div>
          @if ((step.status === 'completed' || step.status === 'partial') && step.duration_seconds) {
            <div class="step-time">{{ fmt(step.duration_seconds) }}</div>
          }
          @if (step.status === 'running') {
            <div class="step-time step-time-active">
              {{ step.duration_seconds ? fmt(step.duration_seconds) : 'running' }}
            </div>
          }
          @if (step.status === 'skipped') {
            <div class="step-time step-time-uptodate">up to date</div>
          }
          @if (step.status === 'cancelled') {
            <div class="step-time step-time-cancelled">cancelled</div>
          }
        </div>
        @if (!last) {
          <div
            class="stepper-line"
            [class.line-done]="step.status === 'completed' || step.status === 'partial' || step.status === 'skipped'"
            [class.line-active]="step.status === 'running'"
          ></div>
        }
      }
    </div>
  `,
  styles: [
    `
      .stepper-track {
        display: flex;
        align-items: flex-start;
        overflow-x: auto;
      }
      .stepper-step {
        display: flex;
        flex-direction: column;
        align-items: center;
        flex-shrink: 0;
        min-width: var(--step-min-width, 100px);
      }
      .step-circle {
        width: var(--circle-size, 42px);
        height: var(--circle-size, 42px);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--cg-gray-50, #f8f9fa);
        border: 2.5px solid var(--cg-gray-200);
        position: relative;
        z-index: 1;
        transition: all 0.3s ease;
      }
      .step-num {
        font-size: 13px;
        font-weight: 600;
        color: var(--cg-gray-400);
      }
      /* Running */
      .step-running .step-circle {
        background: rgba(0, 112, 173, 0.08);
        border-color: var(--cg-blue);
        box-shadow: 0 0 0 5px rgba(0, 112, 173, 0.1);
        animation: pulse-ring 2s ease-in-out infinite;
      }
      @keyframes pulse-ring {
        0%,
        100% {
          box-shadow: 0 0 0 5px rgba(0, 112, 173, 0.1);
        }
        50% {
          box-shadow: 0 0 0 10px rgba(0, 112, 173, 0.04);
        }
      }
      .step-spinner ::ng-deep circle {
        stroke: var(--cg-blue) !important;
      }
      /* Completed */
      .step-completed .step-circle {
        background: var(--cg-success, #28a745);
        border-color: var(--cg-success, #28a745);
      }
      .step-check {
        font-size: 18px;
        width: 18px;
        height: 18px;
        color: #fff;
      }
      /* Partial */
      .step-partial .step-circle {
        background: var(--cg-warn, #f57c00);
        border-color: var(--cg-warn, #f57c00);
      }
      .step-warn {
        font-size: 18px;
        width: 18px;
        height: 18px;
        color: #fff;
      }
      /* Failed */
      .step-failed .step-circle {
        background: var(--cg-error, #dc3545);
        border-color: var(--cg-error, #dc3545);
      }
      .step-fail {
        font-size: 18px;
        width: 18px;
        height: 18px;
        color: #fff;
      }
      /* Cancelled */
      .step-cancelled .step-circle {
        background: var(--cg-warn, #f57c00);
        border-color: var(--cg-warn, #f57c00);
      }
      .step-cancel {
        font-size: 18px;
        width: 18px;
        height: 18px;
        color: #fff;
      }
      .step-cancelled .step-label {
        color: var(--cg-warn, #f57c00);
      }
      .step-time-cancelled {
        color: var(--cg-warn, #f57c00);
        font-style: italic;
      }
      /* Skipped */
      .step-skipped .step-circle {
        background: var(--cg-success, #28a745);
        border-color: var(--cg-success, #28a745);
        opacity: 0.7;
      }
      .step-check-alt {
        font-size: 18px;
        width: 18px;
        height: 18px;
        color: #fff;
      }
      .step-skipped .step-label {
        color: var(--cg-success);
        opacity: 0.8;
      }
      .step-time-uptodate {
        color: var(--cg-success);
        font-style: italic;
        opacity: 0.8;
      }
      /* Labels */
      .step-label {
        margin-top: 8px;
        font-size: 11px;
        font-weight: 500;
        color: var(--cg-gray-500);
        text-align: center;
        max-width: 110px;
        line-height: 1.3;
      }
      .step-running .step-label {
        color: var(--cg-blue);
        font-weight: 600;
      }
      .step-completed .step-label {
        color: var(--cg-success);
      }
      .step-partial .step-label {
        color: var(--cg-warn, #f57c00);
      }
      .step-failed .step-label {
        color: var(--cg-error);
      }
      /* Duration */
      .step-time {
        margin-top: 3px;
        font-size: 10px;
        font-family: 'Cascadia Code', 'Fira Code', monospace;
        color: var(--cg-gray-400);
      }
      .step-time-active {
        color: var(--cg-blue);
        font-weight: 600;
      }
      /* Connector lines */
      .stepper-line {
        flex: 1;
        min-width: 24px;
        height: 3px;
        background: var(--cg-gray-200);
        border-radius: 2px;
        margin-top: calc(var(--circle-size, 42px) / 2);
        position: relative;
        overflow: hidden;
      }
      .line-done {
        background: var(--cg-success, #28a745);
      }
      .line-active {
        background: var(--cg-gray-200);
      }
      .line-active::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        height: 100%;
        width: 40%;
        background: linear-gradient(90deg, var(--cg-blue), rgba(0, 112, 173, 0.2));
        border-radius: 2px;
        animation: line-sweep 1.5s ease-in-out infinite;
      }
      @keyframes line-sweep {
        0% {
          left: -40%;
        }
        100% {
          left: 100%;
        }
      }
      @media (prefers-reduced-motion: reduce) {
        .step-running .step-circle {
          animation-duration: 0.01ms !important;
        }
        .line-active::after {
          animation-duration: 0.01ms !important;
        }
      }
    `,
  ],
})
export class PipelineStepperComponent {
  @Input() steps: PhaseProgress[] = [];
  /** Circle diameter in px (dashboard: 38, run-pipeline: 42) */
  @Input() circleSize = 42;
  /** Min-width per step in px (dashboard: 90, run-pipeline: 100) */
  @Input() stepMinWidth = 100;
  /** Padding for the track row */
  @Input() padding = '8px 0 12px';

  humanize = humanizePhaseId;
  fmt = formatDuration;
}
