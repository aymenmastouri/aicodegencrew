import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { ApiService, TaskSummary, TaskLifecycle, TaskPhaseSummary } from '../../services/api.service';
import { PhaseProgress } from '../../services/pipeline.service';
import { PipelineStepperComponent } from '../../shared/pipeline-stepper.component';

/** The 5 task-lifecycle phases in order. */
const LIFECYCLE_PHASES = ['triage', 'plan', 'implement', 'verify', 'deliver'] as const;

// ── Local triage interfaces (same as triage.component.ts) ──

interface TriageCustomerSummary {
  summary: string;
  impact_level: string;
  is_bug: boolean;
  workaround: string;
  eta_category: string;
}

interface TriageContextBoundary {
  category: string;
  boundary: string;
  severity: 'info' | 'caution' | 'blocking';
  source_facts: string[];
}

interface TriageAnticipatedQuestion {
  question: string;
  answer: string;
}

interface TriageDeveloperContext {
  big_picture: string;
  scope_boundary: string;
  classification_assessment: string;
  classification_confidence: number;
  affected_components: string[];
  context_boundaries: TriageContextBoundary[];
  architecture_notes: string;
  anticipated_questions: TriageAnticipatedQuestion[];
  linked_tasks: string[];
  relevant_dimensions?: { dimension: string; insight: string }[];
}

// ── Plan interfaces ──

interface PlanComponent {
  name: string;
  stereotype?: string;
  layer?: string;
  file_path?: string;
  change_type?: string;
  relevance_score?: number;
}

interface PlanDependency {
  name: string;
  current_version?: string;
  target_version?: string;
}

interface PlanStep {
  order?: number;
  description: string;
  component?: string;
  file_path?: string;
}

