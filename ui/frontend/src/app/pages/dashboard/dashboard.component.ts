import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatButtonModule } from '@angular/material/button';
import { RouterLink } from '@angular/router';

import { ApiService, PipelineStatus, HealthResponse } from '../../services/api.service';
import { PipelineService } from '../../services/pipeline.service';

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
    RouterLink,
  ],
  template: `
    <div class="page-container">
      <!-- Hero Section -->
      <div class="hero">
        <div class="hero-text">
          <h1 class="hero-title">
            <span class="hero-accent">AI</span>CodeGen<span class="hero-accent">Crew</span>
          </h1>
          <p class="hero-subtitle">Full SDLC Pipeline — from Architecture Analysis to Code Generation</p>
        </div>
        <div class="hero-stats">
          @if (health) {
            <div class="stat-pill" [class.stat-ok]="health.status === 'ok'" [class.stat-error]="health.status !== 'ok'">
              <mat-icon>{{ health.status === 'ok' ? 'check_circle' : 'error' }}</mat-icon>
              <span>Backend {{ health.status }}</span>
            </div>
            <div class="stat-pill" [class.stat-ok]="health.knowledge_dir_exists">
              <mat-icon>{{ health.knowledge_dir_exists ? 'check_circle' : 'cancel' }}</mat-icon>
              <span>Knowledge Base</span>
            </div>
          } @else {
            <div class="stat-pill stat-loading">
              <mat-spinner diameter="16"></mat-spinner>
              <span>Connecting...</span>
            </div>
          }
        </div>
      </div>

      <!-- Active Pipeline Banner -->
      @if (executionState && executionState !== 'idle') {
        <div class="active-banner" [class]="'banner-' + executionState" [routerLink]="'/run'">
          <div class="banner-left">
            <mat-icon class="banner-icon">
              {{ executionState === 'running' ? 'sync' : (executionState === 'completed' ? 'check_circle' : 'error') }}
            </mat-icon>
            <div>
              <div class="banner-title">Pipeline {{ executionState | titlecase }}</div>
              @if (executionRunId) {
                <div class="banner-sub">Run ID: {{ executionRunId }}</div>
              }
            </div>
          </div>
          @if (executionState === 'running') {
            <mat-progress-bar mode="indeterminate" class="banner-progress"></mat-progress-bar>
          }
          <mat-icon class="banner-arrow">arrow_forward</mat-icon>
        </div>
      }

      <!-- Phase Status -->
      <div class="section-header">
        <h2>Pipeline Phases</h2>
        <button mat-stroked-button color="primary" routerLink="/run">
          <mat-icon>rocket_launch</mat-icon> Run Pipeline
        </button>
      </div>

      @if (loading) {
        <div class="loading-center">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (pipeline && pipeline.phases.length > 0) {
        <div class="phase-grid">
          @for (phase of pipeline.phases; track phase.id; let i = $index) {
            <div class="phase-card" [class]="'phase-' + phase.status">
              <div class="phase-header">
                <div class="phase-number">{{ i }}</div>
                <div class="phase-meta">
                  <div class="phase-name">{{ phase.name }}</div>
                  <div class="phase-id">{{ phase.id }}</div>
                </div>
                <mat-icon class="phase-status-icon" [class]="'icon-' + phase.status">
                  {{ statusIcon(phase.status) }}
                </mat-icon>
              </div>
              <div class="phase-footer">
                <span class="status-chip" [class]="'status-' + phase.status">
                  {{ phase.status }}
                </span>
                @if (phase.output_exists) {
                  <span class="output-badge">
                    <mat-icon>inventory_2</mat-icon> Output
                  </span>
                }
              </div>
            </div>
          }
        </div>
      } @else {
        <div class="empty-state">
          <mat-icon class="empty-icon">inbox</mat-icon>
          <p>No pipeline data yet. Run your first pipeline to see status here.</p>
          <button mat-flat-button color="primary" routerLink="/run">
            <mat-icon>rocket_launch</mat-icon> Get Started
          </button>
        </div>
      }

      <!-- Quick Actions -->
      <h2 class="section-title">Quick Actions</h2>
      <div class="action-grid">
        @for (link of quickLinks; track link.route) {
          <a class="action-card" [routerLink]="link.route">
            <mat-icon class="action-icon">{{ link.icon }}</mat-icon>
            <div class="action-text">
              <div class="action-label">{{ link.label }}</div>
              <div class="action-desc">{{ link.description }}</div>
            </div>
            <mat-icon class="action-arrow">chevron_right</mat-icon>
          </a>
        }
      </div>
    </div>
  `,
  styles: [`
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
    }
    .hero-title {
      font-size: 28px;
      font-weight: 300;
      color: #fff;
      margin: 0 0 8px;
    }
    .hero-accent { color: var(--cg-vibrant); font-weight: 600; }
    .hero-subtitle {
      color: rgba(255,255,255,0.6);
      font-size: 14px;
      margin: 0;
    }
    .hero-stats {
      display: flex;
      gap: 12px;
      flex-shrink: 0;
    }
    .stat-pill {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 13px;
      font-weight: 500;
      background: rgba(255,255,255,0.08);
      color: rgba(255,255,255,0.6);
    }
    .stat-pill .mat-icon { font-size: 16px; width: 16px; height: 16px; }
    .stat-ok { color: var(--cg-success); background: rgba(40,167,69,0.15); }
    .stat-error { color: var(--cg-error); background: rgba(220,53,69,0.15); }
    .stat-loading { color: rgba(255,255,255,0.5); }

    /* Active Pipeline Banner */
    .active-banner {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 14px 20px;
      border-radius: 12px;
      margin-bottom: 24px;
      cursor: pointer;
      transition: transform 0.15s;
    }
    .active-banner:hover { transform: translateY(-1px); }
    .banner-running {
      background: rgba(0,112,173,0.08);
      border: 1px solid rgba(0,112,173,0.2);
    }
    .banner-completed {
      background: rgba(40,167,69,0.08);
      border: 1px solid rgba(40,167,69,0.2);
    }
    .banner-failed {
      background: rgba(220,53,69,0.08);
      border: 1px solid rgba(220,53,69,0.2);
    }
    .banner-cancelled {
      background: rgba(255,193,7,0.08);
      border: 1px solid rgba(255,193,7,0.2);
    }
    .banner-left { display: flex; align-items: center; gap: 12px; }
    .banner-icon { font-size: 28px; width: 28px; height: 28px; }
    .banner-running .banner-icon { color: var(--cg-blue); }
    .banner-completed .banner-icon { color: var(--cg-success); }
    .banner-failed .banner-icon { color: var(--cg-error); }
    @keyframes spin { to { transform: rotate(360deg); } }
    .banner-running .banner-icon { animation: spin 1.5s linear infinite; }
    .banner-title { font-weight: 500; font-size: 15px; }
    .banner-sub { font-size: 12px; color: var(--cg-gray-500); font-family: monospace; }
    .banner-progress { flex: 1; max-width: 200px; }
    .banner-arrow { margin-left: auto; color: var(--cg-gray-500); }

    /* Section Header */
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }
    .section-header h2 {
      font-weight: 400;
      font-size: 20px;
      margin: 0;
    }
    .section-title {
      font-weight: 400;
      font-size: 20px;
      margin: 32px 0 16px;
    }

    /* Phase Cards */
    .phase-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 12px;
    }
    .phase-card {
      background: #fff;
      border-radius: 12px;
      padding: 16px;
      border-left: 4px solid var(--cg-gray-200);
      transition: box-shadow 0.2s, transform 0.15s;
    }
    .phase-card:hover {
      box-shadow: 0 4px 12px rgba(0,0,0,0.08);
      transform: translateY(-1px);
    }
    .phase-completed { border-left-color: var(--cg-success); }
    .phase-failed { border-left-color: var(--cg-error); }
    .phase-running { border-left-color: var(--cg-blue); }
    .phase-ready { border-left-color: var(--cg-vibrant); }
    .phase-planned { border-left-color: var(--cg-gray-200); opacity: 0.6; }
    .phase-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }
    .phase-number {
      width: 28px;
      height: 28px;
      border-radius: 8px;
      background: var(--cg-gray-100);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 13px;
      font-weight: 600;
      color: var(--cg-gray-500);
      flex-shrink: 0;
    }
    .phase-meta { flex: 1; min-width: 0; }
    .phase-name {
      font-size: 14px;
      font-weight: 500;
      color: var(--cg-gray-900);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .phase-id {
      font-size: 11px;
      color: var(--cg-gray-500);
      font-family: monospace;
    }
    .phase-status-icon { font-size: 22px; width: 22px; height: 22px; }
    .icon-completed { color: var(--cg-success); }
    .icon-failed { color: var(--cg-error); }
    .icon-running { color: var(--cg-blue); }
    .icon-ready { color: var(--cg-vibrant); }
    .icon-planned { color: var(--cg-gray-200); }
    .icon-idle { color: var(--cg-gray-200); }
    .phase-footer {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .output-badge {
      display: inline-flex;
      align-items: center;
      gap: 3px;
      font-size: 11px;
      color: var(--cg-blue);
    }
    .output-badge .mat-icon { font-size: 14px; width: 14px; height: 14px; }

    /* Loading */
    .loading-center {
      display: flex;
      justify-content: center;
      padding: 48px 0;
    }

    /* Empty State */
    .empty-state {
      text-align: center;
      padding: 48px 24px;
      background: #fff;
      border-radius: 12px;
      border: 2px dashed var(--cg-gray-200);
    }
    .empty-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: var(--cg-gray-200);
      margin-bottom: 12px;
    }
    .empty-state p {
      color: var(--cg-gray-500);
      margin-bottom: 16px;
    }

    /* Quick Actions */
    .action-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 12px;
    }
    .action-card {
      display: flex;
      align-items: center;
      gap: 14px;
      padding: 16px;
      background: #fff;
      border-radius: 12px;
      text-decoration: none;
      color: inherit;
      cursor: pointer;
      transition: box-shadow 0.2s, transform 0.15s;
    }
    .action-card:hover {
      box-shadow: 0 4px 12px rgba(0,0,0,0.08);
      transform: translateY(-1px);
    }
    .action-icon {
      font-size: 24px;
      width: 24px;
      height: 24px;
      color: var(--cg-blue);
    }
    .action-text { flex: 1; }
    .action-label { font-weight: 500; font-size: 14px; }
    .action-desc { font-size: 12px; color: var(--cg-gray-500); margin-top: 2px; }
    .action-arrow { color: var(--cg-gray-200); }
  `],
})
export class DashboardComponent implements OnInit {
  health: HealthResponse | null = null;
  pipeline: PipelineStatus | null = null;
  loading = true;

