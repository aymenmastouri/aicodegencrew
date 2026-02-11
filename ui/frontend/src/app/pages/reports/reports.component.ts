import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule, MatTabChangeEvent } from '@angular/material/tabs';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { ApiService, ReportList, BranchList } from '../../services/api.service';

interface DiffLine {
  type: 'add' | 'del' | 'info' | 'context';
  content: string;
}

@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatTabsModule,
    MatExpansionModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatTableModule,
    MatButtonModule,
    MatTooltipModule,
    MatSnackBarModule,
  ],
  template: `
    <div class="page-container">
      <h1 class="page-title">
        <mat-icon>summarize</mat-icon>
        Reports
      </h1>

      @if (loading) {
        <div class="loading-center">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else {
        <mat-tab-group (selectedTabChange)="onTabChange($event)">

          <!-- ============================================================ -->
          <!-- TAB 1: Development Plans                                     -->
          <!-- ============================================================ -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">description</mat-icon>
              Development Plans ({{ reports?.plans?.length || 0 }})
            </ng-template>

            @if (reports?.plans?.length) {
              <mat-accordion class="report-accordion" multi>
                @for (plan of reports!.plans; track plan['task_id']) {
                  <mat-expansion-panel>
                    <mat-expansion-panel-header>
                      <mat-panel-title>
                        <mat-icon class="panel-icon">task_alt</mat-icon>
                        <span class="mono">{{ plan['task_id'] }}</span>
                      </mat-panel-title>
                      <mat-panel-description>
                        @if ($any(plan['development_plan'])?.['complexity']) {
                          <span class="status-chip"
                            [class]="getComplexityClass($any(plan['development_plan'])['complexity'])">
                            {{ $any(plan['development_plan'])['complexity'] }}
                          </span>
                        }
                        <span class="plan-summary-text">
                          {{ $any(plan['understanding'])?.['summary'] || 'No summary' }}
                        </span>
                      </mat-panel-description>
                    </mat-expansion-panel-header>

                    <div class="plan-body">
                      <!-- Toggle Raw JSON -->
                      <div class="toggle-row">
                        <button mat-button (click)="toggleRawJson($any(plan['task_id']))">
                          <mat-icon>{{ showRawJson[$any(plan['task_id'])] ? 'visibility' : 'code' }}</mat-icon>
                          {{ showRawJson[$any(plan['task_id'])] ? 'Show Structured' : 'Show Raw JSON' }}
                        </button>
                      </div>

                      @if (showRawJson[$any(plan['task_id'])]) {
                        <pre class="plan-content code-viewer">{{ plan | json }}</pre>
                      } @else {
                        <!-- Summary -->
                        @if ($any(plan['understanding'])) {
                          <mat-card class="section-card">
                            <mat-card-header>
                              <mat-card-title>Summary</mat-card-title>
                            </mat-card-header>
                            <mat-card-content>
                              <p>{{ $any(plan['understanding'])['summary'] }}</p>
                              @if ($any(plan['understanding'])['acceptance_criteria']?.length) {
                                <h4>Acceptance Criteria</h4>
                                <ul class="criteria-list">
                                  @for (c of $any(plan['understanding'])['acceptance_criteria']; track c) {
                                    <li>{{ c }}</li>
                                  }
                                </ul>
                              }
                              @if ($any(plan['understanding'])['technical_notes']) {
                                <h4>Technical Notes</h4>
                                <p class="muted">{{ $any(plan['understanding'])['technical_notes'] }}</p>
                              }
                            </mat-card-content>
                          </mat-card>
                        }

                        <!-- Affected Components -->
                        @if ($any(plan['development_plan'])?.['affected_components']?.length) {
                          <mat-card class="section-card">
                            <mat-card-header>
                              <mat-card-title>
                                Affected Components ({{ $any(plan['development_plan'])['affected_components'].length }})
                              </mat-card-title>
                            </mat-card-header>
                            <mat-card-content>
                              <div class="table-scroll">
                                <table mat-table [dataSource]="$any(plan['development_plan'])['affected_components']">
                                  <ng-container matColumnDef="name">
                                    <th mat-header-cell *matHeaderCellDef>Name</th>
                                    <td mat-cell *matCellDef="let c" class="mono">{{ c.name }}</td>
                                  </ng-container>
                                  <ng-container matColumnDef="stereotype">
                                    <th mat-header-cell *matHeaderCellDef>Stereotype</th>
                                    <td mat-cell *matCellDef="let c">{{ c.stereotype || '-' }}</td>
                                  </ng-container>
                                  <ng-container matColumnDef="layer">
                                    <th mat-header-cell *matHeaderCellDef>Layer</th>
                                    <td mat-cell *matCellDef="let c">{{ c.layer || '-' }}</td>
                                  </ng-container>
                                  <ng-container matColumnDef="change_type">
                                    <th mat-header-cell *matHeaderCellDef>Change Type</th>
                                    <td mat-cell *matCellDef="let c">
                                      <span class="status-chip" [class]="'action-' + (c.change_type || 'modified')">
                                        {{ c.change_type || 'modify' }}
                                      </span>
                                    </td>
                                  </ng-container>
                                  <ng-container matColumnDef="relevance_score">
                                    <th mat-header-cell *matHeaderCellDef>Relevance</th>
                                    <td mat-cell *matCellDef="let c">
                                      {{ c.relevance_score != null ? (c.relevance_score | number:'1.0-2') : '-' }}
                                    </td>
                                  </ng-container>
                                  <tr mat-header-row *matHeaderRowDef="componentColumns"></tr>
                                  <tr mat-row *matRowDef="let row; columns: componentColumns;"></tr>
                                </table>
                              </div>
                            </mat-card-content>
                          </mat-card>
                        }

                        <!-- Implementation Steps -->
                        @if ($any(plan['development_plan'])?.['implementation_steps']?.length) {
                          <mat-card class="section-card">
                            <mat-card-header>
                              <mat-card-title>Implementation Steps</mat-card-title>
                            </mat-card-header>
                            <mat-card-content>
                              <ol class="steps-list">
                                @for (step of $any(plan['development_plan'])['implementation_steps']; track step) {
                                  <li>
                                    @if (isString(step)) {
                                      {{ step }}
                                    } @else {
                                      <strong>{{ step['description'] || step['step'] }}</strong>
                                      @if (step['details']) {
                                        <p class="muted">{{ step['details'] }}</p>
                                      }
                                    }
                                  </li>
                                }
                              </ol>
                            </mat-card-content>
                          </mat-card>
                        }

                        <!-- Test Strategy -->
                        @if ($any(plan['development_plan'])?.['test_strategy']) {
                          <mat-card class="section-card">
                            <mat-card-header>
                              <mat-card-title>Test Strategy</mat-card-title>
                            </mat-card-header>
                            <mat-card-content>
                              @if ($any(plan['development_plan'])['test_strategy']['unit_tests']?.length) {
                                <h4>Unit Tests</h4>
                                <ul>
                                  @for (t of $any(plan['development_plan'])['test_strategy']['unit_tests']; track t) {
                                    <li>{{ t }}</li>
                                  }
                                </ul>
                              }
                              @if ($any(plan['development_plan'])['test_strategy']['integration_tests']?.length) {
                                <h4>Integration Tests</h4>
                                <ul>
                                  @for (t of $any(plan['development_plan'])['test_strategy']['integration_tests']; track t) {
                                    <li>{{ t }}</li>
                                  }
                                </ul>
                              }
                              @if ($any(plan['development_plan'])['test_strategy']['similar_patterns']?.length) {
                                <h4>Similar Patterns</h4>
                                <div class="chip-list">
                                  @for (p of $any(plan['development_plan'])['test_strategy']['similar_patterns']; track p) {
                                    <span class="status-chip status-ready">{{ isString(p) ? p : p['name'] || p['pattern'] }}</span>
                                  }
                                </div>
                              }
                            </mat-card-content>
                          </mat-card>
                        }

                        <!-- Collapsible: Security, Validation, Error Handling, Architecture -->
                        <mat-accordion class="nested-accordion">
                          @if ($any(plan['development_plan'])?.['security_considerations']) {
                            <mat-expansion-panel>
                              <mat-expansion-panel-header>
                                <mat-panel-title>
                                  <mat-icon class="panel-icon">security</mat-icon>
                                  Security Considerations
                                </mat-panel-title>
                              </mat-expansion-panel-header>
                              <pre class="section-json">{{ $any(plan['development_plan'])['security_considerations'] | json }}</pre>
                            </mat-expansion-panel>
                          }
                          @if ($any(plan['development_plan'])?.['validation_strategy']) {
                            <mat-expansion-panel>
                              <mat-expansion-panel-header>
                                <mat-panel-title>
                                  <mat-icon class="panel-icon">check_circle</mat-icon>
                                  Validation Strategy
                                </mat-panel-title>
                              </mat-expansion-panel-header>
                              <pre class="section-json">{{ $any(plan['development_plan'])['validation_strategy'] | json }}</pre>
                            </mat-expansion-panel>
                          }
                          @if ($any(plan['development_plan'])?.['error_handling']) {
                            <mat-expansion-panel>
                              <mat-expansion-panel-header>
                                <mat-panel-title>
                                  <mat-icon class="panel-icon">error_outline</mat-icon>
                                  Error Handling
                                </mat-panel-title>
                              </mat-expansion-panel-header>
                              <pre class="section-json">{{ $any(plan['development_plan'])['error_handling'] | json }}</pre>
                            </mat-expansion-panel>
                          }
                          @if ($any(plan['development_plan'])?.['architecture_context']) {
                            <mat-expansion-panel>
                              <mat-expansion-panel-header>
                                <mat-panel-title>
                                  <mat-icon class="panel-icon">architecture</mat-icon>
                                  Architecture Context
                                </mat-panel-title>
                              </mat-expansion-panel-header>
                              <pre class="section-json">{{ $any(plan['development_plan'])['architecture_context'] | json }}</pre>
                            </mat-expansion-panel>
                          }
                        </mat-accordion>

                        <!-- Upgrade Plan (conditional) -->
                        @if ($any(plan['development_plan'])?.['upgrade_plan']) {
                          <mat-card class="section-card">
                            <mat-card-header>
                              <mat-card-title>Upgrade Plan</mat-card-title>
                            </mat-card-header>
                            <mat-card-content>
                              @if ($any(plan['development_plan'])['upgrade_plan']['framework']) {
                                <p><strong>Framework:</strong> {{ $any(plan['development_plan'])['upgrade_plan']['framework'] }}</p>
                              }
                              @if ($any(plan['development_plan'])['upgrade_plan']['from_version']) {
                                <p>
                                  <strong>Version:</strong>
                                  {{ $any(plan['development_plan'])['upgrade_plan']['from_version'] }}
                                  &rarr; {{ $any(plan['development_plan'])['upgrade_plan']['to_version'] }}
                                </p>
                              }
                              @if ($any(plan['development_plan'])['upgrade_plan']['migration_sequence']?.length) {
                                <h4>Migration Sequence</h4>
                                <table class="simple-table">
                                  <thead>
                                    <tr>
                                      <th>#</th>
                                      <th>Step</th>
                                      <th>Description</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    @for (step of $any(plan['development_plan'])['upgrade_plan']['migration_sequence']; track step; let i = $index) {
                                      <tr>
                                        <td>{{ i + 1 }}</td>
                                        <td>{{ step['step'] || step['name'] || '-' }}</td>
                                        <td>{{ step['description'] || step['details'] || '-' }}</td>
                                      </tr>
                                    }
                                  </tbody>
                                </table>
                              }
                              @if ($any(plan['development_plan'])['upgrade_plan']['verification_commands']?.length) {
                                <h4>Verification Commands</h4>
                                <ul class="mono">
                                  @for (cmd of $any(plan['development_plan'])['upgrade_plan']['verification_commands']; track cmd) {
                                    <li>{{ cmd }}</li>
                                  }
                                </ul>
                              }
                            </mat-card-content>
                          </mat-card>
                        }
                      }
                    </div>
                  </mat-expansion-panel>
                }
              </mat-accordion>
            } @else {
              <div class="empty-inline tab-empty">
                <mat-icon>description</mat-icon>
                <span>No development plans found. Run Phase 4 (Planning) to generate plans.</span>
              </div>
            }
          </mat-tab>

          <!-- ============================================================ -->
          <!-- TAB 2: Codegen Reports                                       -->
          <!-- ============================================================ -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">code</mat-icon>
              Codegen Reports ({{ reports?.codegen_reports?.length || 0 }})
            </ng-template>

            @if (reports?.codegen_reports?.length) {
              <mat-accordion class="report-accordion" multi>
                @for (report of reports!.codegen_reports; track report['task_id']) {
                  <mat-expansion-panel>
                    <mat-expansion-panel-header>
                      <mat-panel-title>
                        <mat-icon class="panel-icon">code</mat-icon>
                        <span class="mono">{{ report['task_id'] }}</span>
                      </mat-panel-title>
                      <mat-panel-description>
                        <span class="status-chip" [class]="'status-' + report['status']">
                          {{ report['status'] }}
                        </span>
                        @if ($any(report['generated_files'])?.length) {
                          <span class="file-count-badge">
                            {{ $any(report['generated_files']).length }} files
                          </span>
                        }
                      </mat-panel-description>
                    </mat-expansion-panel-header>

                    <div class="report-body">
                      <!-- Toggle Raw JSON -->
                      <div class="toggle-row">
                        <button mat-button (click)="toggleRawJson('report_' + report['task_id'])">
                          <mat-icon>{{ showRawJson['report_' + report['task_id']] ? 'visibility' : 'code' }}</mat-icon>
                          {{ showRawJson['report_' + report['task_id']] ? 'Show Structured' : 'Show Raw JSON' }}
                        </button>
                      </div>

                      @if (showRawJson['report_' + report['task_id']]) {
                        <pre class="plan-content code-viewer">{{ report | json }}</pre>
                      } @else {
                        <!-- Report Summary -->
                        <mat-card class="section-card">
                          <mat-card-content>
                            <div class="report-meta">
                              @if (report['branch']) {
                                <div class="meta-item">
                                  <mat-icon>account_tree</mat-icon>
                                  <span class="mono">{{ report['branch'] }}</span>
                                </div>
                              }
                              @if (report['token_usage']) {
                                <div class="meta-item">
                                  <mat-icon>token</mat-icon>
                                  <span>{{ $any(report['token_usage'])['total'] || report['token_usage'] }} tokens</span>
                                </div>
                              }
                            </div>
                          </mat-card-content>
                        </mat-card>

                        <!-- Generated Files -->
                        @if ($any(report['generated_files'])?.length) {
                          <div class="files-list">
                            @for (file of $any(report['generated_files']); track file['path']) {
                              <div class="file-entry"
                                (click)="toggleFile(report['task_id'] + ':' + file['path'])"
                                [class.expanded]="expandedFiles[report['task_id'] + ':' + file['path']]">
                                <div class="file-header">
                                  <mat-icon class="expand-icon">
                                    {{ expandedFiles[report['task_id'] + ':' + file['path']] ? 'expand_more' : 'chevron_right' }}
                                  </mat-icon>
                                  <span class="file-path mono">{{ file['path'] }}</span>
                                  <span class="status-chip" [class]="'action-' + (file['action'] || 'modified')">
                                    {{ file['action'] || 'modified' }}
                                  </span>
                                  <span class="lang-badge">{{ getLanguage(file['path']) }}</span>
                                </div>
                                @if (expandedFiles[report['task_id'] + ':' + file['path']] && file['diff']) {
                                  <div class="diff-viewer">
                                    @for (line of parseDiffLines(file['diff']); track $index) {
                                      <div [class]="'diff-line diff-line-' + line.type">{{ line.content }}</div>
                                    }
                                  </div>
                                }
                                @if (expandedFiles[report['task_id'] + ':' + file['path']] && !file['diff']) {
                                  <div class="diff-viewer">
                                    <span class="muted">No diff available for this file.</span>
                                  </div>
                                }
                              </div>
                            }
                          </div>
                        }
                      }
                    </div>
                  </mat-expansion-panel>
                }
              </mat-accordion>
            } @else {
              <div class="empty-inline tab-empty">
                <mat-icon>code</mat-icon>
                <span>No codegen reports found. Run Phase 5 (Code Generation) to see results.</span>
              </div>
            }
          </mat-tab>

          <!-- ============================================================ -->
          <!-- TAB 3: Git Branches                                          -->
          <!-- ============================================================ -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">account_tree</mat-icon>
              Git Branches ({{ branches?.branches?.length || 0 }})
            </ng-template>

            @if (branchesLoading) {
              <div class="loading-center">
                <mat-spinner diameter="32"></mat-spinner>
              </div>
            } @else if (branchesError) {
              <div class="empty-inline tab-empty">
                <mat-icon>error_outline</mat-icon>
                <span>{{ branchesError }}</span>
              </div>
            } @else if (branches?.branches?.length) {
              <div class="branches-grid">
                @for (branch of branches!.branches; track branch.task_id) {
                  <mat-card class="branch-card">
                    <mat-card-content>
                      <div class="branch-row">
                        <div class="branch-info">
                          <mat-icon class="branch-icon">account_tree</mat-icon>
                          <span class="mono branch-name">{{ branch.name }}</span>
                        </div>
                        <div class="branch-actions">
                          <span class="status-chip status-ready" matTooltip="Files changed vs main">
                            {{ branch.file_count }} files
                          </span>
                          @if (branch.has_report) {
                            <span class="status-chip status-completed"
                              matTooltip="View codegen report"
                              style="cursor:pointer"
                              (click)="goToReport(branch.task_id)">
                              Has Report
                            </span>
                          }
                          <button mat-icon-button color="warn"
                            matTooltip="Delete branch"
                            (click)="deleteBranch(branch.task_id)">
                            <mat-icon>delete</mat-icon>
                          </button>
                        </div>
                      </div>
                    </mat-card-content>
                  </mat-card>
                }
              </div>
            } @else {
              <div class="empty-inline tab-empty">
                <mat-icon>account_tree</mat-icon>
                <span>No codegen branches found. Run Phase 5 to generate code.</span>
              </div>
            }
          </mat-tab>
        </mat-tab-group>
      }
    </div>
  `,
  styles: [`
    .tab-icon { margin-right: 6px; font-size: 18px; }
    .report-accordion { margin-top: 16px; }
    .nested-accordion { margin-top: 12px; }
    .panel-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      margin-right: 8px;
      color: var(--cg-blue);
    }
    .plan-content {
      max-height: 500px;
      overflow: auto;
      background: var(--cg-dark);
      color: #eeffff;
      padding: 16px;
      border-radius: 8px;
      font-size: 12px;
      line-height: 1.6;
    }
    .empty-inline {
      display: flex;
      align-items: center;
      gap: 10px;
      color: var(--cg-gray-500);
      font-size: 14px;
    }
    .empty-inline .mat-icon { color: var(--cg-gray-200); }
    .tab-empty { padding: 32px 16px; }

    /* Plan structured view */
    .plan-body, .report-body { padding: 4px 0; }
    .toggle-row { display: flex; justify-content: flex-end; margin-bottom: 8px; }
    .section-card { margin-bottom: 12px; }
    .section-card mat-card-title { font-size: 15px; font-weight: 600; }
    h4 { font-size: 13px; font-weight: 600; margin: 12px 0 6px; color: var(--cg-gray-900); }
    .criteria-list, .steps-list { padding-left: 20px; margin: 4px 0; }
    .criteria-list li, .steps-list li { margin: 4px 0; font-size: 13px; }
    .muted { color: var(--cg-gray-500); font-size: 13px; }
    .chip-list { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
    .section-json {
      background: var(--cg-gray-50);
      padding: 12px;
      border-radius: 6px;
      font-size: 12px;
      line-height: 1.5;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-all;
    }
    .plan-summary-text {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 400px;
      margin-left: 8px;
    }
    .table-scroll { overflow-x: auto; }
    .simple-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      margin-top: 8px;
    }
    .simple-table th, .simple-table td {
      border: 1px solid var(--cg-gray-200);
      padding: 6px 10px;
      text-align: left;
    }
    .simple-table th {
      background: var(--cg-gray-50);
      font-weight: 600;
    }

    /* Codegen report */
    .report-meta {
      display: flex;
      gap: 20px;
      flex-wrap: wrap;
    }
    .meta-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      color: var(--cg-gray-500);
    }
    .meta-item .mat-icon { font-size: 18px; width: 18px; height: 18px; }
    .file-count-badge {
      margin-left: 8px;
      font-size: 12px;
      color: var(--cg-gray-500);
    }
    .files-list { margin-top: 12px; }
    .file-entry {
      border: 1px solid var(--cg-gray-200);
      border-radius: 8px;
      margin-bottom: 8px;
      overflow: hidden;
    }
    .file-header {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 14px;
      cursor: pointer;
      transition: background 0.15s;
    }
    .file-header:hover { background: var(--cg-gray-50); }
    .expand-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
      color: var(--cg-gray-500);
    }
    .file-path { flex: 1; font-size: 13px; }
    .lang-badge {
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 10px;
      background: var(--cg-gray-100);
      color: var(--cg-gray-500);
      text-transform: uppercase;
      font-weight: 600;
    }
    .diff-viewer { border-radius: 0 0 8px 8px; }
    .diff-line { min-height: 19px; padding: 0 12px; }

    /* Branches */
    .branches-grid {
      display: grid;
      gap: 10px;
      margin-top: 16px;
    }
    .branch-card { margin: 0; }
    .branch-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 10px;
    }
    .branch-info {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .branch-icon {
      color: var(--cg-blue);
      font-size: 20px;
      width: 20px;
      height: 20px;
    }
    .branch-name { font-size: 14px; }
    .branch-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  `],
})
export class ReportsComponent implements OnInit {
  reports: ReportList | null = null;
  loading = true;
  branches: BranchList | null = null;
  branchesLoading = false;
  branchesError = '';
  showRawJson: Record<string, boolean> = {};
  expandedFiles: Record<string, boolean> = {};

