import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { NotificationService } from './services/notification.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatToolbarModule,
    MatSidenavModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    MatProgressBarModule,
  ],
  template: `
    <mat-toolbar class="app-toolbar sticky top-0 z-[1000]">
      <button mat-icon-button (click)="sidenav.toggle()" matTooltip="Toggle menu">
        <mat-icon class="text-white">menu</mat-icon>
      </button>
      <a routerLink="/dashboard" class="brand-link">
        <span class="brand">
          <span class="brand-ai">AI</span>CodeGen<span class="brand-ai">Crew</span>
        </span>
        <span class="brand-sub">SDLC Dashboard</span>
      </a>
      <span class="flex-1"></span>

      <!-- Pipeline Status Indicator -->
      @if (notifSvc.notification$ | async; as notif) {
        @if (notif.state === 'running') {
          <a class="status-indicator status-running" routerLink="/run"
             matTooltip="Pipeline running — click to view">
            <div class="mini-progress-wrap">
              <mat-progress-bar mode="determinate" [value]="notif.progressPercent"
                class="mini-progress-bar"></mat-progress-bar>
            </div>
            <span class="mini-progress-pct">{{ notif.progressPercent | number:'1.0-0' }}%</span>
            @if (notif.etaSeconds != null && notif.etaSeconds > 0) {
              <span class="mini-eta">~{{ formatEta(notif.etaSeconds) }}</span>
            }
          </a>
        }
        @if (notif.state === 'completed') {
          <div class="status-indicator status-completed" matTooltip="Pipeline completed">
            <span class="status-dot-static dot-green"></span>
            <span class="status-text">Done</span>
          </div>
        }
        @if (notif.state === 'failed') {
          <button class="status-indicator status-failed" (click)="notifSvc.dismiss()" matTooltip="Click to dismiss">
            <span class="status-dot-static dot-red"></span>
            <span class="status-text">Failed</span>
          </button>
        }
      }

      <div class="toolbar-brand">
        <span class="toolbar-tagline">Make it real</span>
        <img src="assets/logos/Capgemini_Primary-spade_Capgemini-white.png" alt="Capgemini" class="toolbar-logo" />
      </div>
    </mat-toolbar>

    <mat-sidenav-container class="sidenav-container">
      <mat-sidenav #sidenav mode="side" opened class="sidenav">
        <div class="sidenav-inner">
          <div class="nav-content">
            @for (group of navGroups; track group.label) {
              <div class="nav-group-label">{{ group.label }}</div>
              <mat-nav-list class="nav-section">
                @for (item of group.items; track item.route) {
                  <a mat-list-item [routerLink]="item.route" routerLinkActive="active-link">
                    <mat-icon matListItemIcon>{{ item.icon }}</mat-icon>
                    <span matListItemTitle>{{ item.label }}</span>
                  </a>
                }
              </mat-nav-list>
            }
          </div>
          <div class="sidenav-footer">
            <div class="footer-row">
              <span class="footer-legal">&copy; 2026 Capgemini</span>
              <span class="footer-sep"></span>
              <span class="footer-version">v0.3.0</span>
            </div>
          </div>
        </div>
      </mat-sidenav>

      <mat-sidenav-content class="p-0 content-area">
        <router-outlet />
      </mat-sidenav-content>
    </mat-sidenav-container>
  `,
  styles: [
    `
      .app-toolbar {
        background: var(--cg-navy) !important;
        color: #fff !important;
        height: 56px;
      }
      .brand-link {
        text-decoration: none;
        display: flex;
        align-items: baseline;
        gap: 10px;
        margin-left: 12px;
      }
      .brand {
        font-size: 17px;
        font-weight: 500;
        color: #fff;
        letter-spacing: -0.3px;
      }
      .brand-ai {
        color: var(--cg-vibrant);
        font-weight: 700;
      }
      .brand-sub {
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: rgba(255, 255, 255, 0.35);
        font-weight: 500;
      }
      .toolbar-brand {
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .toolbar-logo {
        height: 24px;
      }
      .toolbar-tagline {
        font-size: 11px;
        font-style: italic;
        color: rgba(255, 255, 255, 0.45);
        letter-spacing: 0.5px;
        white-space: nowrap;
      }

      /* Status Indicator */
      .status-indicator {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 16px;
        margin-right: 12px;
        font-size: 12px;
        font-weight: 500;
        border: none;
        cursor: default;
        background: transparent;
      }
      .status-running {
        background: rgba(0, 112, 173, 0.15);
        color: var(--cg-vibrant);
      }
      .status-completed {
        background: rgba(40, 167, 69, 0.15);
        color: var(--cg-success, #28a745);
      }
      .status-failed {
        background: rgba(220, 53, 69, 0.15);
        color: var(--cg-error, #dc3545);
        cursor: pointer;
      }
      .status-failed:hover {
        background: rgba(220, 53, 69, 0.25);
      }
      .status-text {
        font-size: 12px;
      }

      /* Mini progress bar in toolbar */
      .mini-progress-wrap {
        width: 80px;
        height: 4px;
        border-radius: 2px;
        overflow: hidden;
      }
      .mini-progress-bar ::ng-deep .mdc-linear-progress__bar-inner {
        border-color: var(--cg-vibrant) !important;
      }
      .mini-progress-bar ::ng-deep .mdc-linear-progress__buffer-bar {
        background-color: rgba(255, 255, 255, 0.15) !important;
      }
      .mini-progress-pct {
        font-size: 11px;
        font-family: 'Cascadia Code', 'Fira Code', monospace;
        font-weight: 600;
        color: var(--cg-vibrant);
        min-width: 28px;
      }
      .mini-eta {
        font-size: 10px;
        color: rgba(255, 255, 255, 0.45);
        font-family: 'Cascadia Code', 'Fira Code', monospace;
      }

      /* Pulsing dot */
      .status-dot-pulse {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--cg-vibrant);
        animation: pulse-dot 1.5s ease-in-out infinite;
      }
      @keyframes pulse-dot {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(0.8); }
      }

      /* Static dots */
      .status-dot-static {
        width: 8px;
        height: 8px;
        border-radius: 50%;
      }
      .dot-green { background: var(--cg-success, #28a745); }
      .dot-red { background: var(--cg-error, #dc3545); }

      .sidenav-container {
        height: calc(100vh - 56px);
      }
      .sidenav {
        width: 230px;
        background: var(--cg-navy);
        border-right: none !important;
      }
      .sidenav-inner {
        display: flex;
        flex-direction: column;
        height: 100%;
      }
      .nav-content {
        flex: 1;
        overflow-y: auto;
        padding-top: 8px;
      }
      .nav-group-label {
        padding: 16px 20px 4px;
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: rgba(255, 255, 255, 0.35);
      }
      .nav-section {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
      }
      .nav-section ::ng-deep .mat-mdc-list-item {
        color: rgba(255, 255, 255, 0.7);
        height: 44px !important;
        margin: 1px 8px;
        border-radius: 8px;
      }
      .nav-section ::ng-deep .mdc-list-item__primary-text {
        color: rgba(255, 255, 255, 0.7) !important;
      }
      .nav-section ::ng-deep .mat-mdc-list-item .mat-icon {
        color: rgba(255, 255, 255, 0.5);
        font-size: 20px;
        width: 20px;
        height: 20px;
      }
      .nav-section ::ng-deep .mat-mdc-list-item:hover {
        background: rgba(255, 255, 255, 0.06);
      }
      .active-link {
        background: rgba(18, 171, 219, 0.12) !important;
      }
      .active-link ::ng-deep .mdc-list-item__primary-text {
        color: var(--cg-vibrant) !important;
        font-weight: 500;
      }
      .active-link ::ng-deep .mat-icon {
        color: var(--cg-vibrant) !important;
      }
      .sidenav-footer {
        padding: 16px 20px;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
      }
      .footer-row {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .footer-legal {
        font-size: 10px;
        color: rgba(255, 255, 255, 0.3);
      }
      .footer-sep {
        width: 3px; height: 3px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.15);
      }
      .footer-version {
        font-size: 10px;
        font-family: monospace;
        color: rgba(255, 255, 255, 0.25);
      }
      .content-area {
        background: var(--cg-gray-50);
      }
    `,
  ],
})
export class AppComponent {
  constructor(public notifSvc: NotificationService) {}

