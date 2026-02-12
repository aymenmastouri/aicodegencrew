import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatButtonModule } from '@angular/material/button';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';

import { ApiService, PipelineStatus, HealthResponse, SetupStatus } from '../../services/api.service';
import { PipelineService, RunHistoryEntry, ResetPreview } from '../../services/pipeline.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatButtonModule,
    MatSnackBarModule,
    MatTooltipModule,
    RouterLink,
  ],
  template: `
    <div class="page-container">
      <!-- Hero -->
      <div class="hero">
        <img src="assets/logos/Capgemini_Primary-logo_Capgemini-white.png" alt="Capgemini" class="hero-logo" />
        <div class="hero-text">
          <h1 class="hero-title"><span class="hero-accent">AI</span>CodeGen<span class="hero-accent">Crew</span></h1>
          <p class="hero-subtitle">Full SDLC Pipeline — from Architecture Analysis to Code Generation</p>
        </div>
        <div class="hero-stats">
          @if (health) {
            <div class="stat-pill" [class.stat-ok]="health.status === 'ok'" [class.stat-error]="health.status !== 'ok'">
              <span class="stat-dot" [class.dot-ok]="health.status === 'ok'" [class.dot-error]="health.status !== 'ok'"></span>
              <span>Backend</span>
            </div>
            <div class="stat-pill" [class.stat-ok]="health.knowledge_dir_exists" [class.stat-error]="!health.knowledge_dir_exists">
              <span class="stat-dot" [class.dot-ok]="health.knowledge_dir_exists" [class.dot-error]="!health.knowledge_dir_exists"></span>
              <span>Knowledge</span>
            </div>
          } @else {
            <div class="stat-pill stat-loading">
              <mat-spinner diameter="14"></mat-spinner>
              <span>Connecting...</span>
            </div>
          }
        </div>
      </div>

      <!-- Getting Started -->
      @if (setupStatus && !onboardingDismissed) {
        <div class="onboarding-card" [class.onboarding-complete]="allSetupComplete()">
          <div class="onboarding-header">
            <div>
              @if (allSetupComplete()) {
                <div class="onboarding-title onboarding-done-title">All set! You're ready to go.</div>
              } @else {
                <div class="onboarding-title">Getting Started</div>
                <div class="onboarding-sub">Complete these steps to run your first pipeline</div>
              }
            </div>
            <button class="dismiss-btn" (click)="dismissOnboarding()" matTooltip="Dismiss">
              <mat-icon>close</mat-icon>
            </button>
          </div>
          @if (!allSetupComplete()) {
            <div class="onboarding-progress">
              <div class="progress-track">
                <div class="progress-fill" [style.width.%]="setupProgress()"></div>
              </div>
              <span class="progress-label">{{ setupCompleteCount() }} of 4 complete</span>
            </div>
          }
          <div class="onboarding-steps">
            @for (step of setupSteps; track step.label; let i = $index) {
              <a class="onboarding-step" [class.step-done]="step.check()" [routerLink]="step.link">
                <span class="step-num" [class.num-done]="step.check()">
                  @if (step.check()) {
                    <mat-icon class="check-icon">check</mat-icon>
                  } @else {
                    {{ i + 1 }}
                  }
                </span>
                <span class="step-label">{{ step.label }}</span>
                <mat-icon class="step-arrow">chevron_right</mat-icon>
              </a>
            }
          </div>
        </div>
      }
      @if (onboardingDismissed && !allSetupComplete()) {
        <button class="show-wizard-btn" (click)="showOnboarding()">
          <mat-icon>checklist</mat-icon> Show setup guide
        </button>
      }

      <!-- Active Pipeline Banner -->
      @if (executionState && executionState !== 'idle') {
        <a class="active-banner" [class]="'banner-' + executionState" routerLink="/run">
          <div class="banner-left">
            <mat-icon class="banner-icon">
              {{ executionState === 'running' ? 'sync' : executionState === 'completed' ? 'check_circle' : 'error' }}
            </mat-icon>
            <div>
              <div class="banner-title">Pipeline {{ executionState | titlecase }}</div>
              @if (executionRunId) {
                <div class="banner-sub">{{ executionRunId }}</div>
              }
            </div>
          </div>
          @if (executionState === 'running') {
            <mat-progress-bar mode="indeterminate" class="banner-progress"></mat-progress-bar>
          }
          <mat-icon class="banner-arrow">chevron_right</mat-icon>
        </a>
      }

      <!-- Pipeline Phases -->
      <div class="section-header">
        <h2>Phases</h2>
        <div class="section-actions">
          @if (hasCompletedPhases()) {
            <button mat-stroked-button class="btn-reset" (click)="resetAll()" matTooltip="Reset all completed phases">
              Reset All
            </button>
          }
          <button mat-flat-button color="primary" routerLink="/run">Run Pipeline</button>
        </div>
      </div>

      @if (loading) {
        <div class="loading-center">
          <mat-spinner diameter="36"></mat-spinner>
        </div>
      } @else if (pipeline && pipeline.phases.length > 0) {
        <div class="phase-grid">
          @for (phase of pipeline.phases; track phase.id; let i = $index) {
            <div class="phase-card" [class]="'phase-' + phase.status" [routerLink]="'/phases'">
              <div class="phase-top">
                <span class="phase-index">{{ i }}</span>
                <span class="phase-name">{{ phase.name }}</span>
              </div>
              <div class="phase-bottom">
                <span class="status-dot" [class]="'dot-' + phase.status"></span>
                <span class="status-label">{{ phase.status }}</span>
                @if (phase.status === 'completed') {
                  <button class="reset-btn" (click)="resetPhase(phase.id); $event.stopPropagation(); $event.preventDefault()"
                    matTooltip="Reset">
                    <mat-icon>restart_alt</mat-icon>
                  </button>
                }
              </div>
            </div>
          }
        </div>
      } @else {
        <div class="empty-state">
          <mat-icon class="empty-icon">inbox</mat-icon>
          <p>No pipeline data yet.</p>
          <button mat-flat-button color="primary" routerLink="/run">Get Started</button>
        </div>
      }

      <!-- Recent Activity -->
      @if (recentHistory.length > 0) {
        <div class="section-header mt-32">
          <h2>Recent Activity</h2>
          <a routerLink="/history" class="view-all">View all</a>
        </div>
        <div class="activity-card">
          @for (entry of recentHistory; track entry.run_id) {
            <div class="activity-row">
              <span class="activity-trigger" [class]="'at-' + (entry.trigger || 'pipeline')">
                {{ entry.trigger === 'reset' ? 'Reset' : 'Run' }}
              </span>
              <span class="activity-id">{{ entry.run_id }}</span>
              <span class="activity-phases">{{ entry.phases.length }} phase{{ entry.phases.length !== 1 ? 's' : '' }}</span>
              <span class="flex-1"></span>
              <span class="status-dot sm" [class]="'dot-' + entry.status"></span>
              <span class="activity-status">{{ entry.status }}</span>
              <span class="activity-time">{{ entry.started_at | date: 'short' }}</span>
            </div>
          }
        </div>
      }

      <!-- Quick Actions -->
      <div class="section-header mt-32">
        <h2>Quick Actions</h2>
      </div>
      <div class="action-grid">
        @for (link of quickLinks; track link.route) {
          <a class="action-card" [routerLink]="link.route">
            <mat-icon class="action-icon">{{ link.icon }}</mat-icon>
            <div>
              <div class="action-label">{{ link.label }}</div>
              <div class="action-desc">{{ link.description }}</div>
            </div>
          </a>
        }
      </div>
    </div>
  `,
  styles: [
    `
      .mt-32 { margin-top: 32px; }

      /* Hero */
      .hero {
        background: linear-gradient(135deg, var(--cg-navy) 0%, var(--cg-dark) 100%);
        border-radius: 16px;
        padding: 32px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 24px;
        position: relative;
      }
      .hero-logo {
        position: absolute;
        top: 20px;
        right: 24px;
        height: 28px;
        opacity: 0.3;
      }
      .hero-title {
        font-size: 28px;
        font-weight: 300;
        color: #fff;
        margin: 0 0 6px;
      }
      .hero-accent { color: var(--cg-vibrant); font-weight: 600; }
      .hero-subtitle {
        color: rgba(255, 255, 255, 0.55);
        font-size: 14px;
        margin: 0;
      }
      .hero-stats { display: flex; gap: 10px; flex-shrink: 0; }
      .stat-pill {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 5px 12px;
        border-radius: 16px;
        font-size: 12px;
        font-weight: 500;
        background: rgba(255, 255, 255, 0.08);
        color: rgba(255, 255, 255, 0.5);
      }
      .stat-ok { color: var(--cg-success); }
      .stat-error { color: var(--cg-error); }
      .stat-dot {
        width: 7px; height: 7px;
        border-radius: 50%;
        background: rgba(255,255,255,0.3);
      }
      .dot-ok { background: var(--cg-success); }
      .dot-error { background: var(--cg-error); }

      /* Banner */
      .active-banner {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 12px 18px;
        border-radius: 10px;
        margin-bottom: 24px;
        cursor: pointer;
        text-decoration: none;
        color: inherit;
        transition: transform 0.15s;
      }
      .active-banner:hover { transform: translateY(-1px); }
      .banner-running { background: rgba(0, 112, 173, 0.06); border: 1px solid rgba(0, 112, 173, 0.15); }
      .banner-completed { background: rgba(40, 167, 69, 0.06); border: 1px solid rgba(40, 167, 69, 0.15); }
      .banner-failed { background: rgba(220, 53, 69, 0.06); border: 1px solid rgba(220, 53, 69, 0.15); }
      .banner-cancelled { background: rgba(255, 193, 7, 0.06); border: 1px solid rgba(255, 193, 7, 0.15); }
      .banner-left { display: flex; align-items: center; gap: 10px; }
      .banner-icon { font-size: 24px; width: 24px; height: 24px; }
      .banner-running .banner-icon { color: var(--cg-blue); animation: spin 1.5s linear infinite; }
      .banner-completed .banner-icon { color: var(--cg-success); }
      .banner-failed .banner-icon { color: var(--cg-error); }
      @keyframes spin { to { transform: rotate(360deg); } }
      .banner-title { font-weight: 500; font-size: 14px; }
      .banner-sub { font-size: 11px; color: var(--cg-gray-500); font-family: monospace; }
      .banner-progress { flex: 1; max-width: 180px; }
      .banner-arrow { margin-left: auto; color: var(--cg-gray-300); font-size: 20px; }

      /* Section Header */
      .section-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 14px;
      }
      .section-header h2 {
        font-weight: 500;
        font-size: 17px;
        margin: 0;
        color: var(--cg-gray-900);
      }
      .section-actions { display: flex; gap: 8px; }
      .btn-reset {
        color: var(--cg-error, #dc3545) !important;
        border-color: rgba(220, 53, 69, 0.3) !important;
        font-size: 13px !important;
      }
      .view-all {
        font-size: 13px;
        color: var(--cg-blue);
        text-decoration: none;
        font-weight: 500;
      }
      .view-all:hover { text-decoration: underline; }

      /* Phase Cards — Clean & Minimal */
      .phase-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 10px;
      }
      .phase-card {
        background: #fff;
        border-radius: 10px;
        padding: 14px 16px;
        border-left: 3px solid var(--cg-gray-200);
        cursor: pointer;
        text-decoration: none;
        color: inherit;
        transition: box-shadow 0.15s;
      }
      .phase-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.07); }
      .phase-completed { border-left-color: var(--cg-success); }
      .phase-failed { border-left-color: var(--cg-error); }
      .phase-running { border-left-color: var(--cg-blue); }
      .phase-ready { border-left-color: var(--cg-vibrant); }
      .phase-planned { border-left-color: var(--cg-gray-200); opacity: 0.55; }
      .phase-top {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
      }
      .phase-index {
        width: 22px; height: 22px;
        border-radius: 6px;
        background: var(--cg-gray-100);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 11px;
        font-weight: 700;
        color: var(--cg-gray-500);
        flex-shrink: 0;
      }
      .phase-name {
        font-size: 13px;
        font-weight: 500;
        color: var(--cg-gray-900);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .phase-bottom {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .status-dot {
        width: 8px; height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
      }
      .status-dot.sm { width: 6px; height: 6px; }
      .dot-completed { background: var(--cg-success); }
      .dot-success { background: var(--cg-success); }
      .dot-failed { background: var(--cg-error); }
      .dot-running { background: var(--cg-blue); }
      .dot-ready { background: var(--cg-vibrant); }
      .dot-planned { background: var(--cg-gray-300); }
      .dot-idle { background: var(--cg-gray-300); }
      .dot-cancelled { background: #e0a800; }
      .status-label {
        font-size: 12px;
        color: var(--cg-gray-500);
        text-transform: capitalize;
        flex: 1;
      }
      .reset-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 22px; height: 22px;
        border-radius: 6px;
        border: none;
        background: transparent;
        color: var(--cg-gray-300);
        cursor: pointer;
        transition: all 0.15s;
      }
      .reset-btn:hover { background: rgba(220, 53, 69, 0.1); color: var(--cg-error, #dc3545); }
      .reset-btn .mat-icon { font-size: 15px; width: 15px; height: 15px; }

      /* Loading & Empty */
      .loading-center { display: flex; justify-content: center; padding: 48px 0; }
      .empty-state {
        text-align: center;
        padding: 40px 24px;
        background: #fff;
        border-radius: 12px;
        border: 2px dashed var(--cg-gray-200);
      }
      .empty-icon { font-size: 40px; width: 40px; height: 40px; color: var(--cg-gray-200); margin-bottom: 8px; }
      .empty-state p { color: var(--cg-gray-500); margin-bottom: 14px; font-size: 14px; }

      /* Recent Activity — Clean rows */
      .activity-card {
        background: #fff;
        border-radius: 10px;
        overflow: hidden;
      }
      .activity-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 9px 16px;
        border-bottom: 1px solid var(--cg-gray-50);
        font-size: 13px;
      }
      .activity-row:last-child { border-bottom: none; }
      .activity-trigger {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        width: 40px;
      }
      .at-pipeline, .at-run { color: var(--cg-blue); }
      .at-reset { color: var(--cg-error, #dc3545); }
      .activity-id { font-family: monospace; font-size: 11px; color: var(--cg-gray-400); }
      .activity-phases { font-size: 12px; color: var(--cg-gray-400); }
      .activity-status { font-size: 12px; color: var(--cg-gray-500); text-transform: capitalize; }
      .activity-time { font-size: 11px; color: var(--cg-gray-400); white-space: nowrap; }

      /* Quick Actions — Simpler */
      .action-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 10px;
      }
      .action-card {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 14px 16px;
        background: #fff;
        border-radius: 10px;
        text-decoration: none;
        color: inherit;
        cursor: pointer;
        transition: box-shadow 0.15s;
      }
      .action-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.07); }
      .action-icon {
        font-size: 22px; width: 22px; height: 22px;
        color: var(--cg-blue);
        flex-shrink: 0;
      }
      .action-label { font-weight: 500; font-size: 13px; }
      .action-desc { font-size: 12px; color: var(--cg-gray-500); margin-top: 1px; }

      /* Onboarding */
      .onboarding-card {
        background: #fff;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 24px;
        border: 1px solid rgba(18, 171, 219, 0.15);
      }
      .onboarding-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 14px;
      }
      .onboarding-title {
        font-size: 15px;
        font-weight: 500;
        color: var(--cg-gray-900);
      }
      .onboarding-sub {
        font-size: 12px;
        color: var(--cg-gray-500);
        margin-top: 2px;
      }
      .dismiss-btn {
        border: none;
        background: none;
        cursor: pointer;
        color: var(--cg-gray-300);
        padding: 0;
        line-height: 1;
      }
      .dismiss-btn:hover { color: var(--cg-gray-500); }
      .dismiss-btn .mat-icon { font-size: 18px; width: 18px; height: 18px; }
      .onboarding-progress {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
      }
      .progress-track {
        flex: 1;
        height: 6px;
        background: var(--cg-gray-100, #f0f0f0);
        border-radius: 3px;
        overflow: hidden;
      }
      .progress-fill {
        height: 100%;
        background: var(--cg-success, #28a745);
        border-radius: 3px;
        transition: width 0.4s ease;
      }
      .progress-label {
        font-size: 12px;
        color: var(--cg-gray-400);
        white-space: nowrap;
      }
      .onboarding-steps {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
        gap: 8px;
      }
      .onboarding-step {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 12px;
        border-radius: 8px;
        background: var(--cg-gray-50, #f8f9fa);
        text-decoration: none;
        color: inherit;
        cursor: pointer;
        transition: background 0.15s;
      }
      .onboarding-step:hover { background: var(--cg-gray-100, #f0f0f0); }
      .onboarding-step.step-done { opacity: 0.55; }
      .step-num {
        width: 24px; height: 24px;
        border-radius: 50%;
        background: var(--cg-gray-200);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: 600;
        color: var(--cg-gray-500);
        flex-shrink: 0;
      }
      .num-done {
        background: var(--cg-success, #28a745);
        color: #fff;
      }
      .check-icon { font-size: 16px; width: 16px; height: 16px; }
      .step-label {
        font-size: 13px;
        font-weight: 500;
        flex: 1;
      }
      .step-arrow {
        font-size: 16px; width: 16px; height: 16px;
        color: var(--cg-gray-300);
      }
      .onboarding-complete {
        border-color: rgba(40, 167, 69, 0.2);
        background: rgba(40, 167, 69, 0.03);
      }
      .onboarding-done-title {
        color: var(--cg-success, #28a745);
      }
      .show-wizard-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        border: none;
        background: none;
        color: var(--cg-blue);
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
        padding: 0;
        margin-bottom: 16px;
      }
      .show-wizard-btn:hover { text-decoration: underline; }
      .show-wizard-btn .mat-icon { font-size: 16px; width: 16px; height: 16px; }
    `,
  ],
})
export class DashboardComponent implements OnInit {
  health: HealthResponse | null = null;
  pipeline: PipelineStatus | null = null;
  loading = true;
  recentHistory: RunHistoryEntry[] = [];

