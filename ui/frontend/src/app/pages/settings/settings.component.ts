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

interface PhaseToggle {
  id: string;
  name: string;
  enabled: boolean;
}

/** Map backend group names to our tab names */
const GROUP_TO_TAB: Record<string, string> = {
  Repository: 'general',
  Output: 'general',
  LLM: 'llm',
  Embeddings: 'llm',
  Indexing: 'indexing',
  'Phase Control': 'advanced',
  Logging: 'advanced',
  General: 'general',
};

const SECRET_KEYS = new Set(['OPENAI_API_KEY']);

/** Fields that should render as dropdowns */
const FIELD_OPTIONS: Record<string, { label: string; value: string }[]> = {
  LLM_PROVIDER: [
    { label: 'On-Prem', value: 'onprem' },
  ],
  LOG_LEVEL: [
    { label: 'DEBUG', value: 'DEBUG' },
    { label: 'INFO', value: 'INFO' },
    { label: 'WARNING', value: 'WARNING' },
    { label: 'ERROR', value: 'ERROR' },
  ],
  ARC42_LANGUAGE: [
    { label: 'Auto-detect', value: '' },
    { label: 'English', value: 'en' },
    { label: 'Deutsch', value: 'de' },
  ],
  INCLUDE_SUBMODULES: [
    { label: 'Yes', value: 'true' },
    { label: 'No', value: 'false' },
  ],
  CREWAI_TRACING_ENABLED: [
    { label: 'Enabled', value: 'true' },
    { label: 'Disabled', value: 'false' },
  ],
};

