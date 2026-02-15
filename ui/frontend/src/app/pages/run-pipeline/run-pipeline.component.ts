import { Component, OnInit, OnDestroy, ViewChild, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import { CdkVirtualScrollViewport, ScrollingModule } from '@angular/cdk/scrolling';
import { Subscription } from 'rxjs';

import { ApiService, PresetInfo, PhaseInfo } from '../../services/api.service';
import {
  PipelineService,
  ExecutionStatus,
  EnvVariable,
  SSEEvent,
} from '../../services/pipeline.service';
import { NotificationService } from '../../services/notification.service';
import { InputsService, InputsSummary } from '../../services/inputs.service';
import { humanizePhaseId, formatDuration as formatDurationUtil } from '../../shared/phase-utils';

@Component({
  selector: 'app-run-pipeline',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatSelectModule,
    MatCheckboxModule,
    MatExpansionModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatInputModule,
    MatFormFieldModule,
    MatTabsModule,
    MatTooltipModule,
    ScrollingModule,
    RouterLink,
  ],
  template: `
    <div class="page-container">
      <div class="page-header">
        <mat-icon class="page-icon">rocket_launch</mat-icon>
        <div>
          <h1 class="page-title">Run Pipeline</h1>
          <p class="page-subtitle">Configure and execute pipeline phases</p>
        </div>
      </div>

      <!-- ================================================================ -->
      <!-- SECTION 1: CONFIGURE (hidden while pipeline is running)          -->
      <!-- ================================================================ -->
      @if (status?.state !== 'running') {
        <mat-card class="config-card">
          <mat-card-header>
            <mat-card-title class="section-card-title">
              <mat-icon>settings</mat-icon>
              Pipeline Configuration
            </mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <mat-tab-group [(selectedIndex)]="runModeIndex">
              <!-- Preset Mode -->
              <mat-tab label="Run Preset">
                <div class="tab-content">
                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>Select Preset</mat-label>
                    <mat-select [(ngModel)]="selectedPreset">
                      @for (preset of presets; track preset.name) {
                        <mat-option [value]="preset.name">
                          <mat-icon style="font-size:18px;vertical-align:middle;margin-right:6px">{{
                            preset.icon || 'playlist_play'
                          }}</mat-icon>
                          {{ preset.display_name || preset.name }}
                        </mat-option>
                      }
                    </mat-select>
                  </mat-form-field>
                  @if (selectedPreset) {
                    <div class="phase-chips">
                      <span class="chips-label">Phases:</span>
                      @for (phase of getPresetPhases(); track phase) {
                        <mat-chip>{{ humanize(phase) }}</mat-chip>
                      }
                    </div>
                  }
                </div>
              </mat-tab>

              <!-- Custom Phases Mode -->
              <mat-tab label="Run Custom Phases">
                <div class="tab-content">
                  <div class="phase-checkboxes">
                    @for (phase of phases; track phase.id) {
                      <mat-checkbox
                        [checked]="selectedPhases.includes(phase.id)"
                        (change)="togglePhase(phase.id, $event.checked)"
                      >
                        <span class="phase-label">
                          <strong>{{ phase.order }}.</strong> {{ phase.name }}
                        </span>
                      </mat-checkbox>
                    }
                  </div>
                </div>
              </mat-tab>
            </mat-tab-group>

            <!-- Advanced: Input files + Env overrides -->
            <mat-expansion-panel class="advanced-panel">
              <mat-expansion-panel-header>
                <mat-panel-title>
                  <mat-icon>tune</mat-icon>
                  Advanced Options
                </mat-panel-title>
                <mat-panel-description>Input files &amp; environment overrides</mat-panel-description>
              </mat-expansion-panel-header>

              <!-- Input Files Summary -->
              <div class="advanced-section">
                <h3 class="advanced-section-title">
                  <mat-icon>upload_file</mat-icon>
                  Input Files
                  @if (inputSummary && inputSummary.total_files > 0) {
                    <span class="advanced-badge">{{ inputSummary.total_files }} ready</span>
                  }
                </h3>
                <div class="input-chips">
                  @if (inputSummary) {
                    @for (catEntry of inputCategoryEntries; track catEntry.key) {
                      <span class="input-chip" [class.has-files]="catEntry.value.file_count > 0">
                        <mat-icon>{{ catEntry.value.icon }}</mat-icon>
                        {{ catEntry.value.label }}
                        <span class="chip-count">{{ catEntry.value.file_count }}</span>
                      </span>
                    }
                  }
                </div>
                <a mat-stroked-button routerLink="/inputs" class="manage-btn">
                  <mat-icon>open_in_new</mat-icon>
                  Manage Files
                </a>
              </div>

              <!-- Environment Overrides -->
              @if (envGroups.length > 0) {
                <div class="advanced-section">
                  <h3 class="advanced-section-title">
                    <mat-icon>settings_ethernet</mat-icon>
                    Environment Overrides
                  </h3>
                  @for (group of envGroups; track group) {
                    <h4 class="env-group-title">{{ group }}</h4>
                    <div class="env-fields">
                      @for (v of getEnvByGroup(group); track v.name) {
                        <mat-form-field appearance="outline" class="env-field">
                          <mat-label>{{ v.name }}</mat-label>
                          <input
                            matInput
                            [(ngModel)]="envValues[v.name]"
                            [placeholder]="v.value || '(not set)'"
                            [matTooltip]="v.description"
                          />
                          @if (v.required) {
                            <mat-icon matSuffix color="warn" matTooltip="Required">star</mat-icon>
                          }
                        </mat-form-field>
                      }
                    </div>
                  }
                </div>
              }
            </mat-expansion-panel>
          </mat-card-content>

          <!-- Run button inside the config card -->
          <mat-card-actions class="config-actions">
            <button
              mat-flat-button
              color="primary"
              class="run-btn"
              [disabled]="!selectedPreset && selectedPhases.length === 0"
              (click)="runPipeline()"
            >
              <mat-icon>play_arrow</mat-icon>
              Run Pipeline
            </button>
          </mat-card-actions>
        </mat-card>
      }

      <!-- ================================================================ -->
      <!-- SECTION 2: EXECUTION (visible while running / after completion)  -->
      <!-- ================================================================ -->
      @if (status && status.state !== 'idle') {

        <!-- Celebration Banner -->
        @if (showCelebration && celebrationType) {
          <div class="celebration-banner" [class]="'celebration-' + celebrationType">
            @if (celebrationType === 'success') {
              <div class="celebration-content">
                <mat-icon class="celebration-icon">check_circle</mat-icon>
                <div class="celebration-text">
                  <span class="celebration-title">Pipeline Completed Successfully</span>
                  <span class="celebration-sub">
                    {{ status.completed_phase_count || 0 }} phases in {{ formatDuration(status.elapsed_seconds || 0) }}
                  </span>
                </div>
                <button mat-icon-button class="celebration-close" (click)="dismissCelebration()">
                  <mat-icon>close</mat-icon>
                </button>
              </div>
            } @else {
              <div class="celebration-content">
                <mat-icon class="celebration-icon">error_outline</mat-icon>
                <div class="celebration-text">
                  <span class="celebration-title">Pipeline Failed</span>
                  <span class="celebration-sub">
                    Check logs for details
                    <a routerLink="/logs" class="logs-link">Open Logs</a>
                  </span>
                </div>
                <button mat-icon-button class="celebration-close" (click)="dismissCelebration()">
                  <mat-icon>close</mat-icon>
                </button>
              </div>
            }
          </div>
        }

        <!-- Status Card with Phase Stepper -->
        <mat-card class="status-card" [class]="'state-' + status.state">
          <mat-card-header>
            <mat-icon mat-card-avatar [class]="'state-icon-' + status.state">
              {{ stateIcon(status.state) }}
            </mat-icon>
            <mat-card-title>{{ status.state | titlecase }}</mat-card-title>
            <mat-card-subtitle>
              @if (status.run_id) {
                Run: {{ status.run_id }}
              }
              @if (status.elapsed_seconds) {
                | Elapsed: {{ formatDuration(status.elapsed_seconds) }}
              }
              @if (status.eta_seconds !== null && status.eta_seconds !== undefined && status.eta_seconds > 0) {
                | ETA: ~{{ formatDuration(status.eta_seconds) }}
              }
            </mat-card-subtitle>
          </mat-card-header>

          <!-- Progress Bar + Cancel -->
          @if (status.state === 'running') {
            <div class="exec-bar">
              <div class="progress-section">
                <mat-progress-bar
                  [mode]="status.progress_percent !== null && status.progress_percent !== undefined ? 'determinate' : 'indeterminate'"
                  [value]="status.progress_percent || 0"
                  class="run-progress">
                </mat-progress-bar>
                <span class="progress-label">
                  {{ status.completed_phase_count || 0 }}/{{ status.total_phase_count || 0 }} phases
                  <span class="progress-pct">{{ status.progress_percent | number:'1.0-0' }}%</span>
                </span>
              </div>
              <button mat-stroked-button color="warn" (click)="cancelPipeline()">
                <mat-icon>stop</mat-icon>
                Cancel
              </button>
            </div>
          }

          <!-- Live Metrics -->
          @if (status.state === 'running' && status.live_metrics) {
            <div class="metrics-bar">
              <div class="metric-item">
                <mat-icon>timer</mat-icon>
                <span class="metric-value">{{ formatDuration(status.elapsed_seconds || 0) }}</span>
                <span class="metric-label">Elapsed</span>
              </div>
              <div class="metric-item">
                <mat-icon>token</mat-icon>
                <span class="metric-value">{{ (status.live_metrics.total_tokens | number) || '0' }}</span>
                <span class="metric-label">Tokens</span>
              </div>
              <div class="metric-item">
                <mat-icon>groups</mat-icon>
                <span class="metric-value">{{ status.live_metrics.crew_completions }}</span>
                <span class="metric-label">Crews</span>
              </div>
              @if (status.eta_seconds !== null && status.eta_seconds !== undefined && status.eta_seconds > 0) {
                <div class="metric-item metric-eta">
                  <mat-icon>schedule</mat-icon>
                  <span class="metric-value">~{{ formatDuration(status.eta_seconds) }}</span>
                  <span class="metric-label">ETA</span>
                </div>
              }
            </div>
          }

          <!-- Phase Stepper -->
          @if (status.phase_progress.length > 0) {
            <mat-card-content>
              <div class="stepper-track">
                @for (pp of status.phase_progress; track pp.phase_id; let i = $index; let last = $last) {
                  <div class="stepper-step" [class]="'step-' + pp.status">
                    <div class="step-circle">
                      @if (pp.status === 'completed') {
                        <mat-icon class="step-check">check</mat-icon>
                      } @else if (pp.status === 'running') {
                        <mat-spinner diameter="22" class="step-spinner"></mat-spinner>
                      } @else if (pp.status === 'failed') {
                        <mat-icon class="step-fail">close</mat-icon>
                      } @else if (pp.status === 'skipped') {
                        <mat-icon class="step-skip">skip_next</mat-icon>
                      } @else {
                        <span class="step-num">{{ i + 1 }}</span>
                      }
                    </div>
                    <div class="step-label">{{ pp.name || humanize(pp.phase_id) }}</div>
                    @if (pp.status === 'completed' && pp.duration_seconds) {
                      <div class="step-time">{{ formatDuration(pp.duration_seconds) }}</div>
                    }
                    @if (pp.status === 'running') {
                      <div class="step-time step-time-active">running</div>
                    }
                    @if (pp.status === 'skipped') {
                      <div class="step-time step-time-skipped">skipped</div>
                    }
                    @if (pp.status === 'running' && pp.sub_phases?.length) {
                      <div class="sub-phase-chips">
                        @for (sp of pp.sub_phases; track sp.name) {
                          <span class="sub-chip" [class]="'sub-' + sp.status">
                            <mat-icon class="sub-icon">
                              {{ sp.status === 'completed' ? 'check' : 'sync' }}
                            </mat-icon>
                            {{ sp.name }}
                            @if (sp.total_tokens) {
                              <span class="sub-tokens">{{ sp.total_tokens | number }}</span>
                            }
                          </span>
                        }
                      </div>
                    }
                  </div>
                  @if (!last) {
                    <div class="stepper-line" [class.line-done]="pp.status === 'completed'"
                         [class.line-active]="pp.status === 'running'">
                    </div>
                  }
                }
              </div>
            </mat-card-content>
          }

          <!-- "Run again" when completed/failed -->
          @if (status.state === 'completed' || status.state === 'failed' || status.state === 'cancelled') {
            <mat-card-actions class="exec-actions">
              <button mat-flat-button color="primary" (click)="resetToConfig()">
                <mat-icon>replay</mat-icon>
                Configure New Run
              </button>
              <a mat-stroked-button routerLink="/history">
                <mat-icon>history</mat-icon>
                View Full History
              </a>
            </mat-card-actions>
          }
        </mat-card>
      }

      <!-- ================================================================ -->
      <!-- SECTION 3: LIVE LOG OUTPUT (always visible when there are logs)  -->
      <!-- ================================================================ -->
      @if (logLines.length > 0) {
        <mat-card class="log-card">
          <mat-card-header>
            <mat-card-title class="log-title">
              <mat-icon>receipt_long</mat-icon>
              Live Output
              <span class="log-count">{{ filteredLogLines.length }} lines</span>
            </mat-card-title>
            <span class="spacer"></span>
            <mat-form-field appearance="outline" class="log-search-field">
              <mat-icon matPrefix>search</mat-icon>
              <input matInput placeholder="Filter logs..." [(ngModel)]="logSearch"
                     (ngModelChange)="filterLogs()" />
            </mat-form-field>
            <button mat-icon-button (click)="autoScroll = !autoScroll"
                    [matTooltip]="autoScroll ? 'Auto-scroll ON' : 'Auto-scroll OFF'"
                    [class.active-toggle]="autoScroll">
              <mat-icon>{{ autoScroll ? 'vertical_align_bottom' : 'pause' }}</mat-icon>
            </button>
            <button mat-icon-button (click)="scrollToTop()" matTooltip="Scroll to top">
              <mat-icon>vertical_align_top</mat-icon>
            </button>
          </mat-card-header>
          <mat-card-content>
            <cdk-virtual-scroll-viewport itemSize="22" class="log-viewport" #logViewport>
              <div *cdkVirtualFor="let line of filteredLogLines; let i = index"
                   class="log-line" [class]="getLogLevel(line)">
                <span class="log-num">{{ i + 1 }}</span>{{ line }}
              </div>
            </cdk-virtual-scroll-viewport>
          </mat-card-content>
        </mat-card>
      }
    </div>
  `,
  styles: [
    `
      /* Config Card */
      .config-card { margin-bottom: 16px; }
      .tab-content { padding: 16px 0; }
      .full-width { width: 100%; }
      .phase-chips {
        display: flex; align-items: center; gap: 8px;
        flex-wrap: wrap; margin-top: 8px;
      }
      .chips-label { font-size: 13px; font-weight: 500; color: var(--cg-gray-500); }
      .phase-checkboxes { display: flex; flex-direction: column; gap: 8px; }
      .phase-label { display: inline-flex; align-items: center; gap: 4px; }

      /* Advanced panel inside config card */
      .advanced-panel {
        margin-top: 16px;
        box-shadow: none !important;
        border: 1px solid var(--cg-gray-100);
      }
      .advanced-panel ::ng-deep .mat-expansion-panel-body { padding: 0 16px 16px; }
      .advanced-section { margin-top: 16px; }
      .advanced-section-title {
        display: flex; align-items: center; gap: 8px;
        font-size: 14px; font-weight: 600; color: var(--cg-gray-700);
        margin: 0 0 8px;
      }
      .advanced-section-title .mat-icon {
        font-size: 18px; width: 18px; height: 18px; color: var(--cg-blue);
      }
      .advanced-badge {
        font-size: 11px; font-weight: 600;
        background: rgba(40, 167, 69, 0.1); color: var(--cg-success);
        padding: 2px 8px; border-radius: 8px;
      }

      /* Input chips */
      .input-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
      .input-chip {
        display: inline-flex; align-items: center; gap: 4px;
        padding: 4px 10px; border-radius: 8px;
        background: var(--cg-gray-100); font-size: 12px; color: var(--cg-gray-500);
      }
      .input-chip .mat-icon { font-size: 16px; width: 16px; height: 16px; }
      .input-chip.has-files {
        background: rgba(18, 171, 219, 0.1); color: var(--cg-blue); font-weight: 500;
      }
      .chip-count {
        min-width: 18px; height: 18px;
        display: inline-flex; align-items: center; justify-content: center;
        border-radius: 9px; background: rgba(0, 0, 0, 0.06);
        font-size: 11px; font-weight: 600;
      }
      .input-chip.has-files .chip-count { background: var(--cg-vibrant); color: #fff; }
      .manage-btn { font-size: 13px; }
      .manage-btn .mat-icon { font-size: 18px; width: 18px; height: 18px; margin-right: 4px; }

      /* Env overrides */
      .env-group-title {
        font-size: 12px; font-weight: 600; color: var(--cg-blue);
        margin: 12px 0 6px; text-transform: uppercase; letter-spacing: 0.5px;
      }
      .env-fields {
        display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 8px;
      }
      .env-field { width: 100%; }

      /* Config actions */
      .config-actions {
        padding: 8px 16px 16px !important;
      }
      .run-btn {
        font-size: 15px;
        padding: 0 32px;
        height: 44px;
      }

      /* Execution section */
      .exec-bar {
        display: flex; align-items: center; gap: 16px;
        padding: 0 16px 12px;
      }
      .progress-section {
        flex: 1; display: flex; flex-direction: column; gap: 4px;
      }
      .run-progress { width: 100%; }
      .run-progress ::ng-deep .mdc-linear-progress__bar-inner {
        border-color: var(--cg-vibrant) !important;
      }
      .progress-label {
        font-size: 12px; color: var(--cg-gray-500);
        display: flex; align-items: center; gap: 8px;
      }
      .progress-pct {
        font-family: 'Cascadia Code', 'Fira Code', monospace;
        font-weight: 600; color: var(--cg-blue);
      }

      /* Live Metrics */
      .metrics-bar {
        display: flex; gap: 16px; flex-wrap: wrap;
        padding: 8px 16px 12px;
        border-top: 1px solid var(--cg-gray-100);
      }
      .metric-item {
        display: flex; align-items: center; gap: 6px;
        font-size: 13px; color: var(--cg-gray-600);
      }
      .metric-item .mat-icon { font-size: 18px; width: 18px; height: 18px; color: var(--cg-blue); }
      .metric-value {
        font-family: 'Cascadia Code', 'Fira Code', monospace;
        font-weight: 600; color: var(--cg-gray-900);
      }
      .metric-label { font-size: 11px; color: var(--cg-gray-400); }
      .metric-eta .mat-icon { color: var(--cg-vibrant); }
      .metric-eta .metric-value { color: var(--cg-vibrant); }

      /* Celebration Banner */
      .celebration-banner {
        border-radius: 12px; padding: 16px 20px; margin-bottom: 16px;
        position: relative; overflow: hidden;
        animation: slide-in 0.4s ease-out;
      }
      .celebration-success {
        background: linear-gradient(135deg, var(--cg-success, #28a745) 0%, #20c997 100%);
        color: #fff;
      }
      .celebration-failure {
        background: linear-gradient(135deg, var(--cg-error, #dc3545) 0%, #e85d75 100%);
        color: #fff;
      }
      .celebration-content {
        display: flex; align-items: center; gap: 12px; position: relative; z-index: 1;
      }
      .celebration-icon { font-size: 32px; width: 32px; height: 32px; }
      .celebration-text { display: flex; flex-direction: column; flex: 1; }
      .celebration-title { font-size: 16px; font-weight: 600; }
      .celebration-sub { font-size: 13px; opacity: 0.9; }
      .celebration-close { color: rgba(255, 255, 255, 0.7) !important; }
      .logs-link { color: #fff; text-decoration: underline; margin-left: 6px; }
      @keyframes slide-in {
        from { transform: translateY(-20px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
      }

      /* Status Card */
      .status-card { margin-bottom: 16px; }
      .state-completed { border-left: 4px solid var(--cg-success); }
      .state-failed { border-left: 4px solid var(--cg-error); }
      .state-running { border-left: 4px solid var(--cg-blue); }
      .state-cancelled { border-left: 4px solid var(--cg-warn); }
      .state-icon-completed { color: var(--cg-success); }
      .state-icon-failed { color: var(--cg-error); }
      .state-icon-running { color: var(--cg-blue); }
      .state-icon-cancelled { color: var(--cg-warn); }

      .exec-actions {
        padding: 8px 16px 16px !important;
        display: flex; gap: 12px;
      }

      /* Enhanced Stepper */
      .stepper-track {
        display: flex; align-items: flex-start;
        overflow-x: auto; padding: 8px 0 12px;
      }
      .stepper-step {
        display: flex; flex-direction: column; align-items: center;
        flex-shrink: 0; min-width: 100px;
      }
      .step-circle {
        width: 42px; height: 42px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        background: var(--cg-gray-50, #f8f9fa);
        border: 2.5px solid var(--cg-gray-200);
        position: relative; z-index: 1; transition: all 0.3s ease;
      }
      .step-num {
        font-size: 13px; font-weight: 600; color: var(--cg-gray-400);
      }
      .step-running .step-circle {
        background: rgba(0, 112, 173, 0.08); border-color: var(--cg-blue);
        box-shadow: 0 0 0 5px rgba(0, 112, 173, 0.1);
        animation: pulse-ring 2s ease-in-out infinite;
      }
      @keyframes pulse-ring {
        0%, 100% { box-shadow: 0 0 0 5px rgba(0, 112, 173, 0.1); }
        50% { box-shadow: 0 0 0 10px rgba(0, 112, 173, 0.04); }
      }
      .step-spinner ::ng-deep circle { stroke: var(--cg-blue) !important; }
      .step-completed .step-circle {
        background: var(--cg-success, #28a745); border-color: var(--cg-success, #28a745);
      }
      .step-check { font-size: 18px; width: 18px; height: 18px; color: #fff; }
      .step-failed .step-circle {
        background: var(--cg-error, #dc3545); border-color: var(--cg-error, #dc3545);
      }
      .step-fail { font-size: 18px; width: 18px; height: 18px; color: #fff; }
      /* Skipped */
      .step-skipped .step-circle {
        background: var(--cg-gray-100); border-color: var(--cg-gray-200);
        opacity: 0.7;
      }
      .step-skip { font-size: 18px; width: 18px; height: 18px; color: var(--cg-gray-400); }
      .step-skipped .step-label { color: var(--cg-gray-400); text-decoration: line-through; }
      .step-time-skipped { color: var(--cg-gray-400); font-style: italic; }
      .step-label {
        margin-top: 8px; font-size: 11px; font-weight: 500;
        color: var(--cg-gray-500); text-align: center;
        max-width: 110px; line-height: 1.3;
      }
      .step-running .step-label { color: var(--cg-blue); font-weight: 600; }
      .step-completed .step-label { color: var(--cg-success); }
      .step-failed .step-label { color: var(--cg-error); }
      .step-time {
        margin-top: 3px; font-size: 10px;
        font-family: 'Cascadia Code', 'Fira Code', monospace;
        color: var(--cg-gray-400);
      }
      .step-time-active { color: var(--cg-blue); font-weight: 600; }
      .stepper-line {
        flex: 1; min-width: 24px; height: 3px;
        background: var(--cg-gray-200); border-radius: 2px;
        margin-top: 21px; position: relative; overflow: hidden;
      }
      .line-done { background: var(--cg-success, #28a745); }
      .line-active { background: var(--cg-gray-200); }
      .line-active::after {
        content: ''; position: absolute; top: 0; left: 0;
        height: 100%; width: 40%;
        background: linear-gradient(90deg, var(--cg-blue), rgba(0, 112, 173, 0.2));
        border-radius: 2px; animation: line-sweep 1.5s ease-in-out infinite;
      }
      @keyframes line-sweep {
        0% { left: -40%; }
        100% { left: 100%; }
      }

      /* Sub-phase chips */
      .sub-phase-chips {
        display: flex; flex-wrap: wrap; gap: 4px;
        margin-top: 6px; max-width: 160px; justify-content: center;
      }
      .sub-chip {
        display: inline-flex; align-items: center; gap: 3px;
        padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 500;
        background: rgba(0, 112, 173, 0.08); color: var(--cg-blue);
      }
      .sub-completed { background: rgba(40, 167, 69, 0.08); color: var(--cg-success); }
      .sub-failed { background: rgba(220, 53, 69, 0.08); color: var(--cg-error); }
      .sub-icon { font-size: 12px; width: 12px; height: 12px; }
      .sub-tokens { font-family: monospace; font-size: 9px; opacity: 0.7; }

      /* Log Viewer */
      .log-card { margin-bottom: 16px; }
      .log-card mat-card-header { display: flex; align-items: center; }
      .log-title { display: flex !important; align-items: center; gap: 8px; }
      .log-count { font-size: 12px; color: var(--cg-gray-500); font-weight: 400; }
      .spacer { flex: 1; }
      .log-search-field { width: 180px; margin: 0 8px; }
      .log-search-field ::ng-deep .mat-mdc-form-field-subscript-wrapper { display: none; }
      .log-search-field ::ng-deep .mdc-text-field { height: 36px !important; }
      .log-search-field ::ng-deep .mat-mdc-form-field-infix { padding: 4px 0 !important; min-height: unset; }
      .log-search-field ::ng-deep input { font-size: 12px; }
      .log-search-field ::ng-deep .mat-icon { font-size: 16px; width: 16px; height: 16px; color: var(--cg-gray-400); margin-right: 4px; }
      .active-toggle { color: var(--cg-vibrant) !important; }
      .log-viewport {
        height: 500px;
        background: var(--cg-dark);
        color: #d4d4d4;
        font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
        font-size: 12px;
        border-radius: 8px;
      }
      .log-line {
        height: 22px; line-height: 22px;
        padding: 0 12px; white-space: pre; overflow: hidden; text-overflow: ellipsis;
      }
      .log-num {
        display: inline-block; width: 36px; text-align: right;
        margin-right: 12px; color: rgba(255, 255, 255, 0.2); user-select: none;
      }
      .log-error { color: #f48771; }
      .log-warning { color: #cca700; }
      .log-info { color: #89d185; }
    `,
  ],
})
export class RunPipelineComponent implements OnInit, OnDestroy {
  @ViewChild('logViewport') logViewportRef?: CdkVirtualScrollViewport;

