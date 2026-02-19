import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatTabsModule } from '@angular/material/tabs';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { HttpClient } from '@angular/common/http';

import { PipelineService, EnvVariable } from '../../services/pipeline.service';
import { ApiService, PresetInfo } from '../../services/api.service';
import { NotificationService } from '../../services/notification.service';

interface PhaseToggle {
  id: string;
  name: string;
  enabled: boolean;
  required: boolean;
}

const GROUP_TO_TAB: Record<string, string> = {
  Repository: 'general',
  Output: 'general',
  LLM: 'llm',
  Embeddings: 'llm',
  'Phase Control': 'advanced',
  Logging: 'advanced',
  General: 'general',
};

const SECRET_KEYS = new Set(['OPENAI_API_KEY', 'CODEGEN_API_KEY']);

// Fields hidden from user-facing settings (internal tuning params)
const HIDDEN_KEYS = new Set(['MAX_LLM_INPUT_TOKENS', 'LLM_CONTEXT_WINDOW']);

const FIELD_OPTIONS: Record<string, { label: string; value: string }[]> = {
  LLM_PROVIDER: [
    { label: 'On-Prem', value: 'onprem' },
    { label: 'OpenAI', value: 'openai' },
    { label: 'Azure', value: 'azure' },
  ],
  INDEX_MODE: [
    { label: 'Auto (re-index when changed)', value: 'auto' },
    { label: 'Smart (incremental updates only)', value: 'smart' },
    { label: 'Force (always re-index)', value: 'force' },
    { label: 'Off (skip re-indexing)', value: 'off' },
  ],
  LOG_LEVEL: [
    { label: 'INFO', value: 'INFO' },
    { label: 'DEBUG', value: 'DEBUG' },
    { label: 'WARNING', value: 'WARNING' },
    { label: 'ERROR', value: 'ERROR' },
    { label: 'CRITICAL', value: 'CRITICAL' },
  ],
};

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatTabsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatSnackBarModule,
    MatSlideToggleModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
  ],
  template: `
    <div class="page-container">
      <div class="page-header">
        <mat-icon class="page-icon">settings</mat-icon>
        <div>
          <h1 class="page-title">Settings</h1>
          <p class="page-subtitle">Configure repository, LLM, phases, and advanced options</p>
        </div>
      </div>

      @if (loading) {
        <div class="loading-center">
          <mat-spinner diameter="36"></mat-spinner>
        </div>
      } @else {
        <mat-tab-group animationDuration="200ms" class="settings-tabs">

          @if (hasTabVars('general')) {
            <mat-tab>
              <ng-template mat-tab-label>
                <mat-icon class="tab-icon">folder</mat-icon> General
              </ng-template>
              <ng-template matTabContent>
                <div class="tab-body">
                  <p class="tab-description">Repository path, output directories, and general settings</p>
                  <div class="field-list">
                    @for (v of getTabVars('general'); track v.name) {
                      <div class="field-item">
                        <mat-form-field appearance="outline" subscriptSizing="dynamic">
                          <mat-label>{{ v.name }}</mat-label>
                          @if (getOptions(v.name); as opts) {
                            <mat-select [(ngModel)]="v.value" [required]="v.required">
                              @for (opt of opts; track opt.value) {
                                <mat-option [value]="opt.value">{{ opt.label }}</mat-option>
                              }
                            </mat-select>
                          } @else {
                            <input matInput [(ngModel)]="v.value" [required]="v.required" />
                          }
                          @if (v.required) {
                            <mat-error>{{ v.name }} is required</mat-error>
                          }
                        </mat-form-field>
                      </div>
                    }
                  </div>
                  <div class="tab-actions">
                    <button mat-stroked-button (click)="resetTab('general')" class="btn-reset">
                      <mat-icon>restart_alt</mat-icon> Reset
                    </button>
                    <button mat-flat-button color="primary" (click)="saveTab('general')"
                      [disabled]="saving || isRunning"
                      [matTooltip]="isRunning ? 'Pipeline is running' : ''">
                      <mat-icon>save</mat-icon> Save
                    </button>
                  </div>
                </div>
              </ng-template>
            </mat-tab>
          }

          @if (hasTabVars('llm')) {
            <mat-tab>
              <ng-template mat-tab-label>
                <mat-icon class="tab-icon">smart_toy</mat-icon> LLM
              </ng-template>
              <ng-template matTabContent>
                <div class="tab-body">
                  <p class="tab-description">Language model provider, API keys, and embeddings</p>
                  <div class="field-list">
                    @for (v of getTabVars('llm'); track v.name) {
                      <div class="field-item">
                        <mat-form-field appearance="outline" subscriptSizing="dynamic">
                          <mat-label>{{ v.name }}</mat-label>
                          @if (getOptions(v.name); as opts) {
                            <mat-select [(ngModel)]="v.value" [required]="v.required">
                              @for (opt of opts; track opt.value) {
                                <mat-option [value]="opt.value">{{ opt.label }}</mat-option>
                              }
                            </mat-select>
                          } @else {
                            <input matInput [(ngModel)]="v.value"
                              [type]="isSecret(v.name) && !showSecrets[v.name] ? 'password' : 'text'"
                              [required]="v.required" />
                            @if (isSecret(v.name)) {
                              <button mat-icon-button matSuffix (click)="showSecrets[v.name] = !showSecrets[v.name]">
                                <mat-icon>{{ showSecrets[v.name] ? 'visibility_off' : 'visibility' }}</mat-icon>
                              </button>
                            }
                          }
                          @if (v.required) {
                            <mat-error>{{ v.name }} is required</mat-error>
                          }
                        </mat-form-field>
                      </div>
                    }
                  </div>
                  <div class="tab-actions">
                    <button mat-stroked-button (click)="resetTab('llm')" class="btn-reset">
                      <mat-icon>restart_alt</mat-icon> Reset
                    </button>
                    <button mat-flat-button color="primary" (click)="saveTab('llm')"
                      [disabled]="saving || isRunning"
                      [matTooltip]="isRunning ? 'Pipeline is running' : ''">
                      <mat-icon>save</mat-icon> Save
                    </button>
                  </div>
                </div>
              </ng-template>
            </mat-tab>
          }

          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">account_tree</mat-icon> Phases
            </ng-template>
            <ng-template matTabContent>
              <div class="tab-body">
                <p class="tab-description">Enable or disable pipeline phases. Available presets are shown below.</p>

                @if (phaseToggles.length > 0) {
                  <div class="section-label">Phase Toggles</div>
                  <div class="phase-toggle-grid">
                    @for (p of phaseToggles; track p.id) {
                      <div class="phase-toggle-card" [class.phase-disabled]="!p.enabled">
                        <div class="phase-toggle-info">
                          <span class="phase-toggle-name">{{ p.name }}</span>
                          <span class="phase-toggle-id">{{ p.id }}</span>
                        </div>
                        <mat-slide-toggle [(ngModel)]="p.enabled" color="primary"
                          [disabled]="p.required || isRunning"
                          [matTooltip]="p.required ? 'Required phase — cannot disable' : (isRunning ? 'Pipeline is running' : '')">
                        </mat-slide-toggle>
                      </div>
                    }
                  </div>
                  <div class="tab-actions">
                    <button mat-flat-button color="primary" (click)="savePhases()"
                      [disabled]="savingPhases || isRunning"
                      [matTooltip]="isRunning ? 'Pipeline is running' : ''">
                      @if (savingPhases) {
                        <mat-spinner diameter="16" style="display:inline-block;margin-right:6px"></mat-spinner>
                      } @else {
                        <mat-icon>save</mat-icon>
                      }
                      Save Phases
                    </button>
                  </div>
                } @else {
                  <div class="empty-tab">No phases loaded.</div>
                }

                @if (presets.length > 0) {
                  <div class="section-label">Presets</div>
                  <div class="preset-grid">
                    @for (preset of presets; track preset.name) {
                      <div class="preset-card">
                        <mat-icon class="preset-icon">{{ preset.icon }}</mat-icon>
                        <div class="preset-info">
                          <div class="preset-name">{{ preset.display_name || preset.name }}</div>
                          <div class="preset-desc">{{ preset.description }}</div>
                          <div class="preset-phases">{{ preset.phases.join(', ') }}</div>
                        </div>
                      </div>
                    }
                  </div>
                }
              </div>
            </ng-template>
          </mat-tab>

          @if (hasTabVars('advanced')) {
            <mat-tab>
              <ng-template mat-tab-label>
                <mat-icon class="tab-icon">tune</mat-icon> Advanced
              </ng-template>
              <ng-template matTabContent>
                <div class="tab-body">
                  <p class="tab-description">Logging, tracing, skip flags, and directory overrides</p>
                  <div class="field-list">
                    @for (v of getTabVars('advanced'); track v.name) {
                      <div class="field-item">
                        <mat-form-field appearance="outline" subscriptSizing="dynamic">
                          <mat-label>{{ v.name }}</mat-label>
                          @if (getOptions(v.name); as opts) {
                            <mat-select [(ngModel)]="v.value">
                              @for (opt of opts; track opt.value) {
                                <mat-option [value]="opt.value">{{ opt.label }}</mat-option>
                              }
                            </mat-select>
                          } @else {
                            <input matInput [(ngModel)]="v.value" />
                          }
                        </mat-form-field>
                      </div>
                    }
                  </div>
                  <div class="tab-actions">
                    <button mat-stroked-button (click)="resetTab('advanced')" class="btn-reset">
                      <mat-icon>restart_alt</mat-icon> Reset
                    </button>
                    <button mat-flat-button color="primary" (click)="saveTab('advanced')"
                      [disabled]="saving || isRunning"
                      [matTooltip]="isRunning ? 'Pipeline is running' : ''">
                      <mat-icon>save</mat-icon> Save
                    </button>
                  </div>
                </div>
              </ng-template>
            </mat-tab>
          }

        </mat-tab-group>
      }
    </div>
  `,
  styles: [`
    .settings-tabs {
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    }
    .tab-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      margin-right: 6px;
      vertical-align: middle;
    }
    .tab-body {
      padding: 28px 32px;
    }
    .tab-description {
      font-size: 13px;
      color: var(--cg-gray-500);
      margin: 0 0 24px;
    }
    .field-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
      max-width: 640px;
    }
    .field-item mat-form-field {
      width: 100%;
    }
    .tab-actions {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      margin-top: 24px;
      padding-top: 16px;
      border-top: 1px solid var(--cg-gray-100, #eee);
    }
    .btn-reset {
      color: var(--cg-gray-500) !important;
    }
    .btn-reset mat-icon,
    .tab-actions button mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      margin-right: 4px;
      vertical-align: middle;
    }
    .empty-tab {
      text-align: center;
      padding: 32px 0;
      color: var(--cg-gray-400);
      font-size: 13px;
    }
    .section-label {
      font-size: 14px;
      font-weight: 500;
      color: var(--cg-gray-700);
      margin: 8px 0 12px;
    }
    .phase-toggle-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 10px;
      margin-bottom: 28px;
    }
    .phase-toggle-card {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      border-radius: 8px;
      background: var(--cg-gray-50, #f8f9fa);
      border: 1px solid var(--cg-gray-100, #eee);
      transition: border-color 0.15s;
    }
    .phase-toggle-card:hover {
      border-color: var(--cg-gray-200);
    }
    .phase-disabled {
      opacity: 0.55;
    }
    .phase-toggle-name {
      font-size: 13px;
      font-weight: 500;
      color: var(--cg-gray-900);
    }
    .phase-toggle-id {
      display: block;
      font-size: 11px;
      color: var(--cg-gray-400);
      font-family: 'Cascadia Code', 'Fira Code', Consolas, monospace;
      margin-top: 2px;
    }
    .preset-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 10px;
    }
    .preset-card {
      display: flex;
      gap: 12px;
      padding: 14px 16px;
      border-radius: 8px;
      background: var(--cg-gray-50, #f8f9fa);
      border: 1px solid var(--cg-gray-100, #eee);
      transition: border-color 0.15s;
    }
    .preset-card:hover {
      border-color: var(--cg-gray-200);
    }
    .preset-icon {
      font-size: 24px;
      width: 24px;
      height: 24px;
      color: var(--cg-blue);
      flex-shrink: 0;
      margin-top: 2px;
    }
    .preset-name {
      font-size: 13px;
      font-weight: 500;
      color: var(--cg-gray-900);
    }
    .preset-desc {
      font-size: 12px;
      color: var(--cg-gray-500);
      margin-top: 2px;
    }
    .preset-phases {
      font-size: 11px;
      color: var(--cg-gray-400);
      font-family: 'Cascadia Code', 'Fira Code', Consolas, monospace;
      margin-top: 4px;
    }
  `],
})
export class SettingsComponent implements OnInit {
  loading = true;
  saving = false;
  savingPhases = false;
  isRunning = false;
  allVars: EnvVariable[] = [];
  defaults: Record<string, string> = {};
  showSecrets: Record<string, boolean> = {};
  phaseToggles: PhaseToggle[] = [];
  presets: PresetInfo[] = [];

