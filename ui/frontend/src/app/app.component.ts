import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

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
  ],
  template: `
    <mat-toolbar class="!bg-cg-navy !text-white sticky top-0 z-[1000]">
      <button mat-icon-button (click)="sidenav.toggle()">
        <mat-icon class="!text-white">menu</mat-icon>
      </button>
      <span class="font-medium ml-2">
        <span class="text-cg-vibrant">AI</span>CodeGenCrew
      </span>
      <span class="flex-1"></span>
      <span class="text-sm opacity-80">SDLC Dashboard</span>
    </mat-toolbar>

    <mat-sidenav-container class="sidenav-container">
      <mat-sidenav #sidenav mode="side" opened class="sidenav">
        <mat-nav-list>
          @for (item of navItems; track item.route) {
            <a mat-list-item [routerLink]="item.route" routerLinkActive="active-link">
              <mat-icon matListItemIcon>{{ item.icon }}</mat-icon>
              <span matListItemTitle>{{ item.label }}</span>
            </a>
          }
        </mat-nav-list>
      </mat-sidenav>

      <mat-sidenav-content class="content">
        <router-outlet />
      </mat-sidenav-content>
    </mat-sidenav-container>
  `,
  styles: [`
    .sidenav-container {
      height: calc(100vh - 64px);
    }
    .sidenav {
      width: 220px;
      background: var(--cg-navy);
    }
    .sidenav :deep(.mat-mdc-nav-list) {
      padding-top: 8px;
    }
    .sidenav :deep(.mat-mdc-list-item) {
      color: rgba(255, 255, 255, 0.7);
    }
    .sidenav :deep(.mat-mdc-list-item .mat-icon) {
      color: rgba(255, 255, 255, 0.7);
    }
    .sidenav :deep(.mat-mdc-list-item:hover) {
      background: rgba(255, 255, 255, 0.08);
    }
    .active-link {
      background: rgba(18, 171, 219, 0.15) !important;
    }
    .active-link :deep(.mat-mdc-list-item-title),
    .active-link :deep(.mat-icon) {
      color: var(--cg-vibrant) !important;
      font-weight: 500;
    }
    .content {
      padding: 0;
    }
  `],
})
export class AppComponent {
  navItems = [
    { route: '/dashboard', icon: 'dashboard', label: 'Dashboard' },
    { route: '/run', icon: 'play_circle', label: 'Run Pipeline' },
    { route: '/phases', icon: 'layers', label: 'Phases' },
    { route: '/knowledge', icon: 'folder_open', label: 'Knowledge' },
    { route: '/reports', icon: 'description', label: 'Reports' },
    { route: '/metrics', icon: 'analytics', label: 'Metrics' },
    { route: '/logs', icon: 'terminal', label: 'Logs' },
  ];
}
