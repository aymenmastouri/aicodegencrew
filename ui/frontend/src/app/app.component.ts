import { Component, OnInit, OnDestroy, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule, MatSidenav } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { NotificationService } from './services/notification.service';
import { ThemeService } from './services/theme.service';

type SidenavMode = 'full' | 'rail' | 'hidden' | 'overlay';

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
      <button
        mat-icon-button
        (click)="toggleSidenav()"
        [attr.aria-label]="
          sidenavLayout === 'hidden' ? 'Show menu' : sidenavLayout === 'rail' ? 'Hide menu' : 'Collapse menu'
        "
        [matTooltip]="
          sidenavLayout === 'hidden' ? 'Show menu' : sidenavLayout === 'rail' ? 'Hide menu' : 'Collapse menu'
        "
      >
        <mat-icon class="text-white">{{ sidenavLayout === 'hidden' ? 'menu_open' : 'menu' }}</mat-icon>
      </button>
      <a routerLink="/dashboard" class="brand-link">
        <span class="brand"> <span class="brand-ai">SDLC</span> Pilot </span>
        <span class="brand-sub">AI-Powered Development Lifecycle Automation</span>
      </a>
      <span class="flex-1"></span>

      <!-- Notification Permission -->
      @if (notifSvc.notificationPermission() === 'default') {
        <button mat-icon-button (click)="notifSvc.requestPermission()" matTooltip="Enable notifications">
          <mat-icon class="text-white">notifications_none</mat-icon>
        </button>
      }

      <!-- Theme Toggle -->
      <button
        mat-icon-button
        (click)="themeSvc.toggle()"
        [matTooltip]="themeSvc.isDark() ? 'Switch to light mode' : 'Switch to dark mode'"
      >
        <mat-icon class="text-white">{{ themeSvc.isDark() ? 'light_mode' : 'dark_mode' }}</mat-icon>
      </button>

      <!-- Pipeline Status Indicator -->
      @if (notifSvc.notification$ | async; as notif) {
        @if (notif.state === 'running') {
          <a class="status-indicator status-running" routerLink="/run" matTooltip="Pipeline running — click to view">
            <div class="mini-progress-wrap">
              <mat-progress-bar
                mode="determinate"
                [value]="notif.progressPercent"
                class="mini-progress-bar"
              ></mat-progress-bar>
            </div>
            <span class="mini-progress-pct">{{ notif.progressPercent | number: '1.0-0' }}%</span>
            @if (notif.etaSeconds !== null && notif.etaSeconds !== undefined && notif.etaSeconds > 0) {
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
    </mat-toolbar>

    <mat-sidenav-container class="sidenav-container">
      <mat-sidenav
        #sidenav
        [mode]="sidenavLayout === 'overlay' ? 'over' : 'side'"
        [opened]="(sidenavLayout !== 'overlay' && sidenavLayout !== 'hidden') || sidenavOpenOverlay"
        (closedStart)="onSidenavClosed()"
        class="sidenav"
        [class.sidenav-rail]="sidenavLayout === 'rail' && !railExpanded"
        [class.sidenav-full]="sidenavLayout === 'full' || (sidenavLayout === 'rail' && railExpanded)"
        [class.sidenav-hidden]="sidenavLayout === 'hidden'"
      >
        <div class="sidenav-inner" (mouseenter)="onRailHover(true)" (mouseleave)="onRailHover(false)">
          <div class="nav-content">
            @for (group of navGroups; track group.label) {
              <div class="nav-group-label">{{ group.label }}</div>
              <mat-nav-list class="nav-section">
                @for (item of group.items; track item.route) {
                  <a
                    mat-list-item
                    [routerLink]="item.route"
                    routerLinkActive="active-link"
                    (click)="onNavItemClick()"
                    [matTooltip]="sidenavLayout === 'rail' && !railExpanded ? item.label : ''"
                    matTooltipPosition="right"
                  >
                    <mat-icon matListItemIcon>{{ item.icon }}</mat-icon>
                    <span matListItemTitle class="nav-label">{{ item.label }}</span>
                  </a>
                }
              </mat-nav-list>
            }
          </div>
          <div class="sidenav-footer">
            <div class="footer-row">
              <span class="footer-legal">&copy; 2026 Aymen Mastouri</span>
              <span class="footer-sep"></span>
              <span class="footer-version">v0.6.2</span>
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
        color: rgba(255, 255, 255, 0.65);
        font-weight: 500;
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
        color: rgba(255, 255, 255, 0.65);
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
        0%,
        100% {
          opacity: 1;
          transform: scale(1);
        }
        50% {
          opacity: 0.5;
          transform: scale(0.8);
        }
      }

      /* Static dots */
      .status-dot-static {
        width: 8px;
        height: 8px;
        border-radius: 50%;
      }
      .dot-green {
        background: var(--cg-success, #28a745);
      }
      .dot-red {
        background: var(--cg-error, #dc3545);
      }

      .sidenav-container {
        height: calc(100vh - 56px);
      }

      /* Sidenav — responsive width via classes */
      .sidenav {
        background: var(--cg-navy);
        border-right: none !important;
        transition: width 0.2s ease;
        overflow-x: hidden;
      }
      .sidenav-full {
        width: 230px;
      }
      .sidenav-rail {
        width: 64px;
      }
      /* When neither class is set (initial or overlay), default to full */
      .sidenav:not(.sidenav-rail):not(.sidenav-full) {
        width: 230px;
      }

      .sidenav-inner {
        display: flex;
        flex-direction: column;
        height: 100%;
      }
      .nav-content {
        flex: 1;
        overflow-y: auto;
        overflow-x: hidden;
        padding-top: 8px;
        scrollbar-color: rgba(255, 255, 255, 0.1) transparent;
      }
      .nav-content::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.1);
      }
      .nav-content::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.2);
      }

      /* Nav group labels — hidden in rail mode */
      .nav-group-label {
        padding: 16px 20px 4px;
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: rgba(255, 255, 255, 0.6);
        white-space: nowrap;
        overflow: hidden;
        transition: opacity 0.15s ease;
      }
      .sidenav-rail .nav-group-label {
        opacity: 0;
        height: 8px;
        padding: 4px 0;
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

      /* Nav label — hidden in rail mode */
      .nav-label {
        white-space: nowrap;
        overflow: hidden;
        transition: opacity 0.15s ease;
      }
      .sidenav-rail .nav-label {
        opacity: 0;
        width: 0;
      }

      /* Rail mode: center icons */
      .sidenav-rail .nav-section ::ng-deep .mat-mdc-list-item {
        margin: 1px 4px;
      }

      .sidenav-footer {
        padding: 16px 20px;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
        white-space: nowrap;
        overflow: hidden;
      }
      .sidenav-rail .sidenav-footer {
        opacity: 0;
        padding: 8px;
        height: 0;
        overflow: hidden;
      }
      .footer-row {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .footer-legal {
        font-size: 10px;
        color: rgba(255, 255, 255, 0.6);
      }
      .footer-sep {
        width: 3px;
        height: 3px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.15);
      }
      .footer-version {
        font-size: 10px;
        font-family: monospace;
        color: rgba(255, 255, 255, 0.6);
      }
      .content-area {
        background: var(--cg-gray-50);
        overflow-x: hidden;
      }

      /* Hide tagline on small screens */
      @media (max-width: 768px) {
        .brand-sub {
          display: none;
        }
      }
    `,
  ],
})
export class AppComponent implements OnInit, OnDestroy {
  @ViewChild('sidenav') sidenav!: MatSidenav;

  sidenavLayout: SidenavMode = 'full';
  sidenavOpenOverlay = false;
  railExpanded = false;
  private userToggled = false;

  private mediaOverlay!: MediaQueryList;
  private mediaRail!: MediaQueryList;
  private mediaFull!: MediaQueryList;

  constructor(
    public notifSvc: NotificationService,
    public themeSvc: ThemeService,
  ) {}

  ngOnInit(): void {
    // < 1024px → overlay (hidden by default)
    this.mediaOverlay = window.matchMedia('(max-width: 1023px)');
    // 1024–1439px → rail
    this.mediaRail = window.matchMedia('(min-width: 1024px) and (max-width: 1439px)');
    // >= 1440px → full
    this.mediaFull = window.matchMedia('(min-width: 1440px)');

    this.updateLayout();

    this.mediaOverlay.addEventListener('change', this.onMediaChange);
    this.mediaRail.addEventListener('change', this.onMediaChange);
    this.mediaFull.addEventListener('change', this.onMediaChange);
  }

  ngOnDestroy(): void {
    this.mediaOverlay?.removeEventListener('change', this.onMediaChange);
    this.mediaRail?.removeEventListener('change', this.onMediaChange);
    this.mediaFull?.removeEventListener('change', this.onMediaChange);
  }

  private onMediaChange = (): void => {
    this.updateLayout();
  };

  private updateLayout(): void {
    this.userToggled = false;
    this.railExpanded = false;
    if (this.mediaFull.matches) {
      this.sidenavLayout = 'full';
    } else if (this.mediaRail.matches) {
      this.sidenavLayout = 'rail';
    } else {
      this.sidenavLayout = 'overlay';
      this.sidenavOpenOverlay = false;
    }
  }

  toggleSidenav(): void {
    this.userToggled = true;
    this.railExpanded = false;
    if (this.sidenavLayout === 'overlay') {
      this.sidenavOpenOverlay = !this.sidenavOpenOverlay;
    } else if (this.sidenavLayout === 'full') {
      this.sidenavLayout = 'rail';
    } else if (this.sidenavLayout === 'rail') {
      this.sidenavLayout = 'hidden';
    } else {
      // hidden → full
      this.sidenavLayout = 'full';
    }
  }

  onSidenavClosed(): void {
    this.sidenavOpenOverlay = false;
  }

  onNavItemClick(): void {
    // Close overlay sidenav on navigation
    if (this.sidenavLayout === 'overlay') {
      this.sidenavOpenOverlay = false;
    }
  }

  onRailHover(hovering: boolean): void {
    if (this.sidenavLayout === 'rail') {
      this.railExpanded = hovering;
    } else if (this.sidenavLayout === 'hidden' && hovering) {
      // Peek: temporarily show rail on hover when hidden
      this.railExpanded = false;
    }
  }

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
        { route: '/mcps', icon: 'extension', label: 'MCP Servers' },
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