@Component({
  selector: 'app-tasks',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatChipsModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
    PipelineStepperComponent,
  ],
  template: `
    <!-- ═══════════════════ LIST VIEW ═══════════════════ -->
    @if (!selectedTaskId) {
      <div class="page-container">
        <div class="page-header">
          <mat-icon class="page-icon">assignment</mat-icon>
          <div>
            <h1 class="page-title">Task Lifecycle</h1>
            <p class="page-subtitle">Track every task's journey through the SDLC pipeline</p>
          </div>
        </div>

        @if (loading) {
          <div class="center-spinner">
            <mat-spinner diameter="40"></mat-spinner>
          </div>
        }

        @if (!loading && error) {
          <div class="error-banner">
            <mat-icon>error</mat-icon>
            {{ error }}
          </div>
        }

        @if (!loading && !error) {
          <!-- Search -->
          <mat-form-field appearance="outline" class="search-field">
            <mat-label>Search tasks</mat-label>
            <mat-icon matPrefix>search</mat-icon>
            <input matInput [(ngModel)]="searchQuery" placeholder="Filter by task ID..." />
          </mat-form-field>

          @if (filteredTasks.length === 0) {
            <div class="empty-state">
              <mat-icon class="empty-icon">inbox</mat-icon>
              <p>No tasks found. Run a triage or add task files to <code>inputs/tasks/</code>.</p>
            </div>
          }

          <div class="tasks-grid">
            @for (task of filteredTasks; track task.task_id) {
              <mat-card class="task-card" (click)="openTask(task.task_id)">
                <mat-card-content>
                  <div class="task-header">
                    <span class="task-id">{{ task.task_id }}</span>
                    <div class="task-badges">
                      @if (task.classification_type) {
                        <span class="type-chip" [class]="'type-' + task.classification_type">
                          <mat-icon class="chip-icon">{{ getClassIcon(task.classification_type) }}</mat-icon>
                          {{ task.classification_type }}
                        </span>
                      }
                      @if (task.risk_level) {
                        <span class="risk-chip" [class]="'risk-' + task.risk_level">
                          {{ task.risk_level }}
                        </span>
                      }
                    </div>
                  </div>
                  <div class="task-stepper">
                    <app-pipeline-stepper
                      [steps]="buildMiniSteps(task)"
                      [circleSize]="30"
                      [stepMinWidth]="60"
                      padding="4px 0 0"
                    ></app-pipeline-stepper>
                  </div>
                  @if (task.last_activity) {
                    <div class="task-time">
                      <mat-icon class="time-icon">schedule</mat-icon>
                      {{ formatTime(task.last_activity) }}
                    </div>
                  }
                </mat-card-content>
              </mat-card>
            }
          </div>
        }
      </div>
    }

    <!-- ═══════════════════ DETAIL VIEW ═══════════════════ -->
    @if (selectedTaskId) {
      <div class="page-container">
        <!-- Header -->
        <div class="detail-header">
          <button mat-icon-button (click)="goBack()" matTooltip="Back to task list">
            <mat-icon>arrow_back</mat-icon>
          </button>
          <mat-icon class="page-icon">assignment</mat-icon>
          <h1 class="page-title">{{ selectedTaskId }}</h1>
          @if (lifecycle) {
            @if (getClassificationType()) {
              <span class="type-chip" [class]="'type-' + getClassificationType()">
                <mat-icon class="chip-icon">{{ getClassIcon(getClassificationType()!) }}</mat-icon>
                {{ getClassificationType() }}
              </span>
            }
            @if (getRiskLevel()) {
              <span class="risk-chip" [class]="'risk-' + getRiskLevel()">
                {{ getRiskLevel() }}
              </span>
            }
          }
        </div>

        @if (detailLoading) {
          <div class="center-spinner">
            <mat-spinner diameter="40"></mat-spinner>
          </div>
        }

        @if (detailError) {
          <div class="error-banner">
            <mat-icon>error</mat-icon>
            {{ detailError }}
          </div>
        }

        @if (lifecycle) {
          <!-- Pipeline Stepper -->
          <div class="lifecycle-stepper">
            <app-pipeline-stepper
              [steps]="lifecycleSteps"
              [circleSize]="42"
              [stepMinWidth]="100"
            ></app-pipeline-stepper>
          </div>

          <!-- Phase Expansion Panels -->
          <mat-accordion multi>
            <!-- ──── TRIAGE ──── -->
            <mat-expansion-panel [expanded]="isFirstCompleted('triage')">
              <mat-expansion-panel-header>
                <mat-panel-title>
                  <mat-icon class="panel-icon">troubleshoot</mat-icon>
                  Triage
                </mat-panel-title>
                <mat-panel-description>
                  <span class="status-chip" [class]="'st-' + phaseStatus('triage')">
                    {{ phaseStatus('triage') }}
                  </span>
                </mat-panel-description>
              </mat-expansion-panel-header>

              @if (phaseStatus('triage') === 'not_started') {
                <p class="empty-hint">Triage has not been run for this task yet.</p>
              } @else {
                @if (triageCustomerSummary) {
                  <h3 class="section-title">Customer Summary</h3>
                  <div class="summary-grid">
                    <div class="summary-item">
                      <span class="summary-label">Impact</span>
                      <span class="impact-badge" [class]="'impact-' + triageCustomerSummary.impact_level">
                        {{ triageCustomerSummary.impact_level }}
                      </span>
                    </div>
                    <div class="summary-item">
                      <span class="summary-label">Type</span>
                      <span>{{ triageCustomerSummary.is_bug ? 'Bug' : 'Enhancement / Task' }}</span>
                    </div>
                    <div class="summary-item">
                      <span class="summary-label">Timeline</span>
                      <span>{{ triageCustomerSummary.eta_category || 'unknown' }}</span>
                    </div>
                  </div>
                  <p class="summary-text">{{ triageCustomerSummary.summary }}</p>
                  @if (triageCustomerSummary.workaround) {
                    <div class="workaround-box">
                      <strong>Workaround:</strong> {{ triageCustomerSummary.workaround }}
                    </div>
                  }
                }

                @if (triageDeveloperContext) {
                  <h3 class="section-title">Developer Context</h3>

                  <div class="context-section">
                    <h4>Big Picture</h4>
                    <p>{{ triageDeveloperContext.big_picture }}</p>
                  </div>

                  <div class="context-section">
                    <h4>Scope Boundary</h4>
                    <p>{{ triageDeveloperContext.scope_boundary }}</p>
                  </div>

                  @if (triageDeveloperContext.architecture_notes) {
                    <div class="context-section">
                      <h4>Architecture Walkthrough</h4>
                      <p>{{ triageDeveloperContext.architecture_notes }}</p>
                    </div>
                  }

                  @if (triageDeveloperContext.anticipated_questions?.length) {
                    <div class="context-section">
                      <h4>Anticipated Questions</h4>
                      <div class="questions-list">
                        @for (q of triageDeveloperContext.anticipated_questions; track q.question) {
                          <div class="question-item">
                            <div class="question-text">{{ q.question }}</div>
                            <div class="answer-text">{{ q.answer }}</div>
                          </div>
                        }
                      </div>
                    </div>
                  }

                  @if (triageDeveloperContext.context_boundaries?.length) {
                    <div class="context-section">
                      <h4>Context Boundaries</h4>
                      <div class="boundaries-list">
                        @for (b of triageDeveloperContext.context_boundaries; track b.category) {
                          <div class="boundary-item" [class]="'severity-' + b.severity">
                            <div class="boundary-header">
                              <span class="severity-badge" [class]="'sev-' + b.severity">
                                {{ b.severity.toUpperCase() }}
                              </span>
                              <span class="boundary-category">{{ formatCategory(b.category) }}</span>
                            </div>
                            <div class="boundary-text">{{ b.boundary }}</div>
                            @if (b.source_facts?.length) {
                              <div class="boundary-sources">
                                @for (s of b.source_facts; track s) {
                                  <span class="source-chip">{{ s }}</span>
                                }
                              </div>
                            }
                          </div>
                        }
                      </div>
                    </div>
                  }

                  @if (triageDeveloperContext.affected_components?.length) {
                    <div class="context-section">
                      <h4>Affected Components</h4>
                      <ul class="component-list">
                        @for (c of triageDeveloperContext.affected_components; track c) {
                          <li>{{ c }}</li>
                        }
                      </ul>
                    </div>
                  }
                }
              }
            </mat-expansion-panel>

            <!-- ──── PLAN ──── -->
            <mat-expansion-panel [expanded]="isFirstCompleted('plan')">
              <mat-expansion-panel-header>
                <mat-panel-title>
                  <mat-icon class="panel-icon">architecture</mat-icon>
                  Plan
                </mat-panel-title>
                <mat-panel-description>
                  <span class="status-chip" [class]="'st-' + phaseStatus('plan')">
                    {{ phaseStatus('plan') }}
                  </span>
                </mat-panel-description>
              </mat-expansion-panel-header>

              @if (phaseStatus('plan') === 'not_started') {
                <p class="empty-hint">Plan has not been generated for this task yet.</p>
              } @else {
                @if (planComponents.length) {
                  <h3 class="section-title">Affected Components</h3>
                  <div class="plan-table-wrap">
                    <table class="plan-table">
                      <thead>
                        <tr>
                          <th>Component</th>
                          <th>Layer</th>
                          <th>Change</th>
                          <th>File</th>
                        </tr>
                      </thead>
                      <tbody>
                        @for (c of planComponents; track c.name) {
                          <tr>
                            <td class="col-name">{{ c.name }}</td>
                            <td>{{ c.layer || '-' }}</td>
                            <td>
                              <span class="change-chip" [class]="'change-' + (c.change_type || 'modify')">
                                {{ c.change_type || 'modify' }}
                              </span>
                            </td>
                            <td class="col-path"><code>{{ c.file_path || '-' }}</code></td>
                          </tr>
                        }
                      </tbody>
                    </table>
                  </div>
                }

                @if (planSteps.length) {
                  <h3 class="section-title">Implementation Steps</h3>
                  <ol class="steps-list">
                    @for (step of planSteps; track step.description) {
                      <li>
                        {{ step.description }}
                        @if (step.file_path) {
                          <code class="step-file">{{ step.file_path }}</code>
                        }
                      </li>
                    }
                  </ol>
                }

                @if (planDependencies.length) {
                  <h3 class="section-title">Dependencies</h3>
                  <div class="plan-table-wrap">
                    <table class="plan-table">
                      <thead>
                        <tr>
                          <th>Package</th>
                          <th>Current</th>
                          <th>Target</th>
                        </tr>
                      </thead>
                      <tbody>
                        @for (d of planDependencies; track d.name) {
                          <tr>
                            <td class="col-name">{{ d.name }}</td>
                            <td>{{ d.current_version || '?' }}</td>
                            <td>{{ d.target_version || '?' }}</td>
                          </tr>
                        }
                      </tbody>
                    </table>
                  </div>
                }

                @if (planRisks.length) {
                  <h3 class="section-title">Risks</h3>
                  <ul class="risk-list">
                    @for (r of planRisks; track r) {
                      <li>{{ r }}</li>
                    }
                  </ul>
                }
              }
            </mat-expansion-panel>

            <!-- ──── IMPLEMENT ──── -->
            <mat-expansion-panel [expanded]="isFirstCompleted('implement')">
              <mat-expansion-panel-header>
                <mat-panel-title>
                  <mat-icon class="panel-icon">code</mat-icon>
                  Implement
                </mat-panel-title>
                <mat-panel-description>
                  <span class="status-chip" [class]="'st-' + phaseStatus('implement')">
                    {{ phaseStatus('implement') }}
                  </span>
                </mat-panel-description>
              </mat-expansion-panel-header>

              @if (phaseStatus('implement') === 'not_started') {
                <p class="empty-hint">Implementation has not started for this task yet.</p>
              } @else {
                @if (implementBranch) {
                  <div class="impl-meta">
                    <mat-icon class="meta-icon">fork_right</mat-icon>
                    Branch: <code>{{ implementBranch }}</code>
                  </div>
                }
                @if (implementFiles.length) {
                  <h3 class="section-title">Files Written</h3>
                  <ul class="file-list">
                    @for (f of implementFiles; track f) {
                      <li><code>{{ f }}</code></li>
                    }
                  </ul>
                }
                @if (implementBuildStatus) {
                  <div class="impl-meta">
                    <mat-icon class="meta-icon" [class]="implementBuildStatus === 'success' ? 'text-success' : 'text-error'">
                      {{ implementBuildStatus === 'success' ? 'check_circle' : 'error' }}
                    </mat-icon>
                    Build: {{ implementBuildStatus }}
                  </div>
                }
              }
            </mat-expansion-panel>

            <!-- ──── VERIFY ──── -->
            <mat-expansion-panel [expanded]="isFirstCompleted('verify')">
              <mat-expansion-panel-header>
                <mat-panel-title>
                  <mat-icon class="panel-icon">verified</mat-icon>
                  Verify
                </mat-panel-title>
                <mat-panel-description>
                  <span class="status-chip" [class]="'st-' + phaseStatus('verify')">
                    {{ phaseStatus('verify') }}
                  </span>
                </mat-panel-description>
              </mat-expansion-panel-header>

              @if (phaseStatus('verify') === 'not_started') {
                <p class="empty-hint">Verification has not been executed for this task yet.</p>
              } @else {
                <pre class="phase-json">{{ lifecycle!.phases['verify']?.data | json }}</pre>
              }
            </mat-expansion-panel>

            <!-- ──── DELIVER ──── -->
            <mat-expansion-panel [expanded]="isFirstCompleted('deliver')">
              <mat-expansion-panel-header>
                <mat-panel-title>
                  <mat-icon class="panel-icon">local_shipping</mat-icon>
                  Deliver
                </mat-panel-title>
                <mat-panel-description>
                  <span class="status-chip" [class]="'st-' + phaseStatus('deliver')">
                    {{ phaseStatus('deliver') }}
                  </span>
                </mat-panel-description>
              </mat-expansion-panel-header>

              @if (phaseStatus('deliver') === 'not_started') {
                <p class="empty-hint">Delivery has not been executed for this task yet.</p>
              } @else {
                <pre class="phase-json">{{ lifecycle!.phases['deliver']?.data | json }}</pre>
              }
            </mat-expansion-panel>
          </mat-accordion>
        }
      </div>
    }
  `,
  styles: [`
    /* ── Search ── */
    .search-field { width: 100%; margin-bottom: 16px; }

    /* ── Empty state ── */
    .empty-state {
      text-align: center; padding: 48px 20px; color: var(--cg-gray-400);
    }
    .empty-icon { font-size: 48px; width: 48px; height: 48px; margin-bottom: 12px; }
    .empty-state code { padding: 2px 6px; background: var(--cg-gray-100); border-radius: 4px; font-size: 13px; }

    /* ── Task card grid ── */
    .tasks-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
      gap: 16px;
    }
    .task-card {
      cursor: pointer;
      transition: box-shadow 0.15s, transform 0.15s;
    }
    .task-card:hover {
      box-shadow: 0 4px 16px rgba(0,0,0,0.1);
      transform: translateY(-2px);
    }
    .task-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 8px;
    }
    .task-id { font-weight: 700; font-size: 15px; }
    .task-badges { display: flex; gap: 6px; align-items: center; }
    .task-stepper { margin: 8px -4px 4px; }
    .task-time {
      display: flex; align-items: center; gap: 4px;
      font-size: 12px; color: var(--cg-gray-400); margin-top: 6px;
    }
    .time-icon { font-size: 14px; width: 14px; height: 14px; }

    /* ── Type & risk chips ── */
    .type-chip, .risk-chip {
      display: inline-flex; align-items: center; gap: 4px;
      padding: 2px 10px; border-radius: 12px;
      font-size: 12px; font-weight: 600; text-transform: capitalize;
    }
    .chip-icon { font-size: 14px; width: 14px; height: 14px; }
    .type-bug { background: rgba(220,53,69,0.1); color: #dc3545; }
    .type-feature { background: rgba(0,112,173,0.1); color: #0070ad; }
    .type-refactor { background: rgba(156,39,176,0.1); color: #9c27b0; }
    .type-investigation { background: rgba(245,124,0,0.1); color: #f57c00; }
    .risk-chip { background: var(--cg-gray-100); }
    .risk-low { background: rgba(40,167,69,0.1); color: #28a745; }
    .risk-medium { background: rgba(245,124,0,0.1); color: #f57c00; }
    .risk-high { background: rgba(220,53,69,0.1); color: #dc3545; }
    .risk-critical { background: rgba(156,39,176,0.1); color: #9c27b0; }

    /* ── Detail header ── */
    .detail-header {
      display: flex; align-items: center; gap: 12px; margin-bottom: 20px;
    }
    .detail-header .page-title { margin: 0; }

    /* ── Lifecycle stepper ── */
    .lifecycle-stepper {
      background: #fff; border-radius: 12px; padding: 12px 16px;
      margin-bottom: 20px; border: 1px solid var(--cg-gray-100);
    }

    /* ── Expansion panels ── */
    .panel-icon { margin-right: 8px; color: var(--cg-blue, #0070ad); }

    .status-chip {
      padding: 2px 10px; border-radius: 10px;
      font-size: 11px; font-weight: 600; text-transform: capitalize;
    }
    .st-completed { background: rgba(40,167,69,0.1); color: #28a745; }
    .st-not_started { background: var(--cg-gray-100); color: var(--cg-gray-400); }
    .st-running { background: rgba(0,112,173,0.1); color: #0070ad; }
    .st-failed { background: rgba(220,53,69,0.1); color: #dc3545; }

    .empty-hint { color: var(--cg-gray-400); font-style: italic; }

    /* ── Triage sections ── */
    .section-title {
      font-size: 15px; font-weight: 600; margin: 20px 0 10px;
      padding-bottom: 6px; border-bottom: 1px solid var(--cg-gray-100);
    }
    .section-title:first-child { margin-top: 0; }

    .summary-grid {
      display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 12px;
    }
    .summary-item { display: flex; align-items: center; gap: 8px; }
    .summary-label { font-weight: 500; color: var(--cg-gray-500); font-size: 13px; }
    .impact-badge {
      padding: 2px 10px; border-radius: 10px;
      font-size: 12px; font-weight: 600; text-transform: capitalize;
    }
    .impact-low { background: rgba(40,167,69,0.1); color: #28a745; }
    .impact-medium { background: rgba(245,124,0,0.1); color: #f57c00; }
    .impact-high { background: rgba(220,53,69,0.1); color: #dc3545; }
    .impact-critical { background: rgba(156,39,176,0.1); color: #9c27b0; }
    .summary-text { line-height: 1.6; margin-top: 8px; }
    .workaround-box {
      margin-top: 12px; padding: 12px; background: var(--cg-gray-50); border-radius: 8px;
    }

    .context-section { margin-bottom: 16px; }
    .context-section h4 { font-size: 14px; font-weight: 500; margin: 0 0 6px; }
    .context-section p { margin: 0; line-height: 1.6; }

    .questions-list { display: flex; flex-direction: column; gap: 10px; }
    .question-item {
      padding: 10px 14px; border-radius: 8px;
      background: var(--cg-gray-50); border-left: 3px solid var(--cg-blue, #0070ad);
    }
    .question-text { font-weight: 600; font-size: 13px; color: var(--cg-gray-700); margin-bottom: 4px; }
    .question-text::before { content: 'Q: '; color: var(--cg-blue, #0070ad); }
    .answer-text { font-size: 13px; line-height: 1.5; color: var(--cg-gray-600); }
    .answer-text::before { content: 'A: '; font-weight: 600; color: var(--cg-gray-500); }

    .boundaries-list { display: flex; flex-direction: column; gap: 10px; }
    .boundary-item {
      padding: 10px 14px; border-radius: 8px;
      background: var(--cg-gray-50); border-left: 3px solid var(--cg-blue, #0070ad);
    }
    .boundary-item.severity-caution { border-left-color: #f57c00; background: rgba(245,124,0,0.03); }
    .boundary-item.severity-blocking { border-left-color: #dc3545; background: rgba(220,53,69,0.03); }
    .boundary-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
    .severity-badge {
      padding: 1px 8px; border-radius: 8px;
      font-size: 10px; font-weight: 700; letter-spacing: 0.5px;
    }
    .sev-info { background: rgba(0,112,173,0.1); color: #0070ad; }
    .sev-caution { background: rgba(245,124,0,0.1); color: #f57c00; }
    .sev-blocking { background: rgba(220,53,69,0.1); color: #dc3545; }
    .boundary-category { font-weight: 600; font-size: 13px; }
    .boundary-text { font-size: 13px; line-height: 1.5; margin-bottom: 6px; }
    .boundary-sources { display: flex; flex-wrap: wrap; gap: 4px; }
    .source-chip {
      padding: 1px 6px; border-radius: 6px; font-size: 10px;
      background: var(--cg-gray-100); color: var(--cg-gray-500); font-family: monospace;
    }

    .component-list { padding-left: 20px; margin: 0; }
    .component-list li { padding: 2px 0; }

    /* ── Plan sections ── */
    .plan-table-wrap { overflow-x: auto; }
    .plan-table {
      width: 100%; border-collapse: collapse; font-size: 13px;
    }
    .plan-table th {
      text-align: left; padding: 8px 12px; font-weight: 600;
      background: var(--cg-gray-50); border-bottom: 2px solid var(--cg-gray-200);
    }
    .plan-table td {
      padding: 8px 12px; border-bottom: 1px solid var(--cg-gray-100);
    }
    .col-name { font-weight: 500; }
    .col-path code { font-size: 12px; color: var(--cg-gray-500); }

    .change-chip {
      padding: 1px 8px; border-radius: 8px; font-size: 11px; font-weight: 600;
    }
    .change-modify { background: rgba(0,112,173,0.1); color: #0070ad; }
    .change-add { background: rgba(40,167,69,0.1); color: #28a745; }
    .change-delete { background: rgba(220,53,69,0.1); color: #dc3545; }

    .steps-list { padding-left: 20px; }
    .steps-list li { margin-bottom: 8px; line-height: 1.5; }
    .step-file {
      display: inline-block; margin-left: 6px;
      padding: 1px 6px; background: var(--cg-gray-50); border-radius: 4px; font-size: 12px;
    }

    .risk-list { padding-left: 20px; }
    .risk-list li { margin-bottom: 6px; line-height: 1.5; }

    /* ── Implement sections ── */
    .impl-meta {
      display: flex; align-items: center; gap: 6px;
      margin-bottom: 10px; font-size: 14px;
    }
    .meta-icon { font-size: 18px; width: 18px; height: 18px; }
    .text-success { color: #28a745; }
    .text-error { color: #dc3545; }
    .file-list { padding-left: 20px; margin: 0; }
    .file-list li { padding: 2px 0; }
    .file-list code { font-size: 13px; }

    /* ── Generic phase JSON ── */
    .phase-json {
      font-size: 12px; padding: 12px; background: var(--cg-gray-50);
      border-radius: 8px; overflow: auto; max-height: 400px;
      white-space: pre-wrap; word-break: break-all;
    }

    /* ── Shared ── */
    .center-spinner { display: flex; justify-content: center; padding: 40px; }
    .error-banner {
      display: flex; align-items: center; gap: 8px;
      padding: 12px 16px; border-radius: 8px;
      background: rgba(220,53,69,0.06); color: var(--cg-error, #dc3545);
      margin-bottom: 16px;
    }
  `],
})
export class TasksComponent implements OnInit {
  // ── List view state ──
  tasks: TaskSummary[] = [];
  searchQuery = '';
  loading = false;
  error = '';

