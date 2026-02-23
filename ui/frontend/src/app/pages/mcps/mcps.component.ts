import { Component, OnInit, OnDestroy, ChangeDetectorRef, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { catchError, of } from 'rxjs';

interface MCPMetadata {
  id: string;
  name: string;
  package: string;
  description: string;
  use_cases: string[];
  phases: number[];
  tools: string[];
  status: string;
  requires_api_key: boolean;
  api_key_env_var: string | null;
}

interface MCPSummary {
  total: number;
  available: number;
  requires_api_key: number;
  not_installed: number;
  by_phase: Record<number, string[]>;
}

interface MCPListResponse {
  mcps: MCPMetadata[];
  summary: MCPSummary;
}

@Component({
  selector: 'app-mcps',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatExpansionModule,
    MatSnackBarModule,
  ],
  template: `
    <div class="page-container">
      <div class="page-header">
        <mat-icon class="page-icon">extension</mat-icon>
        <div>
          <h1 class="page-title">MCP Servers</h1>
          <p class="page-subtitle">Model Context Protocol integrations for enhanced agent capabilities</p>
        </div>
      </div>

      @if (loading) {
        <div class="loading-center">
          <mat-spinner diameter="36"></mat-spinner>
        </div>
      } @else {
        <!-- Stats Bar -->
        <div class="stats-bar">
          <div class="stat-item">
            <mat-icon>extension</mat-icon>
            <span class="stat-value">{{ summary.total }}</span>
            <span class="stat-label">Total MCPs</span>
          </div>
          <div class="stat-item">
            <mat-icon>check_circle</mat-icon>
            <span class="stat-value">{{ summary.available }}</span>
            <span class="stat-label">Available</span>
          </div>
          <div class="stat-item">
            <mat-icon>key</mat-icon>
            <span class="stat-value">{{ summary.requires_api_key }}</span>
            <span class="stat-label">Requires API Key</span>
          </div>
          <div class="stat-item">
            <mat-icon>build</mat-icon>
            <span class="stat-value">{{ phaseCount }}</span>
            <span class="stat-label">Phases</span>
          </div>
        </div>

        <div class="grid">
          @for (mcp of mcps; track mcp.id) {
            <mat-card class="mcp-card">
              <mat-card-header>
                <mat-icon
                  mat-card-avatar
                  [class.icon-available]="mcp.status === 'available'"
                  [class.icon-key]="mcp.status === 'requires_api_key'"
                >
                  {{ getIcon(mcp.id) }}
                </mat-icon>
                <mat-card-title>{{ mcp.name }}</mat-card-title>
                <mat-card-subtitle>{{ mcp.package }}</mat-card-subtitle>
              </mat-card-header>
              <mat-card-content>
                <p class="mcp-description">{{ mcp.description }}</p>

                <div class="mcp-chips">
                  <span class="chip chip-phases">
                    <mat-icon class="chip-icon">layers</mat-icon>
                    {{ getPhaseNames(mcp.phases) }}
                  </span>
                  <span class="chip chip-tools">
                    <mat-icon class="chip-icon">build_circle</mat-icon>
                    {{ mcp.tools.length }} tools
                  </span>
                  <span
                    class="chip"
                    [class.chip-available]="mcp.status === 'available'"
                    [class.chip-key]="mcp.status === 'requires_api_key'"
                  >
                    <mat-icon class="chip-icon">{{ mcp.status === 'available' ? 'check_circle' : 'key' }}</mat-icon>
                    {{ mcp.status === 'available' ? 'Available' : 'API Key Required' }}
                  </span>
                </div>

                @if (mcp.requires_api_key && mcp.api_key_env_var) {
                  <div class="api-key-info">
                    <mat-icon>info</mat-icon>
                    <span
                      >Set <code>{{ mcp.api_key_env_var }}</code> in .env</span
                    >
                  </div>
                }

                <mat-expansion-panel class="use-cases-panel">
                  <mat-expansion-panel-header>
                    <mat-panel-title>
                      <mat-icon>lightbulb</mat-icon>
                      Use Cases
                    </mat-panel-title>
                  </mat-expansion-panel-header>
                  <ul class="use-cases-list">
                    @for (uc of mcp.use_cases; track uc) {
                      <li>{{ uc }}</li>
                    }
                  </ul>
                </mat-expansion-panel>
              </mat-card-content>
            </mat-card>
          }
        </div>
      }
    </div>
  `,
  styles: `
    /* Grid layout */
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
      gap: 24px;
    }

    /* MCP Cards */
    .mcp-card {
      transition:
        transform 0.2s,
        box-shadow 0.2s;
      cursor: pointer;
    }
    .mcp-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 4px 20px rgba(0, 112, 173, 0.15);
    }

    /* Card avatar icons */
    mat-card-header mat-icon[mat-card-avatar] {
      display: flex !important;
      align-items: center;
      justify-content: center;
      font-size: 24px !important;
      width: 40px;
      height: 40px;
    }
    .icon-available {
      color: var(--cg-vibrant) !important;
      background: rgba(18, 171, 219, 0.12) !important;
    }
    .icon-key {
      color: #f57c00 !important;
      background: rgba(245, 124, 0, 0.12) !important;
    }

    /* Description */
    .mcp-description {
      color: var(--cg-gray-500);
      font-size: 13px;
      line-height: 1.5;
      margin-bottom: 16px;
    }

    /* Chips */
    .mcp-chips {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 16px;
    }
    .chip {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 10px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }
    .chip-icon {
      font-size: 14px !important;
      width: 14px !important;
      height: 14px !important;
    }
    .chip-phases {
      background: rgba(18, 171, 219, 0.08);
      color: var(--cg-vibrant);
    }
    .chip-tools {
      background: var(--cg-gray-100);
      color: var(--cg-gray-500);
    }
    .chip-available {
      background: rgba(76, 175, 80, 0.12);
      color: #388e3c;
    }
    .chip-key {
      background: rgba(245, 124, 0, 0.12);
      color: #f57c00;
    }

    /* API Key Info */
    .api-key-info {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      background: rgba(245, 124, 0, 0.08);
      border-left: 3px solid #f57c00;
      border-radius: 4px;
      font-size: 12px;
      color: var(--cg-gray-600);
      margin-bottom: 16px;
    }
    .api-key-info mat-icon {
      color: #f57c00;
      font-size: 18px;
      width: 18px;
      height: 18px;
    }
    .api-key-info code {
      background: rgba(0, 0, 0, 0.08);
      padding: 2px 6px;
      border-radius: 3px;
      font-family: 'Courier New', monospace;
      font-size: 11px;
      font-weight: 600;
    }

    /* Use Cases Panel */
    .use-cases-panel {
      box-shadow: none;
      background: var(--cg-gray-50);
    }
    .use-cases-panel mat-panel-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      font-weight: 600;
      color: var(--cg-navy);
    }
    .use-cases-panel mat-icon {
      color: var(--cg-vibrant);
      font-size: 18px;
      width: 18px;
      height: 18px;
    }
    .use-cases-list {
      margin: 8px 0;
      padding-left: 20px;
      color: var(--cg-gray-600);
      font-size: 12px;
      line-height: 1.7;
    }
    .use-cases-list li {
      margin-bottom: 4px;
    }
  `,
})
export class McpsComponent implements OnInit, OnDestroy {
  private refreshTimer: ReturnType<typeof setInterval> | null = null;
  mcps: MCPMetadata[] = [];
  summary: MCPSummary = { total: 0, available: 0, requires_api_key: 0, not_installed: 0, by_phase: {} };
  loading = true;

