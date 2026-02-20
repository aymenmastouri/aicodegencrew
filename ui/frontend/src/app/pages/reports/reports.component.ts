import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule, MatTabChangeEvent } from '@angular/material/tabs';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';

import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { marked } from 'marked';

import { ApiService, ReportList, BranchList } from '../../services/api.service';
import { NotificationService } from '../../services/notification.service';
import { ConfirmDialogComponent, ConfirmDialogData } from '../../shared/confirm-dialog.component';
import { formatBytes as formatBytesUtil } from '../../shared/phase-utils';

interface DiffLine {
  type: 'add' | 'del' | 'info' | 'context';
  content: string;
}

interface ParsedComponent {
  id: string;
  name: string;
  container: string;
  package: string;
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
    MatButtonModule,
    MatTooltipModule,
    MatSnackBarModule,
    MatDialogModule,
  ],
  template: `
    <div class="page-container">
      <div class="page-header">
        <mat-icon class="page-icon">summarize</mat-icon>
        <div>
          <h1 class="page-title">Reports</h1>
          <p class="page-subtitle">Architecture documentation, development plans, code generation, and branches</p>
        </div>
      </div>

      @if (loading) {
        <div class="loading-center">
          <mat-spinner diameter="36"></mat-spinner>
        </div>
      } @else {
        <mat-tab-group [(selectedIndex)]="activeTabIndex" (selectedTabChange)="onTabChange($event)">
          <!-- ============================================================ -->
          <!-- TAB 1: Architecture Documents                                -->
          <!-- ============================================================ -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">auto_stories</mat-icon>
              Architecture ({{ reports?.document_reports?.length || 0 }})
            </ng-template>

            @if (docGroupKeys.length > 0) {
              <div class="doc-groups">
                @for (groupKey of docGroupKeys; track groupKey) {
                  <div class="doc-group">
                    <div
                      class="doc-group-header"
                      role="button"
                      tabindex="0"
                      (click)="toggleDocGroup(groupKey)"
                      (keydown.enter)="toggleDocGroup(groupKey)"
                      (keydown.space)="toggleDocGroup(groupKey); $event.preventDefault()"
                    >
                      <div class="doc-group-icon-wrap" [class]="'group-' + groupKey">
                        <mat-icon>{{ docGroupMeta[groupKey]?.icon || 'description' }}</mat-icon>
                      </div>
                      <div class="doc-group-info">
                        <h3 class="doc-group-title">{{ docGroupMeta[groupKey]?.label || groupKey }}</h3>
                        <p class="doc-group-desc">
                          {{ docGroupMeta[groupKey]?.description || '' }}
                          <span class="doc-group-count">{{ docGroups[groupKey].length }} files</span>
                        </p>
                      </div>
                      <mat-icon class="doc-group-chevron">{{
                        expandedDocGroups[groupKey] ? 'expand_less' : 'expand_more'
                      }}</mat-icon>
                    </div>
                    @if (expandedDocGroups[groupKey]) {
                      <div class="doc-group-files">
                        @for (file of docGroups[groupKey]; track file['_file']) {
                          <div class="doc-file-card">
                            <div
                              class="doc-file-row"
                              role="button"
                              tabindex="0"
                              (click)="toggleDocPreview($any(file['_file']))"
                              (keydown.enter)="toggleDocPreview($any(file['_file']))"
                              (keydown.space)="toggleDocPreview($any(file['_file'])); $event.preventDefault()"
                            >
                              <mat-icon class="doc-file-icon">{{
                                file['_type'] === 'md' ? 'article' : file['_type'] === 'drawio' ? 'draw' : 'data_object'
                              }}</mat-icon>
                              <div class="doc-file-info">
                                <span class="doc-file-name">{{ formatDocName($any(file['_name'])) }}</span>
                                <span class="doc-file-meta"
                                  >{{ $any(file['_type']) | uppercase }} &middot;
                                  {{ formatBytes($any(file['_size'])) }}</span
                                >
                              </div>
                              <button
                                mat-icon-button
                                class="dl-btn"
                                matTooltip="Download"
                                aria-label="Download"
                                (click)="
                                  downloadFileContent($any(file['_file']), $any(file['_name']));
                                  $event.stopPropagation()
                                "
                              >
                                <mat-icon>download</mat-icon>
                              </button>
                              <mat-icon class="doc-expand-icon">
                                {{ docPreviewOpen[$any(file['_file'])] ? 'expand_less' : 'expand_more' }}
                              </mat-icon>
                            </div>
                            @if (docPreviewOpen[$any(file['_file'])]) {
                              <div class="doc-preview">
                                @if (fileLoading[$any(file['_file'])]) {
                                  <div class="loading-center"><mat-spinner diameter="24"></mat-spinner></div>
                                } @else if (fileContents[$any(file['_file'])]) {
                                  @if (file['_type'] === 'md') {
                                    <div
                                      class="rendered-md markdown-body"
                                      [innerHTML]="renderMarkdown(fileContents[$any(file['_file'])])"
                                    ></div>
                                  } @else {
                                    <pre class="code-viewer doc-viewer">{{ fileContents[$any(file['_file'])] }}</pre>
                                  }
                                }
                              </div>
                            }
                          </div>
                        }
                      </div>
                    }
                  </div>
                }
              </div>
            } @else {
              <div class="empty-inline tab-empty">
                <mat-icon>auto_stories</mat-icon>
                <span>No documentation found. Run the Document phase to generate architecture docs.</span>
              </div>
            }
          </mat-tab>

          <!-- ============================================================ -->
          <!-- TAB 2: Development Plans                                     -->
          <!-- ============================================================ -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">description</mat-icon>
              Development Plans ({{ reports?.plans?.length || 0 }})
            </ng-template>

            @if (reports?.plans?.length) {
              <mat-accordion class="report-accordion" multi>
                @for (plan of reports!.plans; track $any(plan['task_id'])) {
                  <mat-expansion-panel>
                    <mat-expansion-panel-header>
                      <mat-panel-title>
                        <mat-icon class="panel-icon">task_alt</mat-icon>
                        <span class="mono">{{ plan['task_id'] }}</span>
                      </mat-panel-title>
                      <mat-panel-description>
                        @if ($any(plan['development_plan'])?.['estimated_complexity']) {
                          <span
                            class="severity-chip"
                            [class]="getSeverityClass($any(plan['development_plan'])['estimated_complexity'])"
                          >
                            {{ $any(plan['development_plan'])['estimated_complexity'] }}
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
                        <button mat-button (click)="downloadPlanJson(plan)">
                          <mat-icon>download</mat-icon> Download
                        </button>
                        <button mat-button (click)="toggleRawJson($any(plan['task_id']))">
                          <mat-icon>{{ showRawJson[$any(plan['task_id'])] ? 'visibility' : 'data_object' }}</mat-icon>
                          {{ showRawJson[$any(plan['task_id'])] ? 'Structured View' : 'Raw JSON' }}
                        </button>
                      </div>

                      @if (showRawJson[$any(plan['task_id'])]) {
                        <pre class="code-viewer">{{ plan | json }}</pre>
                      } @else {
                        <!-- ==================== OVERVIEW ==================== -->
                        <div class="overview-card">
                          <h2 class="overview-title">{{ $any(plan['understanding'])?.['summary'] }}</h2>

                          <div class="metrics-row">
                            @if ($any(plan['development_plan'])?.['estimated_complexity']) {
                              <div class="metric-box">
                                <span class="metric-label">Complexity</span>
                                <span
                                  class="severity-chip"
                                  [class]="getSeverityClass($any(plan['development_plan'])['estimated_complexity'])"
                                >
                                  {{ $any(plan['development_plan'])['estimated_complexity'] }}
                                </span>
                              </div>
                            }
                            @if ($any(plan['development_plan'])?.['estimated_files_changed']) {
                              <div class="metric-box">
                                <span class="metric-label">Estimated Files</span>
                                <span class="metric-value">{{
                                  $any(plan['development_plan'])['estimated_files_changed']
                                }}</span>
                              </div>
                            }
                            @if ($any(plan['development_plan'])?.['upgrade_plan']?.['total_estimated_effort_hours']) {
                              <div class="metric-box">
                                <span class="metric-label">Estimated Effort</span>
                                <span class="metric-value"
                                  >{{
                                    $any(plan['development_plan'])['upgrade_plan']['total_estimated_effort_hours']
                                  }}h</span
                                >
                              </div>
                            }
                            @if ($any(plan['development_plan'])?.['risks']?.length) {
                              <div class="metric-box">
                                <span class="metric-label">Risks</span>
                                <span class="metric-value warn-text">{{
                                  $any(plan['development_plan'])['risks'].length
                                }}</span>
                              </div>
                            }
                          </div>

                          @if ($any(plan['development_plan'])?.['complexity_reasoning']) {
                            <p class="reasoning-text">{{ $any(plan['development_plan'])['complexity_reasoning'] }}</p>
                          }
                        </div>

                        <!-- ==================== REQUIREMENTS ==================== -->
                        @if ($any(plan['understanding'])?.['requirements']?.length) {
                          <div class="section">
                            <h3 class="section-title">
                              <mat-icon>assignment</mat-icon>
                              Requirements
                            </h3>
                            <ul class="detail-list">
                              @for (req of $any(plan['understanding'])['requirements']; track $index) {
                                <li>{{ req }}</li>
                              }
                            </ul>
                          </div>
                        }

                        <!-- ==================== ACCEPTANCE CRITERIA ==================== -->
                        @if ($any(plan['understanding'])?.['acceptance_criteria']?.length) {
                          <div class="section">
                            <h3 class="section-title">
                              <mat-icon>check_circle</mat-icon>
                              Acceptance Criteria
                            </h3>
                            <ul class="detail-list">
                              @for (ac of $any(plan['understanding'])['acceptance_criteria']; track $index) {
                                <li>{{ ac }}</li>
                              }
                            </ul>
                          </div>
                        }

                        <!-- ==================== SOURCE FILES ==================== -->
                        @if ($any(plan['source_files'])?.length) {
                          <div class="section">
                            <h3 class="section-title">
                              <mat-icon>source</mat-icon>
                              Source Files ({{ $any(plan['source_files']).length }})
                            </h3>
                            <div class="component-grid">
                              @for (file of $any(plan['source_files']); track $index) {
                                <div class="component-chip">
                                  <span class="comp-name mono">{{ file }}</span>
                                </div>
                              }
                            </div>
                          </div>
                        }

                        <!-- ==================== IMPLEMENTATION STEPS ==================== -->
                        @if ($any(plan['development_plan'])?.['implementation_steps']?.length) {
                          <div class="section">
                            <h3 class="section-title">
                              <mat-icon>checklist</mat-icon>
                              Implementation Steps
                            </h3>
                            <ol class="steps-list">
                              @for (step of $any(plan['development_plan'])['implementation_steps']; track $index) {
                                <li>
                                  @if (isString(step)) {
                                    {{ stripStepNumber(step) }}
                                  } @else {
                                    <strong>{{ step['description'] || step['step'] }}</strong>
                                    @if (step['details']) {
                                      <span class="muted"> — {{ step['details'] }}</span>
                                    }
                                  }
                                </li>
                              }
                            </ol>
                          </div>
                        }

                        <!-- ==================== AFFECTED COMPONENTS ==================== -->
                        @if ($any(plan['development_plan'])?.['affected_components']?.length) {
                          <div class="section">
                            <h3 class="section-title">
                              <mat-icon>widgets</mat-icon>
                              Affected Components ({{ $any(plan['development_plan'])['affected_components'].length }})
                            </h3>
                            <div class="component-grid">
                              @for (
                                comp of parseComponents($any(plan['development_plan'])['affected_components']);
                                track comp.id
                              ) {
                                <div class="component-chip">
                                  <span class="comp-container">{{ comp.container }}</span>
                                  <span class="comp-name">{{ comp.name }}</span>
                                  @if (comp.package) {
                                    <span class="comp-package">{{ comp.package }}</span>
                                  }
                                </div>
                              }
                            </div>
                          </div>
                        }

                        <!-- ==================== ALL AFFECTED FILES ==================== -->
                        @if (collectAffectedFiles(plan).length) {
                          <div class="section">
                            <h3 class="section-title">
                              <mat-icon>insert_drive_file</mat-icon>
                              All Affected Files ({{ collectAffectedFiles(plan).length }})
                            </h3>
                            <div class="affected-files">
                              @for (f of collectAffectedFiles(plan); track f) {
                                <div class="file-chip mono">{{ shortenPath(f) }}</div>
                              }
                            </div>
                          </div>
                        }

                        <!-- ==================== UPGRADE PLAN ==================== -->
                        @if ($any(plan['development_plan'])?.['upgrade_plan']) {
                          <div class="section">
                            <h3 class="section-title">
                              <mat-icon>upgrade</mat-icon>
                              Upgrade Plan
                              @if ($any(plan['development_plan'])['upgrade_plan']['framework']) {
                                <span class="title-detail">
                                  {{ $any(plan['development_plan'])['upgrade_plan']['framework'] }}
                                  {{ $any(plan['development_plan'])['upgrade_plan']['from_version'] }}
                                  → {{ $any(plan['development_plan'])['upgrade_plan']['to_version'] }}
                                </span>
                              }
                            </h3>

                            <!-- Pre-migration checks -->
                            @if ($any(plan['development_plan'])['upgrade_plan']['pre_migration_checks']?.length) {
                              <h4 class="subsection-title">Pre-Migration Checks</h4>
                              <ul class="check-list">
                                @for (
                                  check of $any(plan['development_plan'])['upgrade_plan']['pre_migration_checks'];
                                  track $index
                                ) {
                                  <li><mat-icon class="check-icon">check_circle_outline</mat-icon> {{ check }}</li>
                                }
                              </ul>
                            }

                            <!-- Migration Sequence -->
                            @if ($any(plan['development_plan'])['upgrade_plan']['migration_sequence']?.length) {
                              <h4 class="subsection-title">Migration Sequence</h4>
                              <mat-accordion class="migration-accordion">
                                @for (
                                  migration of $any(plan['development_plan'])['upgrade_plan']['migration_sequence'];
                                  track migration['rule_id'];
                                  let i = $index
                                ) {
                                  <mat-expansion-panel class="migration-panel">
                                    <mat-expansion-panel-header>
                                      <mat-panel-title class="migration-title">
                                        <span class="step-number">{{ i + 1 }}</span>
                                        <span>{{ migration['title'] }}</span>
                                      </mat-panel-title>
                                      <mat-panel-description class="migration-desc">
                                        <span class="severity-chip" [class]="getSeverityClass(migration['severity'])">
                                          {{ migration['severity'] }}
                                        </span>
                                        @if (migration['estimated_effort_minutes']) {
                                          <span class="effort-badge">{{
                                            formatMinutes(migration['estimated_effort_minutes'])
                                          }}</span>
                                        }
                                      </mat-panel-description>
                                    </mat-expansion-panel-header>

                                    <div class="migration-body">
                                      @if (migration['migration_steps']?.length) {
                                        <h5>Steps</h5>
                                        <ol class="migration-steps">
                                          @for (ms of migration['migration_steps']; track $index) {
                                            <li>{{ ms }}</li>
                                          }
                                        </ol>
                                      }
                                      @if (migration['schematic']) {
                                        <div class="schematic-box">
                                          <mat-icon>terminal</mat-icon>
                                          <code>{{ migration['schematic'] }}</code>
                                        </div>
                                      }
                                      @if (migration['affected_files']?.length) {
                                        <h5>Affected Files ({{ migration['affected_files'].length }})</h5>
                                        <div class="affected-files">
                                          @for (f of migration['affected_files']; track f) {
                                            <div class="file-chip mono">{{ shortenPath(f) }}</div>
                                          }
                                        </div>
                                      }
                                    </div>
                                  </mat-expansion-panel>
                                }
                              </mat-accordion>
                            }

                            <!-- Post-migration checks -->
                            @if ($any(plan['development_plan'])['upgrade_plan']['post_migration_checks']?.length) {
                              <h4 class="subsection-title">Post-Migration Checks</h4>
                              <ul class="check-list">
                                @for (
                                  check of $any(plan['development_plan'])['upgrade_plan']['post_migration_checks'];
                                  track $index
                                ) {
                                  <li><mat-icon class="check-icon">verified</mat-icon> {{ check }}</li>
                                }
                              </ul>
                            }

                            <!-- Verification Commands -->
                            @if ($any(plan['development_plan'])['upgrade_plan']['verification_commands']?.length) {
                              <h4 class="subsection-title">Verification Commands</h4>
                              <div class="commands-box">
                                @for (
                                  cmd of $any(plan['development_plan'])['upgrade_plan']['verification_commands'];
                                  track cmd
                                ) {
                                  <code class="command-line">$ {{ cmd }}</code>
                                }
                              </div>
                            }
                          </div>
                        }

                        <!-- ==================== TEST STRATEGY ==================== -->
                        @if ($any(plan['development_plan'])?.['test_strategy']) {
                          <div class="section">
                            <h3 class="section-title">
                              <mat-icon>science</mat-icon>
                              Test Strategy
                            </h3>
                            @if ($any(plan['development_plan'])['test_strategy']['unit_tests']?.length) {
                              <h4 class="subsection-title">Unit Tests</h4>
                              <ul class="detail-list">
                                @for (
                                  t of $any(plan['development_plan'])['test_strategy']['unit_tests'];
                                  track $index
                                ) {
                                  <li>{{ t }}</li>
                                }
                              </ul>
                            }
                            @if ($any(plan['development_plan'])['test_strategy']['integration_tests']?.length) {
                              <h4 class="subsection-title">Integration Tests</h4>
                              <ul class="detail-list">
                                @for (
                                  t of $any(plan['development_plan'])['test_strategy']['integration_tests'];
                                  track $index
                                ) {
                                  <li>{{ t }}</li>
                                }
                              </ul>
                            }
                            @if ($any(plan['development_plan'])['test_strategy']['similar_patterns']?.length) {
                              <h4 class="subsection-title">Similar Patterns</h4>
                              <div class="patterns-list">
                                @for (
                                  p of $any(plan['development_plan'])['test_strategy']['similar_patterns'];
                                  track $index
                                ) {
                                  <div class="pattern-chip">
                                    {{ isString(p) ? p : p['pattern'] || p['name'] }}
                                    @if (!isString(p) && p['description']) {
                                      <span class="muted"> — {{ p['description'] }}</span>
                                    }
                                  </div>
                                }
                              </div>
                            }
                          </div>
                        }

                        <!-- ==================== RISKS ==================== -->
                        @if ($any(plan['development_plan'])?.['risks']?.length) {
                          <div class="section">
                            <h3 class="section-title">
                              <mat-icon>warning_amber</mat-icon>
                              Risks
                            </h3>
                            <ul class="risks-list">
                              @for (risk of $any(plan['development_plan'])['risks']; track $index) {
                                <li>
                                  <mat-icon class="risk-icon">error_outline</mat-icon>
                                  {{ risk }}
                                </li>
                              }
                            </ul>
                          </div>
                        }

                        <!-- ==================== COLLAPSIBLE DETAILS ==================== -->
                        <mat-accordion class="details-accordion">
                          @if ($any(plan['development_plan'])?.['security_considerations']?.length) {
                            <mat-expansion-panel>
                              <mat-expansion-panel-header>
                                <mat-panel-title>
                                  <mat-icon class="panel-icon">security</mat-icon>
                                  Security ({{ $any(plan['development_plan'])['security_considerations'].length }})
                                </mat-panel-title>
                              </mat-expansion-panel-header>
                              <ul class="detail-list">
                                @for (item of $any(plan['development_plan'])['security_considerations']; track $index) {
                                  <li>{{ item }}</li>
                                }
                              </ul>
                            </mat-expansion-panel>
                          }
                          @if ($any(plan['development_plan'])?.['validation_strategy']?.length) {
                            <mat-expansion-panel>
                              <mat-expansion-panel-header>
                                <mat-panel-title>
                                  <mat-icon class="panel-icon">check_circle</mat-icon>
                                  Validation ({{ $any(plan['development_plan'])['validation_strategy'].length }})
                                </mat-panel-title>
                              </mat-expansion-panel-header>
                              <ul class="detail-list">
                                @for (item of $any(plan['development_plan'])['validation_strategy']; track $index) {
                                  <li>{{ item }}</li>
                                }
                              </ul>
                            </mat-expansion-panel>
                          }
                          @if ($any(plan['development_plan'])?.['error_handling']?.length) {
                            <mat-expansion-panel>
                              <mat-expansion-panel-header>
                                <mat-panel-title>
                                  <mat-icon class="panel-icon">error_outline</mat-icon>
                                  Error Handling ({{ $any(plan['development_plan'])['error_handling'].length }})
                                </mat-panel-title>
                              </mat-expansion-panel-header>
                              <ul class="detail-list">
                                @for (item of $any(plan['development_plan'])['error_handling']; track $index) {
                                  <li>{{ item }}</li>
                                }
                              </ul>
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
                              <div class="arch-context">
                                @if ($any(plan['development_plan'])['architecture_context']['style']) {
                                  <div class="arch-row">
                                    <span class="arch-label">Style</span>
                                    <span>{{ $any(plan['development_plan'])['architecture_context']['style'] }}</span>
                                  </div>
                                }
                                @if ($any(plan['development_plan'])['architecture_context']['layer_pattern']) {
                                  <div class="arch-row">
                                    <span class="arch-label">Layer Pattern</span>
                                    <span class="mono">{{
                                      $any(plan['development_plan'])['architecture_context']['layer_pattern']
                                    }}</span>
                                  </div>
                                }
                                @if ($any(plan['development_plan'])['architecture_context']['quality_grade']) {
                                  <div class="arch-row">
                                    <span class="arch-label">Quality Grade</span>
                                    <span
                                      class="severity-chip"
                                      [class]="
                                        getGradeClass(
                                          $any(plan['development_plan'])['architecture_context']['quality_grade']
                                        )
                                      "
                                    >
                                      {{ $any(plan['development_plan'])['architecture_context']['quality_grade'] }}
                                    </span>
                                  </div>
                                }
                                @if (
                                  $any(plan['development_plan'])['architecture_context']['layer_compliance']?.length
                                ) {
                                  <div class="arch-row">
                                    <span class="arch-label">Compliance</span>
                                    <span>{{
                                      $any(plan['development_plan'])['architecture_context']['layer_compliance'].join(
                                        ', '
                                      )
                                    }}</span>
                                  </div>
                                }
                              </div>
                            </mat-expansion-panel>
                          }

                          <!-- JIRA Context (Technical Notes - collapsible at bottom) -->
                          @if ($any(plan['understanding'])?.['technical_notes']) {
                            <mat-expansion-panel>
                              <mat-expansion-panel-header>
                                <mat-panel-title>
                                  <mat-icon class="panel-icon">article</mat-icon>
                                  JIRA Context
                                </mat-panel-title>
                              </mat-expansion-panel-header>
                              <div
                                class="jira-content"
                                [innerHTML]="cleanHtml($any(plan['understanding'])['technical_notes'])"
                              ></div>
                            </mat-expansion-panel>
                          }
                        </mat-accordion>
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
          <!-- TAB 3: Code Generation                                       -->
          <!-- ============================================================ -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">code</mat-icon>
              Code Generation ({{ reports?.codegen_reports?.length || 0 }})
            </ng-template>

            @if (reports?.codegen_reports?.length) {
              <mat-accordion class="report-accordion" multi>
                @for (report of reports!.codegen_reports; track $any(report['task_id'])) {
                  <mat-expansion-panel>
                    <mat-expansion-panel-header>
                      <mat-panel-title>
                        <mat-icon class="panel-icon">code</mat-icon>
                        <span class="mono">{{ report['task_id'] }}</span>
                      </mat-panel-title>
                      <mat-panel-description>
                        <span class="severity-chip" [class]="'status-' + report['status']">
                          {{ report['status'] }}
                        </span>
                        @if ($any(report['generated_files'])?.length) {
                          <span class="file-count-badge"> {{ $any(report['generated_files']).length }} files </span>
                        }
                      </mat-panel-description>
                    </mat-expansion-panel-header>

                    <div class="report-body">
                      <div class="toggle-row">
                        <button mat-button (click)="downloadReportJson(report)">
                          <mat-icon>download</mat-icon> Download
                        </button>
                        <button mat-button (click)="toggleRawJson('report_' + report['task_id'])">
                          <mat-icon>{{
                            showRawJson['report_' + $any(report['task_id'])] ? 'visibility' : 'data_object'
                          }}</mat-icon>
                          {{ showRawJson['report_' + $any(report['task_id'])] ? 'Structured View' : 'Raw JSON' }}
                        </button>
                      </div>

                      @if (showRawJson['report_' + $any(report['task_id'])]) {
                        <pre class="code-viewer">{{ report | json }}</pre>
                      } @else {
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
                                  <span
                                    >{{ $any(report['token_usage'])['total'] || report['token_usage'] }} tokens</span
                                  >
                                </div>
                              }
                            </div>
                          </mat-card-content>
                        </mat-card>

                        @if ($any(report['generated_files'])?.length) {
                          <div class="files-list">
                            @for (file of $any(report['generated_files']); track file['path']) {
                              <div
                                class="file-entry"
                                role="button"
                                tabindex="0"
                                (click)="toggleFile($any(report['task_id']) + ':' + file['path'])"
                                (keydown.enter)="toggleFile($any(report['task_id']) + ':' + file['path'])"
                                (keydown.space)="
                                  toggleFile($any(report['task_id']) + ':' + file['path']); $event.preventDefault()
                                "
                                [class.expanded]="expandedFiles[$any(report['task_id']) + ':' + file['path']]"
                              >
                                <div class="file-header">
                                  <mat-icon class="expand-icon">
                                    {{
                                      expandedFiles[$any(report['task_id']) + ':' + file['path']]
                                        ? 'expand_more'
                                        : 'chevron_right'
                                    }}
                                  </mat-icon>
                                  <span class="file-path mono">{{ file['path'] }}</span>
                                  <span class="severity-chip" [class]="'action-' + (file['action'] || 'modified')">
                                    {{ file['action'] || 'modified' }}
                                  </span>
                                  <span class="lang-badge">{{ getLanguage(file['path']) }}</span>
                                </div>
                                @if (expandedFiles[$any(report['task_id']) + ':' + file['path']] && file['diff']) {
                                  <div class="diff-viewer">
                                    @for (line of parseDiffLines(file['diff']); track $index) {
                                      <div [class]="'diff-line diff-line-' + line.type">{{ line.content }}</div>
                                    }
                                  </div>
                                }
                                @if (expandedFiles[$any(report['task_id']) + ':' + file['path']] && !file['diff']) {
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
                <span>No codegen reports found. Run the Implement phase to see results.</span>
              </div>
            }
          </mat-tab>

          <!-- ============================================================ -->
          <!-- TAB 4: Git Branches                                          -->
          <!-- ============================================================ -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">account_tree</mat-icon>
              Git Branches ({{ branches?.branches?.length || 0 }})
            </ng-template>

            @if (branchesLoading) {
              <div class="loading-center">
                <mat-spinner diameter="36"></mat-spinner>
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
                          <span class="severity-chip status-ready" matTooltip="Files changed vs main">
                            {{ branch.file_count }} files
                          </span>
                          @if (branch.has_report) {
                            <span
                              class="severity-chip status-completed"
                              matTooltip="View codegen report"
                              style="cursor:pointer"
                              (click)="goToReport(branch.task_id)"
                              role="button"
                              tabindex="0"
                              (keydown.enter)="goToReport(branch.task_id)"
                              (keydown.space)="goToReport(branch.task_id); $event.preventDefault()"
                            >
                              Has Report
                            </span>
                          }
                          <button
                            mat-icon-button
                            color="warn"
                            [matTooltip]="isRunning ? 'Pipeline is running' : 'Delete branch'"
                            [disabled]="isRunning"
                            (click)="deleteBranch(branch.task_id)"
                          >
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
  styles: [
    `
      /* Architecture grouped docs */
      .doc-groups {
        margin-top: 16px;
        display: flex;
        flex-direction: column;
        gap: 24px;
      }
      .doc-group-header {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 12px;
        cursor: pointer;
        border-radius: 10px;
        padding: 6px 8px;
        margin: -6px -8px 12px;
        transition: background 0.15s;
      }
      .doc-group-header:hover {
        background: var(--cg-gray-50, #f8f9fa);
      }
      .doc-group-chevron {
        color: var(--cg-gray-400);
        font-size: 22px;
        width: 22px;
        height: 22px;
        flex-shrink: 0;
      }
      .doc-group-icon-wrap {
        width: 44px;
        height: 44px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
      }
      .doc-group-icon-wrap .mat-icon {
        color: #fff;
        font-size: 22px;
        width: 22px;
        height: 22px;
      }
      .group-arc42 {
        background: linear-gradient(135deg, #0070ad, #12abdb);
      }
      .group-c4 {
        background: linear-gradient(135deg, #2b0a3d, #5b2d8e);
      }
      .group-quality {
        background: linear-gradient(135deg, #28a745, #20c997);
      }
      .group-other {
        background: linear-gradient(135deg, #6c757d, #adb5bd);
      }
      .doc-group-info {
        flex: 1;
      }
      .doc-group-title {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
        color: var(--cg-gray-900);
      }
      .doc-group-desc {
        margin: 2px 0 0;
        font-size: 12px;
        color: var(--cg-gray-500);
      }
      .doc-group-count {
        display: inline-block;
        margin-left: 6px;
        padding: 1px 8px;
        border-radius: 8px;
        background: var(--cg-gray-100);
        font-weight: 600;
        font-size: 11px;
      }
      .doc-group-files {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      .doc-file-card {
        background: #fff;
        border: 1px solid var(--cg-gray-100);
        border-radius: 10px;
        cursor: pointer;
        transition:
          border-color 0.15s,
          box-shadow 0.15s;
        overflow: hidden;
      }
      .doc-file-card:hover {
        border-color: var(--cg-gray-200);
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
      }
      .doc-file-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 14px;
      }
      .doc-file-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
        color: var(--cg-blue);
        flex-shrink: 0;
      }
      .doc-file-info {
        flex: 1;
        display: flex;
        flex-direction: column;
      }
      .doc-file-name {
        font-size: 13px;
        font-weight: 500;
        color: var(--cg-gray-900);
      }
      .doc-file-meta {
        font-size: 11px;
        color: var(--cg-gray-400);
      }
      .doc-expand-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
        color: var(--cg-gray-400);
      }
      .doc-preview {
        border-top: 1px solid var(--cg-gray-100);
      }
      .doc-preview .code-viewer {
        border-radius: 0 0 10px 10px;
        max-height: 400px;
      }
      .rendered-md {
        padding: 20px 24px;
        max-height: 500px;
        overflow: auto;
        font-size: 14px;
        line-height: 1.7;
        color: var(--cg-gray-900);
      }
      .rendered-md :is(h1, h2, h3, h4) {
        margin-top: 1.2em;
        margin-bottom: 0.4em;
        color: var(--cg-gray-900);
      }
      .rendered-md h1 {
        font-size: 20px;
        border-bottom: 1px solid var(--cg-gray-100);
        padding-bottom: 6px;
      }
      .rendered-md h2 {
        font-size: 17px;
      }
      .rendered-md h3 {
        font-size: 15px;
      }
      .rendered-md p {
        margin: 0.5em 0;
      }
      .rendered-md ul,
      .rendered-md ol {
        padding-left: 24px;
        margin: 0.5em 0;
      }
      .rendered-md li {
        margin: 2px 0;
      }
      .rendered-md code {
        background: var(--cg-gray-50);
        padding: 1px 5px;
        border-radius: 4px;
        font-size: 12px;
      }
      .rendered-md pre {
        background: var(--cg-dark);
        color: #eeffff;
        padding: 12px 16px;
        border-radius: 6px;
        overflow: auto;
        font-size: 12px;
      }
      .rendered-md pre code {
        background: none;
        padding: 0;
      }
      .rendered-md table {
        border-collapse: collapse;
        width: 100%;
        margin: 0.5em 0;
      }
      .rendered-md th,
      .rendered-md td {
        border: 1px solid var(--cg-gray-200);
        padding: 6px 10px;
        font-size: 13px;
        text-align: left;
      }
      .rendered-md th {
        background: var(--cg-gray-50);
        font-weight: 600;
      }

      .tab-icon {
        margin-right: 6px;
        font-size: 18px;
      }
      .report-accordion {
        margin-top: 16px;
      }
      .panel-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
        margin-right: 8px;
        color: var(--cg-blue);
      }
      .code-viewer {
        max-height: 500px;
        overflow: auto;
        background: var(--cg-dark);
        color: #eeffff;
        padding: 16px;
        border-radius: 8px;
        font-size: 12px;
        line-height: 1.6;
      }
      .tab-empty {
        padding: 32px 16px;
      }
      .doc-viewer {
        white-space: pre-wrap;
        word-wrap: break-word;
      }
      .file-size-badge {
        font-size: 11px;
        color: var(--cg-gray-500);
        font-family: monospace;
      }

      /* Plan body layout */
      .plan-body,
      .report-body {
        padding: 4px 0;
      }
      .toggle-row {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 4px;
      }
      .plan-summary-text {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 400px;
        margin-left: 8px;
      }
      .muted {
        color: var(--cg-gray-500);
        font-size: 13px;
      }

      /* Overview card */
      .overview-card {
        background: linear-gradient(135deg, rgba(18, 171, 219, 0.04) 0%, rgba(18, 171, 219, 0.01) 100%);
        border: 1px solid var(--cg-gray-200);
        border-left: 4px solid var(--cg-vibrant);
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
      }
      .overview-title {
        font-size: 18px;
        font-weight: 600;
        margin: 0 0 14px;
        color: var(--cg-gray-900);
        line-height: 1.4;
      }
      .metrics-row {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
        margin-bottom: 12px;
      }
      .metric-box {
        display: flex;
        flex-direction: column;
        gap: 4px;
        padding: 8px 14px;
        background: white;
        border: 1px solid var(--cg-gray-200);
        border-radius: 6px;
        min-width: 100px;
      }
      .metric-label {
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: var(--cg-gray-500);
        font-weight: 600;
      }
      .metric-value {
        font-size: 18px;
        font-weight: 700;
        color: var(--cg-gray-900);
      }
      .warn-text {
        color: var(--cg-error) !important;
      }
      .reasoning-text {
        font-size: 13px;
        color: var(--cg-gray-500);
        margin: 0;
        line-height: 1.5;
        font-style: italic;
      }

      /* Sections */
      .section {
        margin-bottom: 20px;
        padding-bottom: 16px;
        border-bottom: 1px solid var(--cg-gray-100);
      }
      .section:last-child {
        border-bottom: none;
      }
      .section-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 15px;
        font-weight: 600;
        margin: 0 0 12px;
        color: var(--cg-gray-900);
      }
      .section-title .mat-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
        color: var(--cg-blue);
      }
      .title-detail {
        font-size: 13px;
        font-weight: 400;
        color: var(--cg-gray-500);
        margin-left: 4px;
      }
      .subsection-title {
        font-size: 13px;
        font-weight: 600;
        margin: 14px 0 8px;
        color: var(--cg-gray-700);
      }

      /* Steps list */
      .steps-list {
        padding-left: 24px;
        margin: 0;
        counter-reset: steps;
      }
      .steps-list li {
        margin: 6px 0;
        font-size: 13px;
        line-height: 1.5;
        color: var(--cg-gray-700);
      }

      /* Component grid */
      .component-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }
      .component-chip {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 6px 12px;
        background: var(--cg-gray-50);
        border: 1px solid var(--cg-gray-200);
        border-radius: 6px;
        font-size: 12px;
      }
      .comp-container {
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: var(--cg-vibrant);
        font-weight: 600;
        padding: 1px 6px;
        background: rgba(18, 171, 219, 0.08);
        border-radius: 3px;
      }
      .comp-name {
        font-weight: 600;
        color: var(--cg-gray-900);
      }
      .comp-package {
        color: var(--cg-gray-400);
        font-family: monospace;
        font-size: 11px;
      }

      /* Severity / status chips */
      .severity-chip {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        text-transform: capitalize;
      }
      .severity-low,
      .severity-recommended {
        background: rgba(40, 167, 69, 0.1);
        color: var(--cg-success);
      }
      .severity-medium,
      .severity-deprecated {
        background: rgba(255, 193, 7, 0.15);
        color: #d4a017;
      }
      .severity-high,
      .severity-breaking {
        background: rgba(220, 53, 69, 0.1);
        color: var(--cg-error);
      }
      .grade-a {
        background: rgba(40, 167, 69, 0.1);
        color: var(--cg-success);
      }
      .grade-b {
        background: rgba(0, 112, 173, 0.1);
        color: var(--cg-blue);
      }
      .grade-c {
        background: rgba(255, 193, 7, 0.15);
        color: #d4a017;
      }
      .grade-d,
      .grade-f {
        background: rgba(220, 53, 69, 0.1);
        color: var(--cg-error);
      }

      /* Migration accordion */
      .migration-accordion {
        margin-top: 8px;
      }
      .migration-panel {
        margin-bottom: 4px !important;
      }
      .migration-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px !important;
      }
      .migration-desc {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .step-number {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 22px;
        height: 22px;
        border-radius: 50%;
        background: var(--cg-vibrant);
        color: white;
        font-size: 11px;
        font-weight: 700;
        flex-shrink: 0;
      }
      .effort-badge {
        font-size: 11px;
        color: var(--cg-gray-500);
        font-family: monospace;
      }
      .migration-body {
        padding: 4px 0;
      }
      .migration-body h5 {
        font-size: 12px;
        font-weight: 600;
        margin: 10px 0 6px;
        color: var(--cg-gray-700);
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }
      .migration-steps {
        padding-left: 20px;
        margin: 0;
      }
      .migration-steps li {
        font-size: 12px;
        margin: 3px 0;
        line-height: 1.5;
        color: var(--cg-gray-600);
      }
      .schematic-box {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        background: var(--cg-dark);
        border-radius: 6px;
        margin-top: 8px;
      }
      .schematic-box .mat-icon {
        color: var(--cg-vibrant);
        font-size: 16px;
        width: 16px;
        height: 16px;
      }
      .schematic-box code {
        color: #c3e88d;
        font-size: 12px;
      }
      .affected-files {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        margin-top: 4px;
      }
      .file-chip {
        font-size: 11px;
        padding: 2px 8px;
        background: var(--cg-gray-50);
        border: 1px solid var(--cg-gray-200);
        border-radius: 4px;
        color: var(--cg-gray-600);
      }

      /* Check lists */
      .check-list {
        list-style: none;
        padding: 0;
        margin: 0;
      }
      .check-list li {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        font-size: 13px;
        margin: 4px 0;
        color: var(--cg-gray-700);
      }
      .check-icon {
        font-size: 16px !important;
        width: 16px !important;
        height: 16px !important;
        color: var(--cg-success);
        margin-top: 2px;
        flex-shrink: 0;
      }
      .commands-box {
        background: var(--cg-dark);
        border-radius: 6px;
        padding: 12px 16px;
      }
      .command-line {
        display: block;
        color: #c3e88d;
        font-size: 12px;
        line-height: 1.8;
      }

      /* Detail lists */
      .detail-list {
        padding-left: 20px;
        margin: 0;
      }
      .detail-list li {
        font-size: 13px;
        margin: 4px 0;
        line-height: 1.5;
        color: var(--cg-gray-700);
      }
      .patterns-list {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      .pattern-chip {
        font-size: 13px;
        padding: 6px 12px;
        background: var(--cg-gray-50);
        border-radius: 6px;
        border: 1px solid var(--cg-gray-200);
      }

      /* Risks */
      .risks-list {
        list-style: none;
        padding: 0;
        margin: 0;
      }
      .risks-list li {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        font-size: 13px;
        margin: 6px 0;
        line-height: 1.5;
        color: var(--cg-gray-700);
      }
      .risk-icon {
        font-size: 16px !important;
        width: 16px !important;
        height: 16px !important;
        color: #d4a017;
        margin-top: 2px;
        flex-shrink: 0;
      }

      /* Collapsible details */
      .details-accordion {
        margin-top: 12px;
      }

      /* Architecture context */
      .arch-context {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .arch-row {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 13px;
      }
      .arch-label {
        font-weight: 600;
        color: var(--cg-gray-500);
        min-width: 120px;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }

      /* JIRA content */
      .jira-content {
        font-size: 13px;
        line-height: 1.6;
        color: var(--cg-gray-700);
        max-height: 400px;
        overflow-y: auto;
        padding: 8px;
      }
      .jira-content :is(h2, h3, h4) {
        font-size: 14px;
        font-weight: 600;
        margin: 12px 0 6px;
        color: var(--cg-gray-900);
      }
      .jira-content ul,
      .jira-content ol {
        padding-left: 20px;
        margin: 4px 0;
      }
      .jira-content li {
        margin: 2px 0;
      }
      .jira-content a {
        color: var(--cg-vibrant);
        text-decoration: none;
      }
      .jira-content a:hover {
        text-decoration: underline;
      }
      .jira-content p {
        margin: 6px 0;
      }
      .jira-content code,
      .jira-content tt {
        background: var(--cg-gray-100);
        padding: 1px 4px;
        border-radius: 3px;
        font-size: 12px;
      }

      /* Codegen report */
      .section-card {
        margin-bottom: 12px;
      }
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
      .meta-item .mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
      }
      .file-count-badge {
        margin-left: 8px;
        font-size: 12px;
        color: var(--cg-gray-500);
      }
      .files-list {
        margin-top: 12px;
      }
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
      .file-header:hover {
        background: var(--cg-gray-50);
      }
      .expand-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
        color: var(--cg-gray-500);
      }
      .file-path {
        flex: 1;
        font-size: 13px;
      }
      .lang-badge {
        font-size: 11px;
        padding: 2px 8px;
        border-radius: 10px;
        background: var(--cg-gray-100);
        color: var(--cg-gray-500);
        text-transform: uppercase;
        font-weight: 600;
      }
      .diff-viewer {
        border-radius: 0 0 8px 8px;
      }
      .diff-line {
        min-height: 19px;
        padding: 0 12px;
      }

      /* Download button in panel description */
      .dl-btn {
        width: 32px !important;
        height: 32px !important;
        line-height: 32px !important;
        margin-left: 4px;
      }
      .dl-btn .mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
        color: var(--cg-gray-500);
      }
      .dl-btn:hover .mat-icon {
        color: var(--cg-vibrant);
      }

      /* Branches */
      .branches-grid {
        display: grid;
        gap: 10px;
        margin-top: 16px;
      }
      .branch-card {
        margin: 0;
      }
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
      .branch-name {
        font-size: 14px;
      }
      .branch-actions {
        display: flex;
        align-items: center;
        gap: 8px;
      }
    `,
  ],
})
export class ReportsComponent implements OnInit, OnDestroy {
  private refreshTimer: ReturnType<typeof setInterval> | null = null;
  reports: ReportList | null = null;
  loading = true;
  isRunning = false;
  branches: BranchList | null = null;
  branchesLoading = false;
  branchesError = '';
  activeTabIndex = 0;
  showRawJson: Record<string, boolean> = {};
  expandedFiles: Record<string, boolean> = {};

  /** Lazy-loaded file contents keyed by knowledge-relative path */
  fileContents: Record<string, string> = {};
  fileLoading: Record<string, boolean> = {};

  /** Architecture doc grouping */
  docPreviewOpen: Record<string, boolean> = {};
  expandedDocGroups: Record<string, boolean> = {};
  docGroups: Record<string, Record<string, unknown>[]> = {};
  docGroupKeys: string[] = [];
  docGroupMeta: Record<string, { label: string; icon: string; description: string }> = {
    arc42: { label: 'Arc42 Documentation', icon: 'menu_book', description: 'Standardized architecture documentation' },
    c4: {
      label: 'C4 Model Diagrams',
      icon: 'architecture',
      description: 'Context, Container, Component & Deployment views',
    },
    quality: { label: 'Quality Reports', icon: 'verified', description: 'Architecture quality assessments & reviews' },
    other: { label: 'Other Documents', icon: 'description', description: 'Additional documentation artifacts' },
  };

  private mdCache: Record<string, SafeHtml> = {};
  private destroy$ = new Subject<void>();

  constructor(
    private api: ApiService,
    private notifSvc: NotificationService,
    private cdr: ChangeDetectorRef,
    private snackBar: MatSnackBar,
    private dialog: MatDialog,
    private sanitizer: DomSanitizer,
  ) {}

  ngOnInit(): void {
    this.notifSvc.notification$.pipe(takeUntil(this.destroy$)).subscribe((n) => {
      this.isRunning = n.state === 'running';
      this.cdr.markForCheck();
    });
    this.loadReports();
    this.refreshTimer = setInterval(() => this.loadReports(), 10000);
  }

  ngOnDestroy(): void {
    if (this.refreshTimer) clearInterval(this.refreshTimer);
    this.destroy$.next();
    this.destroy$.complete();
  }

  private loadReports(): void {
    this.api.getReports().subscribe({
      next: (r) => {
        this.reports = r;
        this.buildDocGroups(r.document_reports || []);
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.cdr.markForCheck();
      },
    });
  }

  /** Group document files by subdirectory (arc42, c4, quality, other) */
  private buildDocGroups(docs: Record<string, unknown>[]): void {
    const groups: Record<string, Record<string, unknown>[]> = {};
    const order = ['arc42', 'c4', 'quality'];
    for (const doc of docs) {
      const filePath = (doc['_file'] as string) || '';
      // Extract subfolder: "document/arc42/file.md" → "arc42"
      const parts = filePath.split('/');
      const group = parts.length >= 3 ? parts[1] : 'other';
      if (!groups[group]) groups[group] = [];
      groups[group].push(doc);
    }
    // Sort keys: known groups first, then alphabetical
    this.docGroupKeys = [
      ...order.filter((k) => groups[k]),
      ...Object.keys(groups)
        .filter((k) => !order.includes(k))
        .sort(),
    ];
    this.docGroups = groups;
  }

  toggleDocGroup(groupKey: string): void {
    this.expandedDocGroups[groupKey] = !this.expandedDocGroups[groupKey];
  }

  toggleDocPreview(filePath: string): void {
    this.docPreviewOpen[filePath] = !this.docPreviewOpen[filePath];
    if (this.docPreviewOpen[filePath]) {
      this.loadFileContent(filePath);
    }
  }

  /** Format doc filename for display: "01-introduction.md" → "Introduction" */
  formatDocName(name: string): string {
    return name
      .replace(/\.\w+$/, '') // remove extension
      .replace(/^\d+-/, '') // remove leading number prefix
      .replace(/^c4-/, 'C4 ') // "c4-context" → "C4 context"
      .replace(/[-_]/g, ' ') // dashes/underscores to spaces
      .replace(/\b\w/g, (c) => c.toUpperCase()); // capitalize words
  }

  onTabChange(event: MatTabChangeEvent): void {
    // Git Branches is the 4th tab (index 3)
    if (event.index === 3 && !this.branches) {
      this.loadBranches();
    }
  }

  loadBranches(): void {
    this.branchesLoading = true;
    this.branchesError = '';
    this.api.getBranches().subscribe({
      next: (b) => {
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

  /** Load file content on demand when a phase panel is opened */
  loadFileContent(path: string): void {
    if (this.fileContents[path] || this.fileLoading[path]) return;
    this.fileLoading[path] = true;
    this.api.getKnowledgeFile(path).subscribe({
      next: (data) => {
        this.fileContents[path] = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
        this.fileLoading[path] = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.fileContents[path] = '(Failed to load file)';
        this.fileLoading[path] = false;
        this.cdr.markForCheck();
      },
    });
  }

  renderMarkdown(text: string): SafeHtml {
    if (this.mdCache[text]) return this.mdCache[text];
    const html = marked.parse(text) as string;
    const safe = this.sanitizer.bypassSecurityTrustHtml(html);
    this.mdCache[text] = safe;
    return safe;
  }

  formatBytes(bytes: number): string {
    return formatBytesUtil(bytes);
  }

  /** Parse component ID strings into structured objects */
  parseComponents(ids: string[]): ParsedComponent[] {
    if (!ids?.length) return [];
    return ids.map((id) => {
      // "component.frontend.core.app_module" -> container=frontend, package=core, name=app_module
      const parts = id.replace(/^component\./, '').split('.');
      const container = parts[0] || '';
      const name = parts[parts.length - 1] || id;
      const pkg = parts.length > 2 ? parts.slice(1, -1).join('.') : '';
      return {
        id,
        name: name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
        container,
        package: pkg,
      };
    });
  }

  /** Strip leading step numbers like "1. " from implementation steps */
  stripStepNumber(step: string): string {
    return step.replace(/^\d+\.\s*/, '');
  }

  /** Convert raw JIRA HTML/text to safe HTML for rendering */
  cleanHtml(text: unknown): string {
    if (!text) return '';
    if (typeof text !== 'string') return typeof text === 'object' ? JSON.stringify(text, null, 2) : String(text);
    // Convert escaped newlines to <br> for plain text sections
    let html = text.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
    // Wrap comment blocks for visual separation
    html = html.replace(
      /\[Comment (\d+)\]/g,
      '<div style="margin-top:16px;padding-top:12px;border-top:1px solid var(--cg-gray-200)"><strong style="color:var(--cg-blue)">Comment $1</strong></div>',
    );
    // Clean up JIRA user references
    html = html.replace(/<a[^>]*class="user-hover"[^>]*>([^<]*)<\/a>/g, '<strong>$1</strong>');
    // Remove image emoticons
    html = html.replace(/<img[^>]*class="emoticon"[^>]*>/g, '');
    // Wrap in paragraph if not already
    if (!html.startsWith('<')) html = '<p>' + html + '</p>';
    return html;
  }

  /** Format minutes to human readable */
  formatMinutes(minutes: number): string {
    if (minutes < 60) return `${minutes}min`;
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return m > 0 ? `${h}h ${m}min` : `${h}h`;
  }

  /** Collect all unique affected files from migration rules */
  collectAffectedFiles(plan: Record<string, unknown>): string[] {
    const dp = plan['development_plan'] as Record<string, unknown> | undefined;
    if (!dp) return [];
    const up = dp['upgrade_plan'] as Record<string, unknown> | undefined;
    if (!up) return [];
    const seq = up['migration_sequence'] as Record<string, unknown>[] | undefined;
    if (!seq?.length) return [];
    const seen = new Set<string>();
    for (const rule of seq) {
      const files = rule['affected_files'] as string[] | undefined;
      if (files) {
        for (const f of files) seen.add(f);
      }
    }
    return [...seen].sort();
  }

  /** Shorten file paths for display */
  shortenPath(path: string): string {
    // Remove common prefix like "frontend\src\app\"
    return path.replace(/^frontend\\src\\app\\/, '').replace(/\\/g, '/');
  }

  getSeverityClass(level: string): string {
    const l = (level || '').toLowerCase();
    if (l === 'low' || l === 'recommended') return 'severity-chip severity-low';
    if (l === 'high' || l === 'breaking') return 'severity-chip severity-high';
    return 'severity-chip severity-medium';
  }

  getGradeClass(grade: string): string {
    const g = (grade || '').toUpperCase();
    if (g === 'A') return 'severity-chip grade-a';
    if (g === 'B') return 'severity-chip grade-b';
    if (g === 'C') return 'severity-chip grade-c';
    return 'severity-chip grade-d';
  }

  parseDiffLines(diff: string): DiffLine[] {
    return diff.split('\n').map((line) => {
      if (line.startsWith('+')) return { type: 'add' as const, content: line };
      if (line.startsWith('-')) return { type: 'del' as const, content: line };
      if (line.startsWith('@@')) return { type: 'info' as const, content: line };
      return { type: 'context' as const, content: line };
    });
  }

  getLanguage(filePath: string): string {
    if (!filePath) return '';
    const ext = filePath.split('.').pop()?.toLowerCase() || '';
    const map: Record<string, string> = {
      ts: 'TypeScript',
      js: 'JavaScript',
      java: 'Java',
      py: 'Python',
      html: 'HTML',
      css: 'CSS',
      scss: 'SCSS',
      json: 'JSON',
      xml: 'XML',
      yaml: 'YAML',
      yml: 'YAML',
      kt: 'Kotlin',
      sql: 'SQL',
      sh: 'Shell',
      md: 'Markdown',
      gradle: 'Gradle',
    };
    return map[ext] || ext.toUpperCase();
  }

  deleteBranch(taskId: string): void {
    const ref = this.dialog.open(ConfirmDialogComponent, {
      width: '420px',
      data: {
        title: 'Delete Branch',
        message: `Delete branch codegen/${taskId}? This cannot be undone.`,
        type: 'warn',
        icon: 'delete',
        confirmLabel: 'Delete',
      } as ConfirmDialogData,
    });
    ref.afterClosed().subscribe((confirmed) => {
      if (!confirmed) return;
      this.api.deleteBranch(taskId).subscribe({
        next: () => {
          if (this.branches) {
            this.branches.branches = this.branches.branches.filter((b) => b.task_id !== taskId);
          }
          this.snackBar.open(`Branch codegen/${taskId} deleted`, 'OK', { duration: 3000 });
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.snackBar.open(`Failed to delete branch: ${err.error?.detail || err.message}`, 'OK', { duration: 5000 });
        },
      });
    });
  }

  goToReport(_taskId: string): void {
    this.activeTabIndex = 2; // Code Generation tab
  }

  isString(val: unknown): boolean {
    return typeof val === 'string';
  }

  /** Download a knowledge file by its path */
  downloadFileContent(path: string, filename: string): void {
    this.api.getKnowledgeFile(path).subscribe({
      next: (data) => {
        const text = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
        this.triggerDownload(text, filename, filename.endsWith('.json') ? 'application/json' : 'text/plain');
      },
      error: () => {
        this.snackBar.open('Failed to download file', 'OK', { duration: 3000 });
      },
    });
  }

  /** Download a plan as JSON */
  downloadPlanJson(plan: Record<string, unknown>): void {
    const taskId = (plan['task_id'] as string) || 'plan';
    this.triggerDownload(JSON.stringify(plan, null, 2), `${taskId}_plan.json`, 'application/json');
  }

  /** Download a codegen report as JSON */
  downloadReportJson(report: Record<string, unknown>): void {
    const taskId = (report['task_id'] as string) || 'report';
    this.triggerDownload(JSON.stringify(report, null, 2), `${taskId}_report.json`, 'application/json');
  }

  private triggerDownload(content: string, filename: string, mime: string): void {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }
}