  executionState: string = 'idle';
  executionRunId: string = '';

  quickLinks = [
    { route: '/knowledge', icon: 'psychology', label: 'Knowledge Explorer', description: 'Browse architecture facts, components, and analysis results' },
    { route: '/reports', icon: 'summarize', label: 'Development Plans', description: 'View generated plans and codegen reports' },
    { route: '/metrics', icon: 'monitoring', label: 'Pipeline Metrics', description: 'Execution metrics, token usage, and performance' },
  ];

  constructor(private api: ApiService, private pipelineSvc: PipelineService, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.api.health().subscribe(h => { this.health = h; this.cdr.markForCheck(); });
    this.api.getPipelineStatus().subscribe({
      next: p => { this.pipeline = p; this.loading = false; this.cdr.markForCheck(); },
      error: () => { this.loading = false; this.cdr.markForCheck(); },
    });
    this.pipelineSvc.getStatus().subscribe(s => {
      this.executionState = s.state;
      this.executionRunId = s.run_id || '';
      this.cdr.markForCheck();
    });
  }

  statusIcon(status: string): string {
    switch (status) {
      case 'completed': return 'check_circle';
      case 'failed': return 'error';
      case 'running': return 'sync';
      case 'ready': return 'play_circle';
      case 'planned': return 'schedule';
      default: return 'radio_button_unchecked';
    }
  }
}
