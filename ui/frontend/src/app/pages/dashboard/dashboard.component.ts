import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatChipsModule } from '@angular/material/chips';
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
    MatChipsModule,
    RouterLink,
  ],
  template: `
    <div class="page-container">
      <h1 class="page-title">Dashboard</h1>

      @if (health) {
        <div class="status-banner" [class.ok]="health.status === 'ok'">
          <mat-icon>{{ health.status === 'ok' ? 'check_circle' : 'error' }}</mat-icon>
          <span>Backend: {{ health.status }} | Version: {{ health.version }}</span>
          <span class="spacer"></span>
          <mat-chip-set>
            <mat-chip [highlighted]="health.knowledge_dir_exists">Knowledge</mat-chip>
            <mat-chip [highlighted]="health.phases_config_exists">Config</mat-chip>
          </mat-chip-set>
        </div>
      }

      @if (executionState && executionState !== 'idle') {
        <div class="running-banner" [class]="'banner-' + executionState" [routerLink]="'/run'">
          <mat-icon>{{ executionState === 'running' ? 'hourglass_empty' : (executionState === 'completed' ? 'check_circle' : 'error') }}</mat-icon>
          <span>Pipeline {{ executionState }} {{ executionRunId ? '(Run: ' + executionRunId + ')' : '' }}</span>
          @if (executionState === 'running') {
            <mat-progress-bar mode="indeterminate" class="banner-progress"></mat-progress-bar>
          }
        </div>
      }

      @if (pipeline) {
        <h2>Pipeline Status</h2>
        <div class="card-grid">
          @for (phase of pipeline.phases; track phase.id) {
            <mat-card>
              <mat-card-header>
                <mat-icon mat-card-avatar [class]="'status-icon status-' + phase.status">
                  {{ statusIcon(phase.status) }}
                </mat-icon>
                <mat-card-title>{{ phase.name }}</mat-card-title>
                <mat-card-subtitle>{{ phase.id }}</mat-card-subtitle>
              </mat-card-header>
              <mat-card-content>
                <span class="status-chip" [class]="'status-' + phase.status">
                  {{ phase.status }}
                </span>
                @if (phase.output_exists) {
                  <mat-icon class="output-icon">folder</mat-icon>
                }
              </mat-card-content>
            </mat-card>
          }
        </div>
      }

      <h2>Quick Links</h2>
      <div class="card-grid">
        @for (link of quickLinks; track link.route) {
          <mat-card class="link-card" [routerLink]="link.route">
            <mat-card-header>
              <mat-icon mat-card-avatar>{{ link.icon }}</mat-icon>
              <mat-card-title>{{ link.label }}</mat-card-title>
              <mat-card-subtitle>{{ link.description }}</mat-card-subtitle>
            </mat-card-header>
          </mat-card>
        }
      </div>
    </div>
  `,
  styles: [`
    .status-banner {
      @apply flex items-center gap-2 px-4 py-3 rounded-lg mb-6;
      background: var(--cg-gray-100);
    }
    .status-banner.ok {
      background: rgba(40, 167, 69, 0.1);
    }
    .spacer { flex: 1; }
    .status-icon { font-size: 40px; width: 40px; height: 40px; }
    .status-completed { color: var(--cg-success); }
    .status-failed { color: var(--cg-error); }
    .status-running { color: var(--cg-blue); }
    .status-idle { color: var(--cg-gray-500); }
    .output-icon {
      color: var(--cg-blue);
      font-size: 18px;
      vertical-align: middle;
      margin-left: 8px;
    }
    .link-card {
      @apply cursor-pointer transition-shadow duration-200;
    }
    .link-card:hover {
      @apply shadow-lg;
    }
    .running-banner {
      @apply flex items-center gap-2 px-4 py-3 rounded-lg mb-4 cursor-pointer;
    }
    .banner-running { background: rgba(0, 112, 173, 0.1); color: var(--cg-blue); }
    .banner-completed { background: rgba(40, 167, 69, 0.1); color: var(--cg-success); }
    .banner-failed { background: rgba(220, 53, 69, 0.1); color: var(--cg-error); }
    .banner-cancelled { background: rgba(255, 193, 7, 0.15); color: #d4a017; }
    .banner-progress { flex: 1; max-width: 200px; }
    h2 {
      @apply mt-8 mb-4 font-normal;
    }
  `],
})
export class DashboardComponent implements OnInit {
  health: HealthResponse | null = null;
  pipeline: PipelineStatus | null = null;

  executionState: string = 'idle';
  executionRunId: string = '';

  quickLinks = [
    { route: '/run', icon: 'play_circle', label: 'Run Pipeline', description: 'Execute pipeline presets or individual phases' },
    { route: '/knowledge', icon: 'folder_open', label: 'Knowledge Explorer', description: 'Browse architecture facts and analysis' },
    { route: '/reports', icon: 'description', label: 'Reports', description: 'View development plans and codegen reports' },
    { route: '/metrics', icon: 'analytics', label: 'Metrics', description: 'Pipeline execution metrics' },
    { route: '/logs', icon: 'terminal', label: 'Logs', description: 'View application logs' },
  ];

  constructor(private api: ApiService, private pipelineSvc: PipelineService) {}

  ngOnInit(): void {
    this.api.health().subscribe(h => this.health = h);
    this.api.getPipelineStatus().subscribe(p => this.pipeline = p);
    this.pipelineSvc.getStatus().subscribe(s => {
      this.executionState = s.state;
      this.executionRunId = s.run_id || '';
    });
  }

  statusIcon(status: string): string {
    switch (status) {
      case 'completed': return 'check_circle';
      case 'failed': return 'error';
      case 'running': return 'hourglass_empty';
      default: return 'radio_button_unchecked';
    }
  }
}