  executionState: string = 'idle';
  executionRunId: string = '';

  // Onboarding
  setupStatus: SetupStatus | null = null;
  onboardingDismissed = localStorage.getItem('onboarding_dismissed') === 'true';

  setupSteps = [
    { label: 'Configure repository', link: '/settings', check: () => this.setupStatus?.repo_configured ?? false },
    { label: 'Configure LLM', link: '/settings', check: () => this.setupStatus?.llm_configured ?? false },
    { label: 'Upload task files', link: '/inputs', check: () => this.setupStatus?.has_input_files ?? false },
    { label: 'Run first pipeline', link: '/run', check: () => this.setupStatus?.has_run_history ?? false },
  ];

  quickLinks = [
    {
      route: '/knowledge',
      icon: 'psychology',
      label: 'Knowledge Explorer',
      description: 'Browse architecture facts and analysis results',
    },
    {
      route: '/reports',
      icon: 'summarize',
      label: 'Development Plans',
      description: 'View generated plans and codegen reports',
    },
    {
      route: '/metrics',
      icon: 'monitoring',
      label: 'Pipeline Metrics',
      description: 'Execution metrics and performance data',
    },
  ];

  constructor(
    private api: ApiService,
    private pipelineSvc: PipelineService,
    private cdr: ChangeDetectorRef,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    this.api.health().subscribe((h) => {
      this.health = h;
      this.cdr.markForCheck();
    });
    this.api.getPipelineStatus().subscribe({
      next: (p) => {
        this.pipeline = p;
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.cdr.markForCheck();
      },
    });
    this.pipelineSvc.getStatus().subscribe((s) => {
      this.executionState = s.state;
      this.executionRunId = s.run_id || '';
      this.cdr.markForCheck();
    });
    this.pipelineSvc.getHistory().subscribe((h) => {
      this.recentHistory = h.slice(0, 5);
      this.cdr.markForCheck();
    });

    this.api.getSetupStatus().subscribe({
      next: (s) => {
        this.setupStatus = s;
        this.cdr.markForCheck();
      },
      error: () => {
        // Show wizard with all-false defaults so user can still see it
        this.setupStatus = { repo_configured: false, llm_configured: false, has_input_files: false, has_run_history: false };
        this.cdr.markForCheck();
      },
    });
  }

