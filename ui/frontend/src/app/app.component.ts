import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatToolbarModule,
    MatSidenavModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
  ],
  template: `
    <mat-toolbar class="app-toolbar sticky top-0 z-[1000]">
      <button mat-icon-button (click)="sidenav.toggle()" matTooltip="Toggle menu">
        <mat-icon class="text-white">menu</mat-icon>
      </button>
      <span class="brand font-medium ml-3">
        <span class="text-cg-vibrant font-bold">AI</span><span class="text-white">CodeGen</span
        ><span class="text-cg-vibrant">Crew</span>
      </span>
      <span class="flex-1"></span>
      <span class="toolbar-badge">SDLC Dashboard</span>
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
            <div class="version-badge">
              <mat-icon class="version-icon">code</mat-icon>
              <span>v0.3.0</span>
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
      .brand {
        font-size: 18px;
        letter-spacing: -0.3px;
      }
      .toolbar-badge {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        opacity: 0.6;
        font-weight: 500;
      }
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
        padding: 12px 16px;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
      }
      .version-badge {
        display: flex;
        align-items: center;
        gap: 6px;
        color: rgba(255, 255, 255, 0.3);
        font-size: 11px;
        font-family: monospace;
      }
      .version-icon {
        font-size: 14px;
        width: 14px;
        height: 14px;
      }
      .content-area {
        background: var(--cg-gray-50);
      }
    `,
  ],
})
export class AppComponent {
  navGroups = [
    {
      label: 'Operations',
      items: [
        { route: '/dashboard', icon: 'space_dashboard', label: 'Dashboard' },
        { route: '/run', icon: 'rocket_launch', label: 'Run Pipeline' },
        { route: '/inputs', icon: 'upload_file', label: 'Input Files' },
        { route: '/collectors', icon: 'hub', label: 'Collectors' },
      ],
    },
    {
      label: 'Explore',
      items: [
        { route: '/phases', icon: 'account_tree', label: 'Phases' },
        { route: '/knowledge', icon: 'psychology', label: 'Knowledge' },
        { route: '/reports', icon: 'summarize', label: 'Reports' },
      ],
    },
    {
      label: 'Monitor',
      items: [
        { route: '/metrics', icon: 'monitoring', label: 'Metrics' },
        { route: '/logs', icon: 'receipt_long', label: 'Logs' },
      ],
    },
  ];
}