  constructor(
    private pipelineSvc: PipelineService,
    private api: ApiService,
    private notifSvc: NotificationService,
    private http: HttpClient,
    private snackBar: MatSnackBar,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.notifSvc.notification$.subscribe((n) => {
      this.isRunning = n.state === 'running';
      this.cdr.markForCheck();
    });
    this.pipelineSvc.getEnvSchema().subscribe({
      next: (vars) => {
        this.allVars = vars;
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.cdr.markForCheck();
      },
    });

    this.http.get<Record<string, string>>('/api/env/defaults').subscribe({
      next: (d) => {
        this.defaults = d;
        this.cdr.markForCheck();
      },
    });

    this.api.getPhases().subscribe({
      next: (phases) => {
        this.phaseToggles = phases.map((p) => ({
          id: p.id,
          name: p.name,
          enabled: p.enabled,
          required: p.required ?? false,
        }));
        this.cdr.markForCheck();
      },
    });

    this.api.getPresets().subscribe({
      next: (p) => {
        this.presets = p;
        this.cdr.markForCheck();
      },
    });
  }

  getTabVars(tab: string): EnvVariable[] {
    return this.allVars.filter((v) => {
      if (HIDDEN_KEYS.has(v.name)) return false;
      const mappedTab = GROUP_TO_TAB[v.group] || 'general';
      return mappedTab === tab;
    });
  }