  setupCompleteCount(): number {
    return this.setupSteps.filter((s) => s.check()).length;
  }

  setupProgress(): number {
    return (this.setupCompleteCount() / 4) * 100;
  }

  allSetupComplete(): boolean {
    return this.setupCompleteCount() === 4;
  }

  dismissOnboarding(): void {
    this.onboardingDismissed = true;
    localStorage.setItem('onboarding_dismissed', 'true');
  }

  showOnboarding(): void {
    this.onboardingDismissed = false;
    localStorage.removeItem('onboarding_dismissed');
  }

  hasCompletedPhases(): boolean {
    return !!this.pipeline?.phases.some((p) => p.status === 'completed');
  }

  resetPhase(phaseId: string): void {
    this.pipelineSvc.previewReset([phaseId]).subscribe({
      next: (preview: ResetPreview) => {
        const msg =
          `Reset ${preview.phases_to_reset.length} phase(s):\n` +
          preview.phases_to_reset.join(', ') +
          `\n\n${preview.files_to_delete.length} file(s) will be archived and deleted.`;
        if (confirm(msg)) {
          this.pipelineSvc.executeReset([phaseId]).subscribe({
            next: (result) => {
              this.snackBar.open(
                `Reset ${result.reset_phases.length} phase(s), deleted ${result.deleted_count} file(s)`,
                'OK',
                { duration: 4000 },
              );
              this.refreshAll();
            },
            error: (err) => {
              this.snackBar.open(err?.error?.detail || 'Reset failed', 'OK', { duration: 4000 });
            },
          });
        }
      },
    });
  }

  resetAll(): void {
    this.pipelineSvc.previewReset(
      this.pipeline?.phases.filter((p) => p.status === 'completed').map((p) => p.id) || [],
    ).subscribe({
      next: (preview: ResetPreview) => {
        const msg =
          `Reset ALL completed phases:\n` +
          preview.phases_to_reset.join(', ') +
          `\n\n${preview.files_to_delete.length} file(s) will be archived and deleted.`;
        if (confirm(msg)) {
          this.pipelineSvc.resetAll().subscribe({
            next: (result) => {
              this.snackBar.open(
                `Reset all phases, deleted ${result.deleted_count} file(s)`,
                'OK',
                { duration: 4000 },
              );
              this.refreshAll();
            },
            error: (err) => {
              this.snackBar.open(err?.error?.detail || 'Reset failed', 'OK', { duration: 4000 });
            },
          });
        }
      },
    });
  }

  private refreshAll(): void {
    this.api.getPipelineStatus().subscribe((p) => {
      this.pipeline = p;
      this.cdr.markForCheck();
    });
    this.pipelineSvc.getHistory().subscribe((h) => {
      this.recentHistory = h.slice(0, 5);
      this.cdr.markForCheck();
    });
  }
}
