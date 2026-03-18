import { Component, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

import { ApiService } from '../../services/api.service';

interface TriageEntryPoint {
  component: string;
  file_path: string;
  score: number;
  signals: string[];
}

interface TriageBlastRadius {
  affected: { component: string; depth: number }[];
  depth: number;
  component_count: number;
  containers_affected: string[];
}

interface TriageTestCoverage {
  covered: string[];
  uncovered: string[];
  coverage_ratio: number;
}

interface TriageRiskAssessment {
  risk_level: string;
  security_sensitive: boolean;
  flags: string[];
}

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
  // backward compat
  relevant_dimensions?: { dimension: string; insight: string }[];
}

@Component({
  selector: 'app-triage',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatInputModule,
    MatFormFieldModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatTabsModule,
    MatTooltipModule,
    MatSlideToggleModule,
    MatSnackBarModule,
  ],
  template: `
    <div class="page-container">
      <div class="page-header">
        <mat-icon class="page-icon">troubleshoot</mat-icon>
        <div>
          <h1 class="page-title">Issue Triage</h1>
          <p class="page-subtitle">Classify issues, find entry points, calculate blast radius</p>
        </div>
      </div>

      <!-- Input Form -->
      <mat-card class="triage-form-card">
        <mat-card-content>
          <div class="form-row">
            <mat-form-field class="id-field" appearance="outline">
              <mat-label>Issue ID</mat-label>
              <input matInput [(ngModel)]="issueId" placeholder="e.g. BUG-123" />
            </mat-form-field>
            <mat-form-field class="title-field" appearance="outline">
              <mat-label>Title</mat-label>
              <input matInput [(ngModel)]="title" placeholder="Short issue summary" />
            </mat-form-field>
          </div>
          <mat-form-field class="full-width" appearance="outline">
            <mat-label>Description</mat-label>
            <textarea matInput [(ngModel)]="description" rows="4" placeholder="Detailed description, stack traces, steps to reproduce..."></textarea>
          </mat-form-field>
          <div class="form-actions">
            <mat-slide-toggle [(ngModel)]="fullMode" color="primary">
              Full Analysis (LLM)
            </mat-slide-toggle>
            <span class="flex-1"></span>
            <button
              mat-flat-button
              color="primary"
              (click)="runTriage()"
              [disabled]="running || (!title && !description)"
            >
              @if (running) {
                <mat-spinner diameter="18" class="btn-spinner"></mat-spinner>
              } @else {
                <mat-icon>troubleshoot</mat-icon>
              }
              {{ running ? (fullMode ? 'Analysing...' : 'Scanning...') : (fullMode ? 'Run Full Triage' : 'Quick Triage') }}
            </button>
          </div>
        </mat-card-content>
      </mat-card>

      <!-- Results -->
      @if (error) {
        <div class="error-banner">
          <mat-icon>error</mat-icon>
          {{ error }}
        </div>
      }

      @if (result) {
        <!-- Classification Banner -->
        <div class="classification-banner" [class]="'risk-' + riskLevel">
          <div class="class-main">
            <span class="class-type">
              <mat-icon>{{ classIcon }}</mat-icon>
              {{ classification }}
            </span>
            <span class="class-confidence">{{ confidencePercent }}% confidence</span>
          </div>
          <div class="class-meta">
            <span class="risk-badge">Risk: {{ riskLevel }}</span>
            @if (entryPointCount > 0) {
              <span class="meta-item">
                <mat-icon class="meta-icon">pin_drop</mat-icon>
                {{ entryPointCount }} entry points
              </span>
            }
            @if (blastRadiusCount > 0) {
              <span class="meta-item">
                <mat-icon class="meta-icon">radar</mat-icon>
                {{ blastRadiusCount }} affected components
              </span>
            }
            @if (durationSeconds > 0) {
              <span class="meta-item">
                <mat-icon class="meta-icon">timer</mat-icon>
                {{ durationSeconds }}s
              </span>
            }
          </div>
        </div>

        <!-- Tabs: Customer / Developer / Findings -->
        <mat-tab-group class="result-tabs" animationDuration="200ms">
          <!-- Customer Summary Tab -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">person</mat-icon> Customer Summary
            </ng-template>
            <div class="tab-body">
              @if (customerMd) {
                <div class="md-content" [innerHTML]="renderMarkdown(customerMd)"></div>
              } @else if (customerSummary) {
                <div class="summary-card">
                  <div class="summary-row">
                    <span class="summary-label">Impact</span>
                    <span class="impact-badge" [class]="'impact-' + customerSummary.impact_level">
                      {{ customerSummary.impact_level }}
                    </span>
                  </div>
                  <div class="summary-row">
                    <span class="summary-label">Type</span>
                    <span>{{ customerSummary.is_bug ? 'Bug' : 'Enhancement / Task' }}</span>
                  </div>
                  <div class="summary-row">
                    <span class="summary-label">Timeline</span>
                    <span>{{ customerSummary.eta_category || 'unknown' }}</span>
                  </div>
                  <div class="summary-text">{{ customerSummary.summary }}</div>
                  @if (customerSummary.workaround) {
                    <div class="workaround">
                      <strong>Workaround:</strong> {{ customerSummary.workaround }}
                    </div>
                  }
                </div>
              } @else {
                <p class="empty-hint">Run full triage (LLM) to generate a customer summary.</p>
              }
            </div>
          </mat-tab>

          <!-- Developer Context Tab -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">code</mat-icon> Developer Context
            </ng-template>
            <div class="tab-body">
              @if (developerMd) {
                <div class="md-content" [innerHTML]="renderMarkdown(developerMd)"></div>
              } @else if (developerContext) {
                <div class="brief-section">
                  <h3>Big Picture</h3>
                  <p>{{ developerContext.big_picture || 'Needs investigation' }}</p>
                </div>
                <div class="brief-section">
                  <h3>Scope Boundary</h3>
                  <p>{{ developerContext.scope_boundary || 'Needs investigation' }}</p>
                </div>
                @if (developerContext.classification_assessment) {
                  <div class="brief-section">
                    <h3>Classification Assessment</h3>
                    @if (developerContext.classification_confidence >= 0) {
                      <span class="confidence-badge" [class]="getConfidenceClass(developerContext.classification_confidence)">
                        {{ getConfidenceLabel(developerContext.classification_confidence) }}
                        {{ (developerContext.classification_confidence * 100).toFixed(0) }}%
                      </span>
                    }
                    <p>{{ developerContext.classification_assessment }}</p>
                  </div>
                }
                @if (developerContext.affected_components.length) {
                  <div class="brief-section">
                    <h3>Affected Components</h3>
                    <ul class="file-list">
                      @for (c of developerContext.affected_components; track c) {
                        <li>{{ c }}</li>
                      }
                    </ul>
                  </div>
                }
                @if (developerContext.context_boundaries.length) {
                  <div class="brief-section">
                    <h3>Context Boundaries</h3>
                    <div class="boundaries-list">
                      @for (b of developerContext.context_boundaries; track b.category) {
                        <div class="boundary-item" [class]="'severity-' + b.severity">
                          <div class="boundary-header">
                            <span class="severity-badge" [class]="'sev-' + b.severity">
                              {{ b.severity.toUpperCase() }}
                            </span>
                            <span class="boundary-category">{{ formatCategory(b.category) }}</span>
                          </div>
                          <div class="boundary-text">{{ b.boundary }}</div>
                          @if (b.source_facts.length) {
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
                @if (developerContext.architecture_notes) {
                  <div class="brief-section">
                    <h3>Architecture Walkthrough</h3>
                    <p>{{ developerContext.architecture_notes }}</p>
                  </div>
                }
                @if (developerContext.anticipated_questions.length) {
                  <div class="brief-section">
                    <h3>Anticipated Questions</h3>
                    <div class="questions-list">
                      @for (q of developerContext.anticipated_questions; track q.question) {
                        <div class="question-item">
                          <div class="question-text">{{ q.question }}</div>
                          <div class="answer-text">{{ q.answer }}</div>
                        </div>
                      }
                    </div>
                  </div>
                }
              } @else {
                <p class="empty-hint">Run full triage (LLM) to generate developer context.</p>
              }
            </div>
          </mat-tab>

          <!-- Findings Tab -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">analytics</mat-icon> Findings
            </ng-template>
            <div class="tab-body">
              <!-- Entry Points -->
              @if (entryPoints.length) {
                <div class="findings-section">
                  <h3><mat-icon class="section-icon">pin_drop</mat-icon> Entry Points</h3>
                  <div class="entry-points-grid">
                    @for (ep of entryPoints; track ep.component) {
                      <div class="ep-card">
                        <div class="ep-name">{{ ep.component }}</div>
                        @if (ep.file_path) {
                          <div class="ep-path"><code>{{ ep.file_path }}</code></div>
                        }
                        <div class="ep-score">Score: {{ (ep.score * 100).toFixed(0) }}%</div>
                        <div class="ep-signals">
                          @for (s of ep.signals; track s) {
                            <span class="signal-chip">{{ s }}</span>
                          }
                        </div>
                      </div>
                    }
                  </div>
                </div>
              }

              <!-- Blast Radius -->
              @if (blastRadius) {
                <div class="findings-section">
                  <h3><mat-icon class="section-icon">radar</mat-icon> Blast Radius</h3>
                  <div class="blast-stats">
                    <div class="blast-stat">
                      <strong>{{ blastRadius.component_count }}</strong> components affected
                    </div>
                    <div class="blast-stat">
                      <strong>{{ blastRadius.depth }}</strong> depth levels
                    </div>
                    @if (blastRadius.containers_affected.length) {
                      <div class="blast-stat">
                        <strong>{{ blastRadius.containers_affected.length }}</strong> containers:
                        {{ blastRadius.containers_affected.join(', ') }}
                      </div>
                    }
                  </div>
                </div>
              }

              <!-- Test Coverage -->
              @if (testCoverage) {
                <div class="findings-section">
                  <h3><mat-icon class="section-icon">verified</mat-icon> Test Coverage</h3>
                  <div class="coverage-bar-container">
                    <div class="coverage-bar" [style.width.%]="testCoverage.coverage_ratio * 100"></div>
                  </div>
                  <div class="coverage-label">
                    {{ (testCoverage.coverage_ratio * 100).toFixed(0) }}% covered
                    ({{ testCoverage.covered.length || 0 }} / {{ (testCoverage.covered.length || 0) + (testCoverage.uncovered.length || 0) }})
                  </div>
                  @if (testCoverage.uncovered.length) {
                    <div class="uncovered-list">
                      <strong>Uncovered:</strong>
                      @for (u of testCoverage.uncovered; track u) {
                        <span class="uncovered-chip">{{ u }}</span>
                      }
                    </div>
                  }
                </div>
              }

              <!-- Risk Assessment -->
              @if (riskAssessment) {
                <div class="findings-section">
                  <h3><mat-icon class="section-icon">shield</mat-icon> Risk Assessment</h3>
                  <div class="risk-detail">
                    <span class="risk-level-badge" [class]="'risk-' + riskAssessment.risk_level">
                      {{ riskAssessment.risk_level }}
                    </span>
                    @if (riskAssessment.security_sensitive) {
                      <span class="security-flag">Security Sensitive</span>
                    }
                  </div>
                  @if (riskAssessment.flags.length) {
                    <div class="risk-flags">
                      @for (flag of riskAssessment.flags; track flag) {
                        <span class="flag-chip">{{ flag }}</span>
                      }
                    </div>
                  }
                </div>
              }
            </div>
          </mat-tab>
        </mat-tab-group>
      }

      <!-- Past Results -->
      @if (pastResults.length && !result) {
        <h2 class="section-heading">Past Triage Results</h2>
        <div class="past-results-grid">
          @for (r of pastResults; track r.issue_id) {
            <mat-card class="past-card" (click)="loadResult(r.issue_id)">
              <mat-card-content>
                <div class="past-id">{{ r.issue_id }}</div>
                <span class="past-type">{{ r.classification['type'] || 'unknown' }}</span>
              </mat-card-content>
            </mat-card>
          }
        </div>
      }
    </div>
  `,
  styles: [
    `
      .triage-form-card {
        margin-bottom: 20px;
      }
      .form-row {
        display: flex;
        gap: 16px;
      }
      .id-field {
        width: 200px;
      }
      .title-field {
        flex: 1;
      }
      .full-width {
        width: 100%;
      }
      .form-actions {
        display: flex;
        align-items: center;
        gap: 16px;
        margin-top: 8px;
      }
      .btn-spinner {
        display: inline-block;
        margin-right: 8px;
      }

      /* Classification Banner */
      .classification-banner {
        padding: 16px 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        border: 1px solid var(--cg-gray-200);
        background: #fff;
      }
      .classification-banner.risk-low {
        border-left: 4px solid var(--cg-success, #28a745);
      }
      .classification-banner.risk-medium {
        border-left: 4px solid var(--cg-warn, #f57c00);
      }
      .classification-banner.risk-high {
        border-left: 4px solid var(--cg-error, #dc3545);
      }
      .classification-banner.risk-critical {
        border-left: 4px solid #9c27b0;
      }
      .class-main {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;
      }
      .class-type {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 18px;
        font-weight: 600;
        text-transform: capitalize;
      }
      .class-confidence {
        font-size: 13px;
        color: var(--cg-gray-500);
      }
      .class-meta {
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
        align-items: center;
      }
      .risk-badge {
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        text-transform: capitalize;
        background: var(--cg-gray-100);
      }
      .risk-low .risk-badge {
        background: rgba(40, 167, 69, 0.1);
        color: #28a745;
      }
      .risk-medium .risk-badge {
        background: rgba(245, 124, 0, 0.1);
        color: #f57c00;
      }
      .risk-high .risk-badge {
        background: rgba(220, 53, 69, 0.1);
        color: #dc3545;
      }
      .risk-critical .risk-badge {
        background: rgba(156, 39, 176, 0.1);
        color: #9c27b0;
      }
      .meta-item {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 13px;
        color: var(--cg-gray-500);
      }
      .meta-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
      }

      /* Result Tabs */
      .result-tabs {
        background: #fff;
        border-radius: 12px;
        overflow: hidden;
      }
      .tab-icon {
        margin-right: 6px;
        font-size: 18px;
        width: 18px;
        height: 18px;
      }
      .tab-body {
        padding: 20px;
      }
      .empty-hint {
        color: var(--cg-gray-400);
        font-style: italic;
      }

      /* Customer Summary */
      .summary-card {
        max-width: 600px;
      }
      .summary-row {
        display: flex;
        gap: 12px;
        margin-bottom: 8px;
        align-items: center;
      }
      .summary-label {
        font-weight: 500;
        width: 80px;
        color: var(--cg-gray-500);
      }
      .impact-badge {
        padding: 2px 10px;
        border-radius: 10px;
        font-size: 12px;
        font-weight: 600;
        text-transform: capitalize;
      }
      .impact-low {
        background: rgba(40, 167, 69, 0.1);
        color: #28a745;
      }
      .impact-medium {
        background: rgba(245, 124, 0, 0.1);
        color: #f57c00;
      }
      .impact-high {
        background: rgba(220, 53, 69, 0.1);
        color: #dc3545;
      }
      .impact-critical {
        background: rgba(156, 39, 176, 0.1);
        color: #9c27b0;
      }
      .summary-text {
        margin-top: 16px;
        line-height: 1.6;
      }
      .workaround {
        margin-top: 12px;
        padding: 12px;
        background: var(--cg-gray-50);
        border-radius: 8px;
      }

      /* Developer Brief */
      .brief-section {
        margin-bottom: 20px;
      }
      .brief-section h3 {
        font-size: 15px;
        font-weight: 500;
        margin: 0 0 8px;
      }
      .confidence-badge {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        margin-bottom: 8px;
      }
      .confidence-high {
        background: rgba(40, 167, 69, 0.1);
        color: #28a745;
      }
      .confidence-medium {
        background: rgba(245, 124, 0, 0.1);
        color: #f57c00;
      }
      .confidence-low {
        background: rgba(220, 53, 69, 0.1);
        color: #dc3545;
      }
      .file-list {
        list-style: none;
        padding: 0;
        margin: 0;
      }
      .file-list li {
        padding: 4px 0;
      }
      .file-list code {
        font-size: 13px;
        padding: 2px 6px;
        background: var(--cg-gray-50);
        border-radius: 4px;
      }
      .action-list li {
        margin-bottom: 6px;
        line-height: 1.5;
      }
      .boundaries-list {
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
      .boundary-item {
        padding: 10px 14px;
        border-radius: 8px;
        background: var(--cg-gray-50);
        border-left: 3px solid var(--cg-blue, #0070ad);
      }
      .boundary-item.severity-caution {
        border-left-color: #f57c00;
        background: rgba(245, 124, 0, 0.03);
      }
      .boundary-item.severity-blocking {
        border-left-color: #dc3545;
        background: rgba(220, 53, 69, 0.03);
      }
      .boundary-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
      }
      .severity-badge {
        padding: 1px 8px;
        border-radius: 8px;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.5px;
      }
      .sev-info {
        background: rgba(0, 112, 173, 0.1);
        color: #0070ad;
      }
      .sev-caution {
        background: rgba(245, 124, 0, 0.1);
        color: #f57c00;
      }
      .sev-blocking {
        background: rgba(220, 53, 69, 0.1);
        color: #dc3545;
      }
      .boundary-category {
        font-weight: 600;
        font-size: 13px;
        color: var(--cg-gray-700);
      }
      .boundary-text {
        font-size: 13px;
        line-height: 1.5;
        margin-bottom: 6px;
      }
      .boundary-sources {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
      }
      .source-chip {
        padding: 1px 6px;
        border-radius: 6px;
        font-size: 10px;
        background: var(--cg-gray-100);
        color: var(--cg-gray-500);
        font-family: monospace;
      }

      /* Anticipated Questions */
      .questions-list {
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
      .question-item {
        padding: 10px 14px;
        border-radius: 8px;
        background: var(--cg-gray-50);
        border-left: 3px solid var(--cg-blue, #0070ad);
      }
      .question-text {
        font-weight: 600;
        font-size: 13px;
        color: var(--cg-gray-700);
        margin-bottom: 4px;
      }
      .question-text::before {
        content: 'Q: ';
        color: var(--cg-blue, #0070ad);
      }
      .answer-text {
        font-size: 13px;
        line-height: 1.5;
        color: var(--cg-gray-600);
      }
      .answer-text::before {
        content: 'A: ';
        font-weight: 600;
        color: var(--cg-gray-500);
      }

      /* Markdown content */
      .md-content {
        line-height: 1.7;
      }
      .md-content h1 {
        font-size: 20px;
        margin: 0 0 12px;
      }
      .md-content h2 {
        font-size: 16px;
        margin: 16px 0 8px;
      }
      .md-content ul,
      .md-content ol {
        padding-left: 20px;
      }
      .md-content code {
        padding: 1px 4px;
        background: var(--cg-gray-50);
        border-radius: 3px;
        font-size: 13px;
      }

      /* Findings */
      .findings-section {
        margin-bottom: 24px;
      }
      .findings-section h3 {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 15px;
        font-weight: 500;
        margin: 0 0 12px;
      }
      .section-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
        color: var(--cg-blue);
      }
      .entry-points-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 12px;
      }
      .ep-card {
        padding: 12px;
        border-radius: 10px;
        border: 1px solid var(--cg-gray-100);
        background: var(--cg-gray-50);
      }
      .ep-name {
        font-weight: 600;
        margin-bottom: 4px;
      }
      .ep-path code {
        font-size: 12px;
        color: var(--cg-gray-500);
      }
      .ep-score {
        font-size: 12px;
        color: var(--cg-gray-400);
        margin: 4px 0;
      }
      .ep-signals {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
      }
      .signal-chip {
        padding: 1px 7px;
        border-radius: 8px;
        font-size: 10px;
        background: rgba(0, 112, 173, 0.08);
        color: var(--cg-blue);
      }
      .blast-stats {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
      }
      .blast-stat {
        font-size: 14px;
      }
      .blast-stat strong {
        color: var(--cg-navy);
      }
      .coverage-bar-container {
        width: 100%;
        height: 8px;
        background: var(--cg-gray-100);
        border-radius: 4px;
        overflow: hidden;
        margin-bottom: 6px;
      }
      .coverage-bar {
        height: 100%;
        background: var(--cg-success, #28a745);
        border-radius: 4px;
        transition: width 0.3s;
      }
      .coverage-label {
        font-size: 13px;
        color: var(--cg-gray-500);
        margin-bottom: 8px;
      }
      .uncovered-list {
        margin-top: 8px;
        font-size: 13px;
      }
      .uncovered-chip {
        display: inline-block;
        padding: 1px 7px;
        margin: 2px 4px;
        border-radius: 8px;
        font-size: 11px;
        background: rgba(220, 53, 69, 0.08);
        color: var(--cg-error, #dc3545);
      }
      .risk-detail {
        display: flex;
        gap: 12px;
        align-items: center;
        margin-bottom: 8px;
      }
      .risk-level-badge {
        padding: 4px 14px;
        border-radius: 12px;
        font-weight: 600;
        text-transform: capitalize;
      }
      .risk-level-badge.risk-low {
        background: rgba(40, 167, 69, 0.1);
        color: #28a745;
      }
      .risk-level-badge.risk-medium {
        background: rgba(245, 124, 0, 0.1);
        color: #f57c00;
      }
      .risk-level-badge.risk-high {
        background: rgba(220, 53, 69, 0.1);
        color: #dc3545;
      }
      .risk-level-badge.risk-critical {
        background: rgba(156, 39, 176, 0.1);
        color: #9c27b0;
      }
      .security-flag {
        padding: 2px 10px;
        border-radius: 10px;
        font-size: 12px;
        font-weight: 600;
        background: rgba(220, 53, 69, 0.08);
        color: #dc3545;
      }
      .risk-flags {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
      }
      .flag-chip {
        padding: 2px 8px;
        border-radius: 8px;
        font-size: 11px;
        background: var(--cg-gray-50);
        color: var(--cg-gray-600);
        font-family: monospace;
      }

      /* Past Results */
      .section-heading {
        font-size: 16px;
        font-weight: 500;
        margin: 24px 0 12px;
      }
      .past-results-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 12px;
      }
      .past-card {
        cursor: pointer;
        transition: box-shadow 0.15s;
      }
      .past-card:hover {
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      }
      .past-id {
        font-weight: 600;
        font-size: 14px;
        margin-bottom: 4px;
      }
      .past-type {
        font-size: 12px;
        text-transform: capitalize;
        color: var(--cg-gray-500);
      }

      .error-banner {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 12px 16px;
        border-radius: 8px;
        background: rgba(220, 53, 69, 0.06);
        color: var(--cg-error, #dc3545);
        margin-bottom: 16px;
      }
    `,
  ],
})
export class TriageComponent {
  // Form
  issueId = '';
  title = '';
  description = '';
  fullMode = false;
  running = false;
  error = '';