  // Config
  presets: PresetInfo[] = [];
  phases: PhaseInfo[] = [];
  selectedPreset = '';
  selectedPhases: string[] = [];
  runModeIndex = 0;

  // Environment
  envVariables: EnvVariable[] = [];
  envGroups: string[] = [];
  envValues: Record<string, string> = {};

  // Input files
  inputSummary: InputsSummary | null = null;
  inputCategoryEntries: { key: string; value: { label: string; icon: string; file_count: number } }[] = [];

  // Execution
  status: ExecutionStatus | null = null;
  logLines: string[] = [];
  filteredLogLines: string[] = [];
  logSearch = '';
  autoScroll = true;

  // Celebration
  showCelebration = false;
  celebrationType: 'success' | 'failure' | null = null;
  private celebrationTimer?: ReturnType<typeof setTimeout>;

  private sseSub?: Subscription;

  constructor(
    private api: ApiService,
    private pipeline: PipelineService,
    private inputsService: InputsService,
    private notifSvc: NotificationService,
    private route: ActivatedRoute,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.api.getPresets().subscribe((p) => {
      this.presets = p;
      this.cdr.markForCheck();
    });
    this.api.getPhases().subscribe((p) => {
      this.phases = p;
      this.cdr.markForCheck();
    });
    this.pipeline.getStatus().subscribe((s) => {
      this.status = s;
      if (s.state === 'running') {
        this.connectSSE();
      }
      this.cdr.markForCheck();
    });

    this.inputsService.getSummary().subscribe((s) => {
      this.inputSummary = s;
      this.inputCategoryEntries = Object.entries(s.categories).map(([key, value]) => ({ key, value }));
      this.cdr.markForCheck();
    });

    this.pipeline.getEnv().subscribe((vars) => {
      this.envVariables = vars;
      this.envGroups = [...new Set(vars.map((v) => v.group))];
      vars.forEach((v) => (this.envValues[v.name] = v.value));
      this.cdr.markForCheck();
    });

    this.route.queryParams.subscribe((params) => {
      if (params['preset']) {
        this.selectedPreset = params['preset'];
        this.runModeIndex = 0;
      }
      if (params['phase']) {
        this.selectedPhases = [params['phase']];
        this.runModeIndex = 1;
      }
      this.cdr.markForCheck();
    });
  }