  get phaseCount(): number {
    return Object.keys(this.summary.by_phase).length;
  }

  constructor(
    private http: HttpClient,
    private snack: MatSnackBar,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.loadMcps();
    this.refreshTimer = setInterval(() => this.loadMcps(), 15000);
  }

  ngOnDestroy(): void {
    if (this.refreshTimer) clearInterval(this.refreshTimer);
  }

  private loadMcps(): void {
    this.http
      .get<MCPListResponse>('/api/mcps/')
      .pipe(
        catchError((err) => {
          console.error('Failed to load MCPs:', err);
          return of({
            mcps: [],
            summary: { total: 0, available: 0, requires_api_key: 0, not_installed: 0, by_phase: {} },
          });
        }),
      )
      .subscribe((res) => {
        this.mcps = res.mcps;
        this.summary = res.summary;
        this.loading = false;
        this.cdr.markForCheck();
      });
  }

  getIcon(id: string): string {
    const icons: Record<string, string> = {
      sequential_thinking: 'psychology',
      memory: 'storage',
      brave_search: 'search',
      filesystem: 'folder',
      playwright: 'public',
      github: 'code',
    };
    return icons[id] || 'extension';
  }

  getPhaseNames(phases: number[]): string {
    const phaseMap: Record<number, string> = {
      0: 'Discover',
      1: 'Extract',
      2: 'Analyze',
      3: 'Document',
      4: 'Triage',
      5: 'Plan',
      6: 'Implement',
      7: 'Verify',
      8: 'Deliver',
    };
    return (phases ?? []).map((p) => phaseMap[p] || `Phase ${p}`).join(', ');
  }
}