  componentColumns = ['name', 'stereotype', 'layer', 'change_type', 'relevance_score'];

  private tabGroup: { selectedIndex: number } | null = null;

  constructor(
    private api: ApiService,
    private cdr: ChangeDetectorRef,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    this.api.getReports().subscribe({
      next: r => { this.reports = r; this.loading = false; this.cdr.markForCheck(); },
      error: () => { this.loading = false; this.cdr.markForCheck(); },
    });
  }

  onTabChange(event: MatTabChangeEvent): void {
    if (event.index === 2 && !this.branches) {
      this.loadBranches();
    }
  }

  loadBranches(): void {
    this.branchesLoading = true;
    this.branchesError = '';
    this.api.getBranches().subscribe({
      next: b => {
        this.branches = b;
        this.branchesLoading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.branchesError = 'Could not read git branches (is PROJECT_PATH a git repository?)';
        this.branchesLoading = false;
        this.cdr.markForCheck();
      },
    });
  }

  toggleRawJson(id: string): void {
    this.showRawJson[id] = !this.showRawJson[id];
  }

  toggleFile(fileKey: string): void {
    this.expandedFiles[fileKey] = !this.expandedFiles[fileKey];
  }

  parseDiffLines(diff: string): DiffLine[] {
    return diff.split('\n').map(line => {
      if (line.startsWith('+')) return { type: 'add' as const, content: line };
      if (line.startsWith('-')) return { type: 'del' as const, content: line };
      if (line.startsWith('@@')) return { type: 'info' as const, content: line };
      return { type: 'context' as const, content: line };
    });
  }