  ngOnDestroy(): void {
    this.sseSub?.unsubscribe();
    if (this.celebrationTimer) clearTimeout(this.celebrationTimer);
  }

  getPresetPhases(): string[] {
    const preset = this.presets.find((p) => p.name === this.selectedPreset);
    return preset?.phases || [];
  }

  getEnvByGroup(group: string): EnvVariable[] {
    return this.envVariables.filter((v) => v.group === group);
  }

  togglePhase(phaseId: string, checked: boolean | null): void {
    if (checked) {
      if (!this.selectedPhases.includes(phaseId)) {
        this.selectedPhases = [...this.selectedPhases, phaseId];
      }
    } else {
      this.selectedPhases = this.selectedPhases.filter((p) => p !== phaseId);
    }
  }

  /** Reset execution state so the config form shows again */
  resetToConfig(): void {
    this.status = { state: 'idle', phases: [], phase_progress: [] };
    this.logLines = [];
    this.filteredLogLines = [];
    this.showCelebration = false;
    this.celebrationType = null;
    this.cdr.markForCheck();
  }

  runPipeline(): void {
    const overrides: Record<string, string> = {};
    for (const v of this.envVariables) {
      if (this.envValues[v.name] && this.envValues[v.name] !== v.value) {
        overrides[v.name] = this.envValues[v.name];
      }
    }

    const request: { preset?: string; phases?: string[]; env_overrides?: Record<string, string> } = {};
    if (this.runModeIndex === 0 && this.selectedPreset) {
      request.preset = this.selectedPreset;
    } else if (this.selectedPhases.length > 0) {
      request.phases = this.selectedPhases;
    }
    if (Object.keys(overrides).length > 0) {
      request.env_overrides = overrides;
    }

    this.logLines = [];
    this.filteredLogLines = [];
    this.showCelebration = false;
    this.celebrationType = null;
    this.pipeline.startPipeline(request).subscribe({
      next: () => {
        this.notifSvc.refreshNow();
        this.connectSSE();
      },
      error: (err) => {
        const msg = err?.error?.detail || 'Failed to start pipeline';
        this.logLines = [`ERROR: ${msg}`];
        this.filteredLogLines = this.logLines;
        this.cdr.markForCheck();
      },
    });
  }