  // Result
  result: Record<string, unknown> | null = null;
  customerMd = '';
  developerMd = '';
  customerSummary: TriageCustomerSummary | null = null;
  developerContext: TriageDeveloperContext | null = null;

  // Findings
  entryPoints: TriageEntryPoint[] = [];
  blastRadius: TriageBlastRadius | null = null;
  testCoverage: TriageTestCoverage | null = null;
  riskAssessment: TriageRiskAssessment | null = null;

  // Derived
  classification = '';
  confidencePercent = 0;
  riskLevel = 'medium';
  classIcon = 'help_outline';
  entryPointCount = 0;
  blastRadiusCount = 0;
  durationSeconds = 0;

  // Past results
  pastResults: { issue_id: string; classification: Record<string, unknown> }[] = [];

  constructor(
    private api: ApiService,
    private cdr: ChangeDetectorRef,
    private snackBar: MatSnackBar,
  ) {
    this.loadPastResults();
  }

  runTriage(): void {
    this.running = true;
    this.error = '';
    this.result = null;

    const id = this.issueId || `TRIAGE-${Date.now()}`;

    if (this.fullMode) {
      this.api
        .runFullTriage({
          issue_id: id,
          title: this.title,
          description: this.description,
        })
        .subscribe({
          next: (res) => this.handleResult(res as Record<string, unknown>, id),
          error: (err) => this.handleError(err),
        });
    } else {
      this.api.runQuickTriage({ title: this.title, description: this.description }).subscribe({
        next: (res) => this.handleResult(res as Record<string, unknown>, null),
        error: (err) => this.handleError(err),
      });
    }
  }

