import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatChipsModule } from '@angular/material/chips';
import { RouterLink } from '@angular/router';

import { ApiService, PipelineStatus, HealthResponse } from '../../services/api.service';

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
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 16px;
      border-radius: 8px;
      background: #f5f5f5;
      margin-bottom: 24px;
    }
    .status-banner.ok {
      background: #e8f5e9;
    }
    .spacer { flex: 1; }
    .status-icon {
      font-size: 40px;
      width: 40px;
      height: 40px;
    }
    .status-completed { color: #2e7d32; }
    .status-failed { color: #c62828; }
    .status-running { color: #1565c0; }
    .status-idle { color: #9e9e9e; }
    .output-icon {
      color: #1565c0;
      font-size: 18px;
      vertical-align: middle;
      margin-left: 8px;
    }
    .link-card {
      cursor: pointer;
    }
    .link-card:hover {
      box-shadow: 0 4px 8px rgba(0,0,0,0.12);
    }
    h2 {
      margin-top: 32px;
      margin-bottom: 16px;
      font-weight: 400;
    }
  `],
})
export class DashboardComponent implements OnInit {
  health: HealthResponse | null = null;
  pipeline: PipelineStatus | null = null;

  quickLinks = [
    { route: '/knowledge', icon: 'folder_open', label: 'Knowledge Explorer', description: 'Browse architecture facts and analysis' },
    { route: '/reports', icon: 'description', label: 'Reports', description: 'View development plans and codegen reports' },
    { route: '/metrics', icon: 'analytics', label: 'Metrics', description: 'Pipeline execution metrics' },
    { route: '/logs', icon: 'terminal', label: 'Logs', description: 'View application logs' },
  ];

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.health().subscribe(h => this.health = h);
    this.api.getPipelineStatus().subscribe(p => this.pipeline = p);
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