  getLanguage(filePath: string): string {
    const ext = filePath.split('.').pop()?.toLowerCase() || '';
    const map: Record<string, string> = {
      ts: 'TypeScript', js: 'JavaScript', java: 'Java', py: 'Python',
      html: 'HTML', css: 'CSS', scss: 'SCSS', json: 'JSON',
      xml: 'XML', yaml: 'YAML', yml: 'YAML', kt: 'Kotlin',
      sql: 'SQL', sh: 'Shell', md: 'Markdown', gradle: 'Gradle',
    };
    return map[ext] || ext.toUpperCase();
  }

  getComplexityClass(level: string): string {
    const l = (level || '').toLowerCase();
    if (l === 'low') return 'status-chip complexity-low';
    if (l === 'high') return 'status-chip complexity-high';
    return 'status-chip complexity-medium';
  }

  deleteBranch(taskId: string): void {
    if (!confirm(`Delete branch codegen/${taskId}?`)) return;
    this.api.deleteBranch(taskId).subscribe({
      next: () => {
        if (this.branches) {
          this.branches.branches = this.branches.branches.filter(b => b.task_id !== taskId);
        }
        this.snackBar.open(`Branch codegen/${taskId} deleted`, 'OK', { duration: 3000 });
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.snackBar.open(`Failed to delete branch: ${err.error?.detail || err.message}`, 'OK', { duration: 5000 });
      },
    });
  }

  goToReport(taskId: string): void {
    // Switch to Codegen Reports tab (index 1)
    // We find the mat-tab-group element and set its selectedIndex
    const tabGroupEl = document.querySelector('mat-tab-group');
    if (tabGroupEl) {
      const matTabGroup = (tabGroupEl as any).__ngContext__?.[0];
      // Simple approach: use the DOM to click the second tab
      const tabs = tabGroupEl.querySelectorAll('.mat-mdc-tab');
      if (tabs[1]) {
        (tabs[1] as HTMLElement).click();
      }
    }
  }

  isString(val: unknown): boolean {
    return typeof val === 'string';
  }
}