/** Fields that should render as number inputs */
const NUMERIC_FIELDS = new Set([
  'MAX_LLM_INPUT_TOKENS', 'MAX_LLM_OUTPUT_TOKENS', 'LLM_CONTEXT_WINDOW',
  'LLM_NUM_RETRIES', 'LLM_RETRY_DELAY', 'OLLAMA_TIMEOUT_S',
  'CHUNK_CHARS', 'CHUNK_OVERLAP', 'MAX_FILE_BYTES',
  'INDEX_MAX_TOTAL_FILES', 'INDEX_MAX_TOTAL_CHUNKS', 'INDEX_BATCH_SIZE',
  'MAX_RAG_RESULTS', 'MAX_EVIDENCE_PER_ITEM',
]);

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
          <p class="page-subtitle">Configure environment, LLM, indexing, phases, and advanced options</p>
        </div>
      </div>

      @if (loading) {
        <div class="loading-center">
          <mat-spinner diameter="36"></mat-spinner>
        </div>
      } @else {
        <mat-tab-group animationDuration="200ms" class="settings-tabs">
          <!-- General Tab -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">folder</mat-icon> General
            </ng-template>
            <ng-template matTabContent>
              <div class="tab-content">
                <div class="tab-description">Repository path, output directories, and general settings</div>
                @for (v of getTabVars('general'); track v.name) {
                  <mat-form-field appearance="outline" class="field-full">
                    <mat-label>{{ v.name }}{{ v.required ? ' *' : '' }}</mat-label>
                    @if (getOptions(v.name); as opts) {
                      <mat-select [(ngModel)]="v.value">
                        @for (opt of opts; track opt.value) {
                          <mat-option [value]="opt.value">{{ opt.label }}</mat-option>
                        }
                      </mat-select>
                    } @else if (isNumeric(v.name)) {
                      <input matInput type="number" [(ngModel)]="v.value" [placeholder]="v.description || ''" />
                    } @else {
                      <input matInput [(ngModel)]="v.value" [placeholder]="v.description || ''" />
                    }
                    @if (v.description) {
                      <mat-hint>{{ v.description }}</mat-hint>
                    }
                  </mat-form-field>
                }
                @if (getTabVars('general').length === 0) {
                  <div class="empty-tab">No variables found for this tab.</div>
                }
                <div class="tab-actions">
                  <button mat-stroked-button (click)="resetTab('general')" class="btn-reset">
                    <mat-icon>restart_alt</mat-icon> Reset to defaults
                  </button>
                  <button mat-flat-button color="primary" (click)="saveTab('general')" [disabled]="saving">
                    <mat-icon>save</mat-icon> Save
                  </button>
                </div>
              </div>
            </ng-template>
          </mat-tab>

          <!-- LLM Tab -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">smart_toy</mat-icon> LLM
            </ng-template>
            <ng-template matTabContent>
              <div class="tab-content">
                <div class="tab-description">Language model provider, API keys, embeddings, and token limits</div>
                @for (v of getTabVars('llm'); track v.name) {
                  <mat-form-field appearance="outline" class="field-full">
                    <mat-label>{{ v.name }}{{ v.required ? ' *' : '' }}</mat-label>
                    @if (getOptions(v.name); as opts) {
                      <mat-select [(ngModel)]="v.value">
                        @for (opt of opts; track opt.value) {
                          <mat-option [value]="opt.value">{{ opt.label }}</mat-option>
                        }
                      </mat-select>
                    } @else if (isNumeric(v.name)) {
                      <input matInput type="number" [(ngModel)]="v.value" [placeholder]="v.description || ''" />
                    } @else {
                      <input matInput [(ngModel)]="v.value"
                        [type]="isSecret(v.name) && !showSecrets[v.name] ? 'password' : 'text'"
                        [placeholder]="v.description || ''" />
                      @if (isSecret(v.name)) {
                        <button mat-icon-button matSuffix (click)="showSecrets[v.name] = !showSecrets[v.name]">
                          <mat-icon>{{ showSecrets[v.name] ? 'visibility_off' : 'visibility' }}</mat-icon>
                        </button>
                      }
                    }
                    @if (v.description) {
                      <mat-hint>{{ v.description }}</mat-hint>
                    }
                  </mat-form-field>
                }
                @if (getTabVars('llm').length === 0) {
                  <div class="empty-tab">No variables found for this tab.</div>
                }
                <div class="tab-actions">
                  <button mat-stroked-button (click)="resetTab('llm')" class="btn-reset">
                    <mat-icon>restart_alt</mat-icon> Reset to defaults
                  </button>
                  <button mat-flat-button color="primary" (click)="saveTab('llm')" [disabled]="saving">
                    <mat-icon>save</mat-icon> Save
                  </button>
                </div>
              </div>
            </ng-template>
          </mat-tab>

          <!-- Indexing Tab -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">manage_search</mat-icon> Indexing
            </ng-template>
            <ng-template matTabContent>
              <div class="tab-content">
                <div class="tab-description">Index mode, ChromaDB, chunking, and RAG settings</div>
                @for (v of getTabVars('indexing'); track v.name) {
                  <mat-form-field appearance="outline" class="field-full">
                    <mat-label>{{ v.name }}</mat-label>
                    @if (getOptions(v.name); as opts) {
                      <mat-select [(ngModel)]="v.value">
                        @for (opt of opts; track opt.value) {
                          <mat-option [value]="opt.value">{{ opt.label }}</mat-option>
                        }
                      </mat-select>
                    } @else if (isNumeric(v.name)) {
                      <input matInput type="number" [(ngModel)]="v.value" [placeholder]="v.description || ''" />
                    } @else {
                      <input matInput [(ngModel)]="v.value" [placeholder]="v.description || ''" />
                    }
                    @if (v.description) {
                      <mat-hint>{{ v.description }}</mat-hint>
                    }
                  </mat-form-field>
                }
                @if (getTabVars('indexing').length === 0) {
                  <div class="empty-tab">No variables found for this tab.</div>
                }
                <div class="tab-actions">
                  <button mat-stroked-button (click)="resetTab('indexing')" class="btn-reset">
                    <mat-icon>restart_alt</mat-icon> Reset to defaults
                  </button>
                  <button mat-flat-button color="primary" (click)="saveTab('indexing')" [disabled]="saving">
                    <mat-icon>save</mat-icon> Save
                  </button>
                </div>
              </div>
            </ng-template>
          </mat-tab>

          <!-- Phases Tab -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">account_tree</mat-icon> Phases
            </ng-template>
            <ng-template matTabContent>
              <div class="tab-content">
                <div class="tab-description">Enable or disable pipeline phases. Available presets are shown below.</div>

                @if (phaseToggles.length > 0) {
                  <div class="phase-section-label">Phase Toggles</div>
                  <div class="phase-toggle-grid">
                    @for (p of phaseToggles; track p.id) {
                      <div class="phase-toggle-card">
                        <div class="phase-toggle-info">
                          <span class="phase-toggle-name">{{ p.name }}</span>
                          <span class="phase-toggle-id">{{ p.id }}</span>
                        </div>
                        <mat-slide-toggle [(ngModel)]="p.enabled" color="primary"></mat-slide-toggle>
                      </div>
                    }
                  </div>
                } @else {
                  <div class="empty-tab">No phases loaded.</div>
                }

                @if (presets.length > 0) {
                  <div class="phase-section-label">Presets</div>
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

          <!-- Advanced Tab -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">tune</mat-icon> Advanced
            </ng-template>
            <ng-template matTabContent>
              <div class="tab-content">
                <div class="tab-description">Logging, tracing, skip flags, and directory overrides</div>
                @for (v of getTabVars('advanced'); track v.name) {
                  <mat-form-field appearance="outline" class="field-full">
                    <mat-label>{{ v.name }}</mat-label>
                    @if (getOptions(v.name); as opts) {
                      <mat-select [(ngModel)]="v.value">
                        @for (opt of opts; track opt.value) {
                          <mat-option [value]="opt.value">{{ opt.label }}</mat-option>
                        }
                      </mat-select>
                    } @else if (isNumeric(v.name)) {
                      <input matInput type="number" [(ngModel)]="v.value" [placeholder]="v.description || ''" />
                    } @else {
                      <input matInput [(ngModel)]="v.value" [placeholder]="v.description || ''" />
                    }
                    @if (v.description) {
                      <mat-hint>{{ v.description }}</mat-hint>
                    }
                  </mat-form-field>
                }
                @if (getTabVars('advanced').length === 0) {
                  <div class="empty-tab">No variables found for this tab.</div>
                }
                <div class="tab-actions">
                  <button mat-stroked-button (click)="resetTab('advanced')" class="btn-reset">
                    <mat-icon>restart_alt</mat-icon> Reset to defaults
                  </button>
                  <button mat-flat-button color="primary" (click)="saveTab('advanced')" [disabled]="saving">
                    <mat-icon>save</mat-icon> Save
                  </button>
                </div>
              </div>
            </ng-template>
          </mat-tab>
        </mat-tab-group>
      }
    </div>
  `,
  styles: [
    `
      /* Uses global .page-header, .page-icon, .page-title, .page-subtitle, .loading-center */
      .settings-tabs {
        background: #fff;
        border-radius: 12px;
        overflow: hidden;
      }
      .tab-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
        margin-right: 6px;
        vertical-align: middle;
      }
      .tab-content {
        padding: 24px;
      }
      .tab-description {
        font-size: 13px;
        color: var(--cg-gray-500);
        margin-bottom: 20px;
      }
      .field-full {
        width: 100%;
        margin-bottom: 4px;
      }
      .empty-tab {
        text-align: center;
        padding: 32px 0;
        color: var(--cg-gray-400);
        font-size: 13px;
      }
      .tab-actions {
        display: flex;
        justify-content: flex-end;
        gap: 10px;
        margin-top: 16px;
        padding-top: 16px;
        border-top: 1px solid var(--cg-gray-100, #f0f0f0);
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

      /* Phase toggles */
      .phase-section-label {
        font-size: 14px;
        font-weight: 500;
        color: var(--cg-gray-700);
        margin: 8px 0 12px;
      }
      .phase-toggle-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 10px;
        margin-bottom: 24px;
      }
      .phase-toggle-card {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 16px;
        border-radius: 8px;
        background: var(--cg-gray-50, #f8f9fa);
        border: 1px solid var(--cg-gray-100, #f0f0f0);
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
        font-family: monospace;
      }

      /* Preset cards */
      .preset-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
        gap: 10px;
      }
      .preset-card {
        display: flex;
        gap: 12px;
        padding: 14px 16px;
        border-radius: 8px;
        background: var(--cg-gray-50, #f8f9fa);
        border: 1px solid var(--cg-gray-100, #f0f0f0);
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
        font-family: monospace;
        margin-top: 4px;
      }
    `,
  ],
})
export class SettingsComponent implements OnInit {
  loading = true;
  saving = false;
  allVars: EnvVariable[] = [];
  defaults: Record<string, string> = {};
  showSecrets: Record<string, boolean> = {};
  phaseToggles: PhaseToggle[] = [];
  presets: PresetInfo[] = [];

  constructor(
    private pipelineSvc: PipelineService,
    private api: ApiService,
    private http: HttpClient,
    private snackBar: MatSnackBar,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
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

  /** Use the backend group field to sort variables into tabs */
  getTabVars(tab: string): EnvVariable[] {
    return this.allVars.filter((v) => {
      const mappedTab = GROUP_TO_TAB[v.group] || 'general';
      return mappedTab === tab;
    });
  }

  isSecret(name: string): boolean {
    return SECRET_KEYS.has(name);
  }

  getOptions(name: string): { label: string; value: string }[] | null {
    return FIELD_OPTIONS[name] || null;
  }

  isNumeric(name: string): boolean {
    return NUMERIC_FIELDS.has(name);
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