  formatEta(seconds: number): string {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const min = Math.floor(seconds / 60);
    const sec = Math.round(seconds % 60);
    return `${min}m ${sec}s`;
  }

  navGroups = [
    {
      label: 'Operations',
      items: [
        { route: '/dashboard', icon: 'space_dashboard', label: 'Dashboard' },
        { route: '/run', icon: 'rocket_launch', label: 'Run Pipeline' },
        { route: '/inputs', icon: 'upload_file', label: 'Input Files' },
        { route: '/collectors', icon: 'hub', label: 'Collectors' },
        { route: '/settings', icon: 'settings', label: 'Settings' },
      ],
    },
    {
      label: 'Explore',
      items: [
        { route: '/phases', icon: 'account_tree', label: 'Phases' },
        { route: '/knowledge', icon: 'psychology', label: 'Knowledge' },
        { route: '/reports', icon: 'summarize', label: 'Reports' },
        { route: '/outputs', icon: 'code', label: 'Outputs' },
      ],
    },
    {
      label: 'Monitor',
      items: [
        { route: '/metrics', icon: 'monitoring', label: 'Metrics' },
        { route: '/logs', icon: 'receipt_long', label: 'Logs' },
        { route: '/history', icon: 'history', label: 'History' },
      ],
    },
  ];
}