  // ── Detail view state ──
  selectedTaskId: string | null = null;
  lifecycle: TaskLifecycle | null = null;
  lifecycleSteps: PhaseProgress[] = [];
  detailLoading = false;
  detailError = '';

  // ── Parsed triage data ──
  triageCustomerSummary: TriageCustomerSummary | null = null;
  triageDeveloperContext: TriageDeveloperContext | null = null;

  // ── Parsed plan data ──
  planComponents: PlanComponent[] = [];
  planSteps: PlanStep[] = [];
  planDependencies: PlanDependency[] = [];
  planRisks: string[] = [];

  // ── Parsed implement data ──
  implementFiles: string[] = [];
  implementBranch = '';
  implementBuildStatus = '';

  constructor(
    private api: ApiService,
    private route: ActivatedRoute,
    private router: Router,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      const taskId = params.get('taskId');
      if (taskId) {
        this.selectedTaskId = taskId;
        this.loadLifecycle(taskId);
      } else {
        this.selectedTaskId = null;
        this.loadTasks();
      }
    });
  }

  // ── List view ──

  get filteredTasks(): TaskSummary[] {
    if (!this.searchQuery) return this.tasks;
    const q = this.searchQuery.toLowerCase();
    return this.tasks.filter(t =>
      t.task_id.toLowerCase().includes(q) ||
      (t.classification_type || '').toLowerCase().includes(q)
    );
  }

  loadTasks(): void {
    this.loading = true;
    this.error = '';
    this.api.getTasks().subscribe({
      next: res => {
        this.tasks = res.tasks;
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: err => {
        this.error = err?.error?.detail || 'Failed to load tasks';
        this.loading = false;
        this.cdr.markForCheck();
      },
    });
  }

  openTask(taskId: string): void {
    this.router.navigate(['/tasks', taskId]);
  }

  buildMiniSteps(task: TaskSummary): PhaseProgress[] {
    return LIFECYCLE_PHASES.map(phase => ({
      phase_id: phase,
      name: phase.charAt(0).toUpperCase() + phase.slice(1),
      status: task.phase_status[phase] || 'not_started',
    }));
  }

  formatTime(iso: string): string {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
      return iso;
    }
  }

  // ── Detail view ──

  loadLifecycle(taskId: string): void {
    this.detailLoading = true;
    this.detailError = '';
    this.lifecycle = null;
    this.api.getTaskLifecycle(taskId).subscribe({
      next: res => {
        this.lifecycle = res;
        this.lifecycleSteps = this.buildLifecycleSteps(res);
        this.parseTriage(res.phases['triage']);
        this.parsePlan(res.phases['plan']);
        this.parseImplement(res.phases['implement']);
        this.detailLoading = false;
        this.cdr.markForCheck();
      },
      error: err => {
        this.detailError = err?.error?.detail || 'Failed to load task lifecycle';
        this.detailLoading = false;
        this.cdr.markForCheck();
      },
    });
  }

  goBack(): void {
    this.router.navigate(['/tasks']);
  }

  buildLifecycleSteps(lc: TaskLifecycle): PhaseProgress[] {
    return LIFECYCLE_PHASES.map(phase => ({
      phase_id: phase,
      name: phase.charAt(0).toUpperCase() + phase.slice(1),
      status: lc.phases[phase]?.status || 'not_started',
    }));
  }

  phaseStatus(phase: string): string {
    return this.lifecycle?.phases[phase]?.status || 'not_started';
  }

  isFirstCompleted(phase: string): boolean {
    if (!this.lifecycle) return false;
    // Expand the first completed phase
    for (const p of LIFECYCLE_PHASES) {
      if (this.lifecycle.phases[p]?.status === 'completed') {
        return p === phase;
      }
    }
    return false;
  }

  getClassificationType(): string | null {
    const triage = this.lifecycle?.phases['triage']?.data;
    if (!triage) return null;
    return (triage['classification'] as Record<string, unknown>)?.['type'] as string || null;
  }

  getRiskLevel(): string | null {
    const triage = this.lifecycle?.phases['triage']?.data;
    if (!triage) return null;
    const findings = triage['findings'] as Record<string, unknown>;
    if (!findings) return null;
    return (findings['risk_assessment'] as Record<string, unknown>)?.['risk_level'] as string || null;
  }

  // ── Phase parsers ──

  private parseTriage(phase: TaskPhaseSummary | undefined): void {
    this.triageCustomerSummary = null;
    this.triageDeveloperContext = null;
    if (!phase || phase.status !== 'completed' || !phase.data) return;

    const data = phase.data;
    this.triageCustomerSummary = (data['customer_summary'] as TriageCustomerSummary) || null;
    this.triageDeveloperContext = (data['developer_context'] || data['developer_brief']) as TriageDeveloperContext || null;

    // Backward compat: map old relevant_dimensions -> context_boundaries
    if (this.triageDeveloperContext && !this.triageDeveloperContext.context_boundaries?.length && this.triageDeveloperContext.relevant_dimensions?.length) {
      this.triageDeveloperContext.context_boundaries = this.triageDeveloperContext.relevant_dimensions.map(dim => ({
        category: 'technology_constraint',
        boundary: dim.insight,
        severity: 'info' as const,
        source_facts: [dim.dimension],
      }));
    }
  }

  private parsePlan(phase: TaskPhaseSummary | undefined): void {
    this.planComponents = [];
    this.planSteps = [];
    this.planDependencies = [];
    this.planRisks = [];
    if (!phase || phase.status !== 'completed' || !phase.data) return;

    const data = phase.data;
    const devPlan = (data['development_plan'] || {}) as Record<string, unknown>;
    this.planComponents = (devPlan['affected_components'] as PlanComponent[]) || [];
    this.planSteps = (devPlan['implementation_steps'] as PlanStep[]) || [];
    this.planDependencies = (devPlan['dependencies'] as PlanDependency[]) || [];
    this.planRisks = (devPlan['risks'] as string[]) || [];
  }

  private parseImplement(phase: TaskPhaseSummary | undefined): void {
    this.implementFiles = [];
    this.implementBranch = '';
    this.implementBuildStatus = '';
    if (!phase || phase.status !== 'completed' || !phase.data) return;

    const data = phase.data;
    this.implementFiles = (data['files_written'] as string[]) || (data['files'] as string[]) || [];
    this.implementBranch = (data['branch'] as string) || '';
    this.implementBuildStatus = (data['build_status'] as string) || (data['build'] as string) || '';
  }

  // ── Helpers ──

  getClassIcon(type: string | null): string {
    switch (type) {
      case 'bug': return 'bug_report';
      case 'feature': return 'add_circle';
      case 'refactor': return 'build';
      case 'investigation': return 'search';
      default: return 'help_outline';
    }
  }

  formatCategory(cat: string): string {
    return cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }
}