  loadResult(issueId: string): void {
    this.api.getTriageResult(issueId).subscribe({
      next: (data) => {
        this.customerMd = data.customer_md || '';
        this.developerMd = data.developer_md || '';
        const triage = data.triage || {};
        this.customerSummary = (triage['customer_summary'] as TriageCustomerSummary) || null;
        this.developerContext = (triage['developer_context'] || triage['developer_brief']) as TriageDeveloperContext || null;

        // Backward compat: map old relevant_dimensions → context_boundaries
        if (this.developerContext && !this.developerContext.context_boundaries?.length && this.developerContext.relevant_dimensions?.length) {
          this.developerContext.context_boundaries = this.developerContext.relevant_dimensions.map(dim => ({
            category: 'technology_constraint',
            boundary: dim.insight,
            severity: 'info' as const,
            source_facts: [dim.dimension],
          }));
        }

        const findings = data.findings || (triage['findings'] as Record<string, unknown>) || {};
        this.applyFindings(findings);
        this.result = triage;
        this.cdr.markForCheck();
      },
      error: () => {
        this.snackBar.open('Failed to load triage result', 'OK', { duration: 4000 });
      },
    });
  }

  renderMarkdown(md: string): string {
    // Simple markdown → HTML (headings, bold, code, lists)
    return md
      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      .replace(/^# (.+)$/gm, '<h1>$1</h1>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/^- (.+)$/gm, '<li>$1</li>')
      .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
      .replace(/\n\n/g, '<br><br>')
      .replace(/\n/g, '<br>');
  }

  private handleResult(res: Record<string, unknown>, issueId: string | null): void {
    this.running = false;
    this.result = res;

    // For full triage, load the detailed result
    if (issueId && res['status'] === 'success') {
      this.loadResult(issueId);
    }

    // For quick triage, apply findings directly
    if (res['mode'] === 'quick') {
      this.applyFindings(res);
    }

    this.durationSeconds = (res['duration_seconds'] as number) || 0;
    this.cdr.markForCheck();
  }

  private applyFindings(findings: Record<string, unknown>): void {
    const cls = (findings['classification'] as Record<string, unknown>) || {};
    this.classification = (cls['type'] as string) || 'unknown';
    this.confidencePercent = Math.round(((cls['confidence'] as number) || 0) * 100);
    this.classIcon = this.getClassIcon(this.classification);

    this.entryPoints = (findings['entry_points'] as TriageEntryPoint[]) || [];
    this.entryPointCount = this.entryPoints.length;

    this.blastRadius = (findings['blast_radius'] as TriageBlastRadius) || null;
    this.blastRadiusCount = this.blastRadius?.component_count || 0;

    this.testCoverage = (findings['test_coverage'] as TriageTestCoverage) || null;

    this.riskAssessment = (findings['risk_assessment'] as TriageRiskAssessment) || null;
    this.riskLevel = this.riskAssessment?.risk_level || 'medium';
  }

  private handleError(err: unknown): void {
    this.running = false;
    this.error = (err as { error?: { detail?: string } })?.error?.detail || 'Triage failed. Check backend logs.';
    this.cdr.markForCheck();
  }

  formatCategory(cat: string): string {
    return cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  getConfidenceClass(confidence: number): string {
    if (confidence >= 0.7) return 'confidence-high';
    if (confidence >= 0.4) return 'confidence-medium';
    return 'confidence-low';
  }

  getConfidenceLabel(confidence: number): string {
    if (confidence >= 0.7) return 'Confirmed bug';
    if (confidence >= 0.4) return 'Uncertain';
    return 'Likely NOT a bug';
  }

  private getClassIcon(type: string): string {
    switch (type) {
      case 'bug':
        return 'bug_report';
      case 'feature':
        return 'add_circle';
      case 'refactor':
        return 'build';
      case 'investigation':
        return 'search';
      default:
        return 'help_outline';
    }
  }

  private loadPastResults(): void {
    this.api.getTriageResults().subscribe({
      next: (data) => {
        this.pastResults = data.results || [];
        this.cdr.markForCheck();
      },
      error: () => {},
    });
  }
}