  hasTabVars(tab: string): boolean {
    return this.getTabVars(tab).length > 0;
  }

  isSecret(name: string): boolean {
    return SECRET_KEYS.has(name);
  }

  getOptions(name: string): { label: string; value: string }[] | null {
    return FIELD_OPTIONS[name] || null;
  }

  saveTab(tab: string): void {
    const vars = this.getTabVars(tab);
    const values: Record<string, string> = {};
    for (const v of vars) {
      values[v.name] = v.value;
    }

    const missing = vars.filter((v) => v.required && !v.value.trim());
    if (missing.length > 0) {
      this.snackBar.open(
        `Required fields missing: ${missing.map((m) => m.name).join(', ')}`,
        'OK',
        { duration: 4000 },
      );
      return;
    }

    this.saving = true;
    this.pipelineSvc.updateEnv(values).subscribe({
      next: () => {
        this.snackBar.open('Settings saved', 'OK', { duration: 3000 });
        this.saving = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.snackBar.open('Failed to save', 'OK', { duration: 4000 });
        this.saving = false;
        this.cdr.markForCheck();
      },
    });
  }

  savePhases(): void {
    this.savingPhases = true;
    const requests = this.phaseToggles
      .filter((p) => !p.required)
      .map((p) =>
        this.http.put(`/api/phases/${p.id}/toggle`, { enabled: p.enabled })
      );

    if (requests.length === 0) {
      this.snackBar.open('No phases to save', 'OK', { duration: 2000 });
      this.savingPhases = false;
      return;
    }

    import('rxjs').then(({ forkJoin }) => {
      forkJoin(requests).subscribe({
        next: () => {
          this.snackBar.open('Phase settings saved', 'OK', { duration: 3000 });
          this.savingPhases = false;
          this.cdr.markForCheck();
        },
        error: () => {
          this.snackBar.open('Failed to save phase settings', 'OK', { duration: 4000 });
          this.savingPhases = false;
          this.cdr.markForCheck();
        },
      });
    });
  }

  resetTab(tab: string): void {
    const vars = this.getTabVars(tab);
    let count = 0;
    for (const v of vars) {
      if (this.defaults[v.name] !== undefined) {
        v.value = this.defaults[v.name];
        count++;
      }
    }
    this.snackBar.open(`Reset ${count} field(s) to defaults (not saved yet)`, 'OK', { duration: 3000 });
  }
}
