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
import { PipelineService, ExecutionStatus, EnvVariable, SSEEvent } from '../../services/pipeline.service';
import { NotificationService } from '../../services/notification.service';
import { InputsService, InputsSummary } from '../../services/inputs.service';
import { PipelineStepperComponent } from '../../shared/pipeline-stepper.component';
import { humanizePhaseId, formatDuration as formatDurationUtil } from '../../shared/phase-utils';
import { statusIcon } from '../../shared/status';

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
    PipelineStepperComponent,
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
            <div class="celebration-content">
              <mat-icon class="celebration-icon">{{ celebrationIcon() }}</mat-icon>
              <div class="celebration-text">
                <span class="celebration-title">{{ celebrationTitle() }}</span>
                <span class="celebration-sub">{{ celebrationSubtitle() }}</span>
              </div>
              <button
                mat-icon-button
                class="celebration-close"
                (click)="dismissCelebration()"
                matTooltip="Dismiss"
                aria-label="Dismiss"
              >
                <mat-icon>close</mat-icon>
              </button>
            </div>
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
                {{ status.run_id ? ' | ' : '' }}Elapsed: {{ formatDuration(status.elapsed_seconds) }}
              }
              @if (status.eta_seconds !== null && status.eta_seconds !== undefined && status.eta_seconds > 0) {
                {{ status.run_id || status.elapsed_seconds ? ' | ' : '' }}ETA: ~{{ formatDuration(status.eta_seconds) }}
              }
            </mat-card-subtitle>
          </mat-card-header>

          <!-- Progress Bar + Cancel -->
          @if (status.state === 'running') {
            <div class="exec-bar">
              <div class="progress-section">
                <mat-progress-bar
                  [mode]="
                    status.progress_percent !== null &&
                    status.progress_percent !== undefined &&
                    status.progress_percent > 0
                      ? 'determinate'
                      : 'indeterminate'
                  "
                  [value]="status.progress_percent || 0"
                  class="run-progress"
                >
                </mat-progress-bar>
                <span class="progress-label">
                  {{ (status.completed_phase_count || 0) + (status.skipped_phase_count || 0) }}/{{
                    status.total_phase_count || 0
                  }}
                  phases
                  <span class="progress-pct">{{ status.progress_percent | number: '1.0-0' }}%</span>
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
              <app-pipeline-stepper [steps]="status.phase_progress"></app-pipeline-stepper>
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
              <input matInput placeholder="Filter logs..." [(ngModel)]="logSearch" (ngModelChange)="filterLogs()" />
            </mat-form-field>
            <button
              mat-icon-button
              (click)="autoScroll = !autoScroll"
              [matTooltip]="autoScroll ? 'Auto-scroll ON' : 'Auto-scroll OFF'"
              [attr.aria-label]="autoScroll ? 'Auto-scroll ON' : 'Auto-scroll OFF'"
              [class.active-toggle]="autoScroll"
            >
              <mat-icon>{{ autoScroll ? 'vertical_align_bottom' : 'pause' }}</mat-icon>
            </button>
            <button mat-icon-button (click)="scrollToTop()" matTooltip="Scroll to top" aria-label="Scroll to top">
              <mat-icon>vertical_align_top</mat-icon>
            </button>
          </mat-card-header>
          <mat-card-content>
            <cdk-virtual-scroll-viewport itemSize="22" class="log-viewport" #logViewport>
              <div
                *cdkVirtualFor="let line of filteredLogLines; let i = index"
                class="log-line"
                [class]="getLogLevel(line)"
              >
                <span class="log-num">{{ i + 1 }}</span
                >{{ line }}
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
      .config-card {
        margin-bottom: 16px;
      }
      .tab-content {
        padding: 16px 0;
      }
      .full-width {
        width: 100%;
      }
      .phase-chips {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 8px;
      }
      .chips-label {
        font-size: 13px;
        font-weight: 500;
        color: var(--cg-gray-500);
      }
      .phase-checkboxes {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .phase-label {
        display: inline-flex;
        align-items: center;
        gap: 4px;
      }

      /* Advanced panel inside config card */
      .advanced-panel {
        margin-top: 16px;
        box-shadow: none !important;
        border: 1px solid var(--cg-gray-100);
      }
      .advanced-panel ::ng-deep .mat-expansion-panel-body {
        padding: 0 16px 16px;
      }
      .advanced-section {
        margin-top: 16px;
      }
      .advanced-section-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
        font-weight: 600;
        color: var(--cg-gray-700);
        margin: 0 0 8px;
      }
      .advanced-section-title .mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
        color: var(--cg-blue);
      }
      .advanced-badge {
        font-size: 11px;
        font-weight: 600;
        background: rgba(40, 167, 69, 0.1);
        color: var(--cg-success);
        padding: 2px 8px;
        border-radius: 8px;
      }

      /* Input chips */
      .input-chips {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 12px;
      }
      .input-chip {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 10px;
        border-radius: 8px;
        background: var(--cg-gray-100);
        font-size: 12px;
        color: var(--cg-gray-500);
      }
      .input-chip .mat-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
      }
      .input-chip.has-files {
        background: rgba(18, 171, 219, 0.1);
        color: var(--cg-blue);
        font-weight: 500;
      }
      .chip-count {
        min-width: 18px;
        height: 18px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 9px;
        background: rgba(0, 0, 0, 0.06);
        font-size: 11px;
        font-weight: 600;
      }
      .input-chip.has-files .chip-count {
        background: var(--cg-vibrant);
        color: #fff;
      }
      .manage-btn {
        font-size: 13px;
      }
      .manage-btn .mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
        margin-right: 4px;
      }

      /* Env overrides */
      .env-group-title {
        font-size: 12px;
        font-weight: 600;
        color: var(--cg-blue);
        margin: 12px 0 6px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }
      .env-fields {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
        gap: 8px;
      }
      .env-field {
        width: 100%;
      }

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
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 0 16px 12px;
      }
      .progress-section {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      .run-progress {
        width: 100%;
      }
      .run-progress ::ng-deep .mdc-linear-progress__bar-inner {
        border-color: var(--cg-vibrant) !important;
      }
      .progress-label {
        font-size: 12px;
        color: var(--cg-gray-500);
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .progress-pct {
        font-family: 'Cascadia Code', 'Fira Code', monospace;
        font-weight: 600;
        color: var(--cg-blue);
      }

      /* Live Metrics */
      .metrics-bar {
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
        padding: 8px 16px 12px;
        border-top: 1px solid var(--cg-gray-100);
      }
      .metric-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        color: var(--cg-gray-600);
      }
      .metric-item .mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
        color: var(--cg-blue);
      }
      .metric-value {
        font-family: 'Cascadia Code', 'Fira Code', monospace;
        font-weight: 600;
        color: var(--cg-gray-900);
      }
      .metric-label {
        font-size: 11px;
        color: var(--cg-gray-400);
      }
      .metric-eta .mat-icon {
        color: var(--cg-vibrant);
      }
      .metric-eta .metric-value {
        color: var(--cg-vibrant);
      }

      /* Celebration Banner */
      .celebration-banner {
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 16px;
        position: relative;
        overflow: hidden;
        animation: slide-in 0.4s ease-out;
      }
      .celebration-success {
        background: linear-gradient(135deg, var(--cg-success, #28a745) 0%, #20c997 100%);
        color: #fff;
      }
      .celebration-partial {
        background: linear-gradient(135deg, var(--cg-success, #28a745) 0%, var(--cg-warn, #f57c00) 100%);
        color: #fff;
      }
      .celebration-all_skipped {
        background: linear-gradient(135deg, #20c997 0%, var(--cg-success, #28a745) 100%);
        color: #fff;
      }
      .celebration-failure {
        background: linear-gradient(135deg, var(--cg-error, #dc3545) 0%, #e85d75 100%);
        color: #fff;
      }
      .celebration-content {
        display: flex;
        align-items: center;
        gap: 12px;
        position: relative;
        z-index: 1;
      }
      .celebration-icon {
        font-size: 32px;
        width: 32px;
        height: 32px;
      }
      .celebration-text {
        display: flex;
        flex-direction: column;
        flex: 1;
      }
      .celebration-title {
        font-size: 16px;
        font-weight: 600;
      }
      .celebration-sub {
        font-size: 13px;
        opacity: 0.9;
      }
      .celebration-close {
        color: rgba(255, 255, 255, 0.7) !important;
      }
      .logs-link {
        color: #fff;
        text-decoration: underline;
        margin-left: 6px;
      }
      @keyframes slide-in {
        from {
          transform: translateY(-20px);
          opacity: 0;
        }
        to {
          transform: translateY(0);
          opacity: 1;
        }
      }

      /* Status Card */
      .status-card {
        margin-bottom: 16px;
      }
      .state-completed {
        border-left: 4px solid var(--cg-success);
      }
      .state-failed {
        border-left: 4px solid var(--cg-error);
      }
      .state-running {
        border-left: 4px solid var(--cg-blue);
      }
      .state-cancelled {
        border-left: 4px solid var(--cg-warn);
      }
      .state-icon-completed {
        color: var(--cg-success);
      }
      .state-icon-failed {
        color: var(--cg-error);
      }
      .state-icon-running {
        color: var(--cg-blue);
      }
      .state-icon-cancelled {
        color: var(--cg-warn);
      }

      .exec-actions {
        padding: 8px 16px 16px !important;
        display: flex;
        gap: 12px;
      }

      /* Log Viewer */
      .log-card {
        margin-bottom: 16px;
      }
      .log-card mat-card-header {
        display: flex;
        align-items: center;
      }
      .log-title {
        display: flex !important;
        align-items: center;
        gap: 8px;
      }
      .log-count {
        font-size: 12px;
        color: var(--cg-gray-500);
        font-weight: 400;
      }
      .spacer {
        flex: 1;
      }
      .log-search-field {
        width: 180px;
        margin: 0 8px;
      }
      .log-search-field ::ng-deep .mat-mdc-form-field-subscript-wrapper {
        display: none;
      }
      .log-search-field ::ng-deep .mdc-text-field {
        height: 36px !important;
      }
      .log-search-field ::ng-deep .mat-mdc-form-field-infix {
        padding: 4px 0 !important;
        min-height: unset;
      }
      .log-search-field ::ng-deep input {
        font-size: 12px;
      }
      .log-search-field ::ng-deep .mat-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
        color: var(--cg-gray-400);
        margin-right: 4px;
      }
      .active-toggle {
        color: var(--cg-vibrant) !important;
      }
      .log-viewport {
        height: 500px;
        background: var(--cg-dark);
        color: #d4d4d4;
        font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
        font-size: 12px;
        border-radius: 8px;
      }
      .log-line {
        height: 22px;
        line-height: 22px;
        padding: 0 12px;
        white-space: pre;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .log-num {
        display: inline-block;
        width: 36px;
        text-align: right;
        margin-right: 12px;
        color: rgba(255, 255, 255, 0.2);
        user-select: none;
      }
      .log-error {
        color: #f48771;
      }
      .log-warning {
        color: #cca700;
      }
      .log-info {
        color: #89d185;
      }
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
  celebrationType: 'success' | 'partial' | 'all_skipped' | 'failure' | null = null;
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
    this.api.getPresets().subscribe({
      next: (p) => {
        this.presets = p;
        this.cdr.markForCheck();
      },
      error: () => {},
    });
    this.api.getPhases().subscribe({
      next: (p) => {
        this.phases = p;
        this.cdr.markForCheck();
      },
      error: () => {},
    });
    this.pipeline.getStatus().subscribe({
      next: (s) => {
        this.status = s;
        if (s.state === 'running') {
          this.connectSSE();
        }
        this.cdr.markForCheck();
      },
      error: () => {},
    });

    this.inputsService.getSummary().subscribe({
      next: (s) => {
        this.inputSummary = s;
        this.inputCategoryEntries = Object.entries(s.categories).map(([key, value]) => ({ key, value }));
        this.cdr.markForCheck();
      },
      error: () => {},
    });

    this.pipeline.getEnv().subscribe({
      next: (vars) => {
        this.envVariables = vars;
        this.envGroups = [...new Set(vars.map((v) => v.group))];
        vars.forEach((v) => (this.envValues[v.name] = v.value));
        this.cdr.markForCheck();
      },
      error: () => {},
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
    if (this.celebrationTimer) clearTimeout(this.celebrationTimer);
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
        // Immediately disconnect SSE so stale status events can't overwrite
        this.sseSub?.unsubscribe();
        this.sseSub = undefined;
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

  celebrationIcon(): string {
    switch (this.celebrationType) {
      case 'success':
        return 'check_circle';
      case 'partial':
        return 'check_circle';
      case 'all_skipped':
        return 'check_circle';
      case 'failure':
        return 'error_outline';
      default:
        return 'info';
    }
  }

  celebrationTitle(): string {
    switch (this.celebrationType) {
      case 'success':
        return 'Run Completed Successfully';
      case 'partial':
        return 'Run Completed (Partial)';
      case 'all_skipped':
        return 'Run Completed - Already Current';
      case 'failure':
        return 'Run Failed';
      default:
        return '';
    }
  }

  celebrationSubtitle(): string {
    if (!this.status) return '';
    const elapsed = this.formatDuration(this.status.elapsed_seconds || 0);
    const completed = this.status.completed_phase_count || 0;
    const skipped = this.status.skipped_phase_count || 0;
    const total = this.status.total_phase_count || 0;

    switch (this.celebrationType) {
      case 'success':
        return `${completed} phase${completed !== 1 ? 's' : ''} in ${elapsed}`;
      case 'partial':
        return `${completed} completed, ${skipped} already current in ${elapsed}`;
      case 'all_skipped':
        if (total === 1) {
          const name = this.status.phase_progress?.[0]?.name || 'Phase';
          return `${name} already up to date - no changes detected`;
        }
        return `All ${total} phases already up to date - no changes detected`;
      case 'failure':
        return 'Check logs for details';
      default:
        return '';
    }
  }

  private triggerCelebration(type: 'success' | 'partial' | 'all_skipped' | 'failure'): void {
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
    // Resume from last received log line to avoid duplicate entries on reconnect
    const resumeFrom = this.logLines.length;

    this.sseSub = this.pipeline.connectSSE(resumeFrom).subscribe({
      next: (event: SSEEvent) => {
        if (event.type === 'log_line') {
          this.logLines = [...this.logLines, event.data as string];
          this.filterLogs();
          if (this.autoScroll) this.scrollToBottom();
        }
        if (event.type === 'status') {
          const incoming = event.data as ExecutionStatus;
          // For running phases, compute elapsed from started_at so the
          // duration doesn't reset to 0 on every SSE update.
          if (incoming.phase_progress) {
            for (const pp of incoming.phase_progress) {
              if (pp.status === 'running' && pp.started_at && !pp.duration_seconds) {
                const started = new Date(pp.started_at).getTime();
                pp.duration_seconds = Math.round((Date.now() - started) / 1000);
              }
            }
          }
          this.status = incoming;
        }
        if (event.type === 'pipeline_complete') {
          this.status = event.data as ExecutionStatus;
          const finalState = this.status?.state || 'completed';
          if (finalState !== 'cancelled') {
            const outcome = this.status?.run_outcome;
            if (outcome === 'all_skipped') {
              this.triggerCelebration('all_skipped');
            } else if (outcome === 'partial') {
              this.triggerCelebration('partial');
            } else if (finalState === 'failed' || outcome === 'failed') {
              this.triggerCelebration('failure');
            } else {
              this.triggerCelebration('success');
            }
          }
        }
        this.cdr.markForCheck();
      },
      complete: () => {
        this.sseSub = undefined;
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
    return statusIcon(state);
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