  cancelPipeline(): void {
    this.pipeline.cancelPipeline().subscribe({
      next: () => {
        this.notifSvc.refreshNow();
        this.refreshStatus();
      },
    });
  }

  filterLogs(): void {
    if (!this.logSearch) {
      this.filteredLogLines = this.logLines;
    } else {
      const q = this.logSearch.toLowerCase();
      this.filteredLogLines = this.logLines.filter((l) => l.toLowerCase().includes(q));
    }
  }

  dismissCelebration(): void {
    this.showCelebration = false;
    this.celebrationType = null;
    if (this.celebrationTimer) clearTimeout(this.celebrationTimer);
  }

  private triggerCelebration(type: 'success' | 'failure'): void {
    this.celebrationType = type;
    this.showCelebration = true;
    this.cdr.markForCheck();

    this.celebrationTimer = setTimeout(() => {
      this.showCelebration = false;
      this.celebrationType = null;
      this.cdr.markForCheck();
    }, 8000);
  }

  private connectSSE(): void {
    this.sseSub?.unsubscribe();

    this.sseSub = this.pipeline.connectSSE().subscribe({
      next: (event: SSEEvent) => {
        if (event.type === 'log_line') {
          this.logLines = [...this.logLines, event.data as string];
          this.filterLogs();
          if (this.autoScroll) this.scrollToBottom();
        }
        if (event.type === 'status') {
          this.status = event.data as ExecutionStatus;
        }
        if (event.type === 'pipeline_complete') {
          this.status = event.data as ExecutionStatus;
          const finalState = this.status?.state || 'completed';
          if (finalState !== 'cancelled') {
            this.triggerCelebration(finalState === 'failed' ? 'failure' : 'success');
          }
        }
        this.cdr.markForCheck();
      },
      complete: () => {
        this.refreshStatus();
      },
    });
  }

  private refreshStatus(): void {
    this.pipeline.getStatus().subscribe((s) => {
      this.status = s;
      this.cdr.markForCheck();
    });
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      const viewport = this.logViewportRef;
      if (viewport) {
        viewport.scrollTo({ bottom: 0 });
      }
    }, 50);
  }

  scrollToTop(): void {
    const viewport = this.logViewportRef;
    if (viewport) {
      viewport.scrollTo({ top: 0 });
    }
  }

  stateIcon(state: string): string {
    switch (state) {
      case 'completed': return 'check_circle';
      case 'failed': return 'error';
      case 'running': return 'sync';
      case 'cancelled': return 'cancel';
      default: return 'radio_button_unchecked';
    }
  }

  humanize(phaseId: string): string {
    return humanizePhaseId(phaseId);
  }

  formatDuration(seconds: number): string {
    return formatDurationUtil(seconds);
  }

  getLogLevel(line: string): string {
    if (line.includes('ERROR') || line.includes('Error')) return 'log-error';
    if (line.includes('WARNING') || line.includes('Warn')) return 'log-warning';
    if (line.includes('INFO') || line.includes('\u2713')) return 'log-info';
    return '';
  }
}
