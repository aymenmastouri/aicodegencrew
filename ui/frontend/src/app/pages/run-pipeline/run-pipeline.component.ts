import { Component, OnInit, OnDestroy, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatTableModule } from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subscription } from 'rxjs';

import { ApiService, PresetInfo, PhaseInfo } from '../../services/api.service';
import {
  PipelineService,
  ExecutionStatus,
  RunHistoryEntry,
  EnvVariable,
  SSEEvent,
} from '../../services/pipeline.service';

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
    MatChipsModule,
    MatInputModule,
    MatFormFieldModule,
    MatTableModule,
    MatTabsModule,
    MatTooltipModule,
  ],
  template: `
    <div class="page-container">
      <h1 class="page-title">
        <mat-icon class="title-icon">play_circle</mat-icon>
        Run Pipeline
      </h1>

      <!-- Run Mode Selector -->
      <mat-card class="config-card">
        <mat-card-header>
          <mat-card-title>Pipeline Configuration</mat-card-title>
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
                      <mat-option [value]="preset.name">{{ preset.name }}</mat-option>
                    }
                  </mat-select>
                </mat-form-field>
                @if (selectedPreset) {
                  <div class="phase-chips">
                    <strong>Phases:</strong>
                    @for (phase of getPresetPhases(); track phase) {
                      <mat-chip>{{ phase }}</mat-chip>
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
                      (change)="togglePhase(phase.id, $event.checked)">
                      <span class="phase-label">
                        <strong>{{ phase.order }}.</strong> {{ phase.name }}
                        <span class="phase-id">({{ phase.id }})</span>
                      </span>
                    </mat-checkbox>
                  }
                </div>
              </div>
            </mat-tab>
          </mat-tab-group>
        </mat-card-content>
      </mat-card>

      <!-- Environment Config -->
      <mat-expansion-panel class="env-panel">
        <mat-expansion-panel-header>
          <mat-panel-title>
            <mat-icon>settings</mat-icon>
            Environment Configuration
          </mat-panel-title>
          <mat-panel-description>Override .env variables for this run</mat-panel-description>
        </mat-expansion-panel-header>

        @for (group of envGroups; track group) {
          <h3 class="env-group-title">{{ group }}</h3>
          <div class="env-fields">
            @for (v of getEnvByGroup(group); track v.name) {
              <mat-form-field appearance="outline" class="env-field">
                <mat-label>{{ v.name }}</mat-label>
                <input matInput [(ngModel)]="envValues[v.name]"
                       [placeholder]="v.value || '(not set)'"
                       [matTooltip]="v.description">
                @if (v.required) {
                  <mat-icon matSuffix color="warn" matTooltip="Required">star</mat-icon>
                }
              </mat-form-field>
            }
          </div>
        }
      </mat-expansion-panel>

      <!-- Action Buttons -->
      <div class="action-bar">
        <button mat-raised-button color="primary"
                [disabled]="status?.state === 'running' || (!selectedPreset && selectedPhases.length === 0)"
                (click)="runPipeline()">
          <mat-icon>play_arrow</mat-icon>
          {{ status?.state === 'running' ? 'Running...' : 'Run Pipeline' }}
        </button>
        <button mat-raised-button color="warn"
                [disabled]="status?.state !== 'running'"
                (click)="cancelPipeline()">
          <mat-icon>stop</mat-icon>
          Cancel
        </button>
        @if (status?.state === 'running') {
          <mat-progress-bar mode="indeterminate" class="run-progress"></mat-progress-bar>
        }
      </div>

      <!-- Live Status -->
      @if (status && status.state !== 'idle') {
        <mat-card class="status-card" [class]="'state-' + status.state">
          <mat-card-header>
            <mat-icon mat-card-avatar [class]="'state-icon-' + status.state">
              {{ stateIcon(status.state) }}
            </mat-icon>
            <mat-card-title>{{ status.state | titlecase }}</mat-card-title>
            <mat-card-subtitle>
              @if (status.run_id) { Run: {{ status.run_id }} }
              @if (status.elapsed_seconds) { | Elapsed: {{ formatDuration(status.elapsed_seconds) }} }
            </mat-card-subtitle>
          </mat-card-header>

          <!-- Phase Progress -->
          @if (status.phase_progress.length > 0) {
            <mat-card-content>
              <div class="phase-timeline">
                @for (pp of status.phase_progress; track pp.phase_id) {
                  <div class="phase-step" [class]="'step-' + pp.status">
                    <mat-icon class="step-icon">{{ phaseStepIcon(pp.status) }}</mat-icon>
                    <div class="step-info">
                      <span class="step-name">{{ pp.name || pp.phase_id }}</span>
                      @if (pp.duration_seconds) {
                        <span class="step-duration">{{ pp.duration_seconds | number:'1.1-1' }}s</span>
                      }
                    </div>
                  </div>
                }
              </div>
            </mat-card-content>
          }
        </mat-card>
      }

      <!-- Live Log Output -->
      @if (logLines.length > 0) {
        <mat-card class="log-card">
          <mat-card-header>
            <mat-card-title>
              <mat-icon>terminal</mat-icon>
              Live Output
            </mat-card-title>
            <span class="spacer"></span>
            <button mat-icon-button (click)="scrollToTop()" matTooltip="Scroll to top">
              <mat-icon>vertical_align_top</mat-icon>
            </button>
          </mat-card-header>
          <mat-card-content>
            <div class="log-viewer" #logViewer>
              @for (line of logLines; track $index) {
                <div class="log-line" [class]="getLogLevel(line)">{{ line }}</div>
              }
            </div>
          </mat-card-content>
        </mat-card>
      }

      <!-- Run History -->
      <mat-card class="history-card">
        <mat-card-header>
          <mat-card-title>
            <mat-icon>history</mat-icon>
            Run History
          </mat-card-title>
        </mat-card-header>
        <mat-card-content>
          @if (history.length === 0) {
            <p class="empty-state">No previous runs found</p>
          } @else {
            <table mat-table [dataSource]="history" class="history-table">
              <ng-container matColumnDef="started_at">
                <th mat-header-cell *matHeaderCellDef>Date</th>
                <td mat-cell *matCellDef="let r">{{ r.started_at | date:'short' }}</td>
              </ng-container>
              <ng-container matColumnDef="run_id">
                <th mat-header-cell *matHeaderCellDef>Run ID</th>
                <td mat-cell *matCellDef="let r" class="mono">{{ r.run_id }}</td>
              </ng-container>
              <ng-container matColumnDef="preset">
                <th mat-header-cell *matHeaderCellDef>Preset</th>
                <td mat-cell *matCellDef="let r">{{ r.preset || '-' }}</td>
              </ng-container>
              <ng-container matColumnDef="phases">
                <th mat-header-cell *matHeaderCellDef>Phases</th>
                <td mat-cell *matCellDef="let r">
                  @for (p of r.phases; track p) {
                    <mat-chip class="small-chip">{{ p | slice:0:20 }}</mat-chip>
                  }
                </td>
              </ng-container>
              <ng-container matColumnDef="status">
                <th mat-header-cell *matHeaderCellDef>Status</th>
                <td mat-cell *matCellDef="let r">
                  <span class="status-chip" [class]="'status-' + r.status">{{ r.status }}</span>
                </td>
              </ng-container>
              <ng-container matColumnDef="duration">
                <th mat-header-cell *matHeaderCellDef>Duration</th>
                <td mat-cell *matCellDef="let r">{{ r.duration || '-' }}</td>
              </ng-container>
              <tr mat-header-row *matHeaderRowDef="historyColumns"></tr>
              <tr mat-row *matRowDef="let row; columns: historyColumns;"></tr>
            </table>
          }
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [`
    .page-container { padding: 24px; }
    .page-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 24px;
      font-weight: 400;
      margin-bottom: 24px;
    }
    .title-icon { font-size: 32px; width: 32px; height: 32px; }
    .config-card { margin-bottom: 16px; }
    .tab-content { padding: 16px 0; }
    .full-width { width: 100%; }
    .phase-chips {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 8px;
    }
    .phase-checkboxes {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .phase-label { display: inline-flex; align-items: center; gap: 4px; }
    .phase-id { color: var(--cg-gray-500); font-size: 12px; }
    .env-panel { margin-bottom: 16px; }
    .env-group-title {
      font-size: 14px;
      font-weight: 500;
      color: var(--cg-blue);
      margin: 16px 0 8px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .env-fields {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 8px;
    }
    .env-field { width: 100%; }
    .action-bar {
      display: flex;
      align-items: center;
      gap: 12px;
      margin: 16px 0;
    }
    .run-progress { flex: 1; }

    .status-card { margin-bottom: 16px; }
    .state-completed { border-left: 4px solid var(--cg-success); }
    .state-failed { border-left: 4px solid var(--cg-error); }
    .state-running { border-left: 4px solid var(--cg-blue); }
    .state-cancelled { border-left: 4px solid var(--cg-warn); }
    .state-icon-completed { color: var(--cg-success); }
    .state-icon-failed { color: var(--cg-error); }
    .state-icon-running { color: var(--cg-blue); }
    .state-icon-cancelled { color: var(--cg-warn); }

    .phase-timeline {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      padding: 16px 0;
    }
    .phase-step {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 8px;
      background: var(--cg-gray-100);
    }
    .step-running { background: rgba(0, 112, 173, 0.1); }
    .step-completed { background: rgba(40, 167, 69, 0.1); }
    .step-failed { background: rgba(220, 53, 69, 0.1); }
    .step-icon { font-size: 20px; width: 20px; height: 20px; }
    .step-info { display: flex; flex-direction: column; }
    .step-name { font-size: 13px; font-weight: 500; }
    .step-duration { font-size: 11px; color: var(--cg-gray-500); }

    .log-card { margin-bottom: 16px; }
    .log-card mat-card-header {
      display: flex;
      align-items: center;
    }
    .spacer { flex: 1; }
    .log-viewer {
      background: var(--cg-dark);
      color: #d4d4d4;
      font-family: 'Consolas', 'Courier New', monospace;
      font-size: 12px;
      padding: 12px;
      border-radius: 4px;
      max-height: 500px;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-all;
    }
    .log-line { line-height: 1.5; }
    .log-error { color: #f48771; }
    .log-warning { color: #cca700; }
    .log-info { color: #89d185; }

    .history-card { margin-bottom: 24px; }
    .history-table { width: 100%; }
    .empty-state { color: var(--cg-gray-500); font-style: italic; padding: 16px; }
    .mono { font-family: monospace; }
    .small-chip { font-size: 11px; }
  `],
})
export class RunPipelineComponent implements OnInit, OnDestroy {
  @ViewChild('logViewer') logViewerRef?: ElementRef;

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

  // Execution
  status: ExecutionStatus | null = null;
  logLines: string[] = [];
  history: RunHistoryEntry[] = [];
  historyColumns = ['started_at', 'run_id', 'preset', 'phases', 'status', 'duration'];

  private sseSub?: Subscription;
  private statusInterval?: ReturnType<typeof setInterval>;

  constructor(
    private api: ApiService,
    private pipeline: PipelineService,
    private route: ActivatedRoute,
  ) {}

  ngOnInit(): void {
    // Load config
    this.api.getPresets().subscribe(p => this.presets = p);
    this.api.getPhases().subscribe(p => this.phases = p);
    this.pipeline.getHistory().subscribe(h => this.history = h);
    this.pipeline.getStatus().subscribe(s => {
      this.status = s;
      if (s.state === 'running') {
        this.connectSSE();
      }
    });

    // Load environment
    this.pipeline.getEnv().subscribe(vars => {
      this.envVariables = vars;
      this.envGroups = [...new Set(vars.map(v => v.group))];
      vars.forEach(v => this.envValues[v.name] = v.value);
    });

    // Check for route params (pre-selected preset/phase)
    this.route.queryParams.subscribe(params => {
      if (params['preset']) {
        this.selectedPreset = params['preset'];
        this.runModeIndex = 0;
      }
      if (params['phase']) {
        this.selectedPhases = [params['phase']];
        this.runModeIndex = 1;
      }
    });
  }

  ngOnDestroy(): void {
    this.sseSub?.unsubscribe();
    if (this.statusInterval) clearInterval(this.statusInterval);
  }

  getPresetPhases(): string[] {
    const preset = this.presets.find(p => p.name === this.selectedPreset);
    return preset?.phases || [];
  }

  getEnvByGroup(group: string): EnvVariable[] {
    return this.envVariables.filter(v => v.group === group);
  }

  togglePhase(phaseId: string, checked: boolean | null): void {
    if (checked) {
      if (!this.selectedPhases.includes(phaseId)) {
        this.selectedPhases = [...this.selectedPhases, phaseId];
      }
    } else {
      this.selectedPhases = this.selectedPhases.filter(p => p !== phaseId);
    }
  }

  runPipeline(): void {
    // Collect env overrides (only changed values)
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
    this.pipeline.startPipeline(request).subscribe({
      next: (res) => {
        this.connectSSE();
      },
      error: (err) => {
        const msg = err?.error?.detail || 'Failed to start pipeline';
        this.logLines = [`ERROR: ${msg}`];
      },
    });
  }

  cancelPipeline(): void {
    this.pipeline.cancelPipeline().subscribe({
      next: () => {
        this.refreshStatus();
      },
    });
  }

  private connectSSE(): void {
    this.sseSub?.unsubscribe();

    this.sseSub = this.pipeline.connectSSE().subscribe({
      next: (event: SSEEvent) => {
        if (event.type === 'log_line') {
          this.logLines = [...this.logLines, event.data as string];
          this.scrollToBottom();
        }
        if (event.type === 'status') {
          this.status = event.data as ExecutionStatus;
        }
        if (event.type === 'pipeline_complete') {
          this.status = event.data as ExecutionStatus;
          this.pipeline.getHistory().subscribe(h => this.history = h);
        }
      },
      complete: () => {
        this.refreshStatus();
      },
    });
  }

  private refreshStatus(): void {
    this.pipeline.getStatus().subscribe(s => this.status = s);
    this.pipeline.getHistory().subscribe(h => this.history = h);
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      const el = this.logViewerRef?.nativeElement;
      if (el) el.scrollTop = el.scrollHeight;
    }, 50);
  }

  scrollToTop(): void {
    const el = this.logViewerRef?.nativeElement;
    if (el) el.scrollTop = 0;
  }

  stateIcon(state: string): string {
    switch (state) {
      case 'completed': return 'check_circle';
      case 'failed': return 'error';
      case 'running': return 'hourglass_empty';
      case 'cancelled': return 'cancel';
      default: return 'radio_button_unchecked';
    }
  }

  phaseStepIcon(status: string): string {
    switch (status) {
      case 'completed': return 'check_circle';
      case 'failed': return 'error';
      case 'running': return 'sync';
      default: return 'radio_button_unchecked';
    }
  }

  formatDuration(seconds: number): string {
    if (seconds < 60) return `${seconds.toFixed(0)}s`;
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return `${min}m ${sec}s`;
  }

  getLogLevel(line: string): string {
    if (line.includes('ERROR') || line.includes('Error')) return 'log-error';
    if (line.includes('WARNING') || line.includes('Warn')) return 'log-warning';
    if (line.includes('INFO') || line.includes('✓')) return 'log-info';
    return '';
  }
}
