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
    <mat-toolbar color="primary" class="app-toolbar">
      <button mat-icon-button (click)="sidenav.toggle()">
        <mat-icon>menu</mat-icon>
      </button>
      <span class="brand">AICodeGenCrew</span>
      <span class="spacer"></span>
      <span class="subtitle">SDLC Dashboard</span>
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
    .app-toolbar {
      position: sticky;
      top: 0;
      z-index: 1000;
    }
    .brand {
      font-weight: 500;
      margin-left: 8px;
    }
    .spacer {
      flex: 1;
    }
    .subtitle {
      font-size: 14px;
      opacity: 0.8;
    }
    .sidenav-container {
      height: calc(100vh - 64px);
    }
    .sidenav {
      width: 220px;
    }
    .content {
      padding: 0;
    }
    .active-link {
      background: rgba(0, 0, 0, 0.04);
      font-weight: 500;
    }
  `],
})
export class AppComponent {
  navItems = [
    { route: '/dashboard', icon: 'dashboard', label: 'Dashboard' },
    { route: '/phases', icon: 'layers', label: 'Phases' },
    { route: '/knowledge', icon: 'folder_open', label: 'Knowledge' },
    { route: '/reports', icon: 'description', label: 'Reports' },
    { route: '/metrics', icon: 'analytics', label: 'Metrics' },
    { route: '/logs', icon: 'terminal', label: 'Logs' },
  ];
}
