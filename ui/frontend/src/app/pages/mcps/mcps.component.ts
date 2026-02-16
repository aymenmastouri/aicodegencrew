import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatBadgeModule } from '@angular/material/badge';
import { HttpClient } from '@angular/common/http';
import { catchError, of } from 'rxjs';

interface MCPMetadata {
  id: string;
  name: string;
  package: string;
  description: string;
  use_cases: string[];
  phases: number[];
  requires_api_key: boolean;
  api_key_env_var: string | null;
  api_key_url: string | null;
  tools: string[];
  status: 'available' | 'requires_api_key' | 'not_installed' | 'running' | 'error';
  command: string;
  args: string[];
}

interface MCPStatusSummary {
  total: number;
  available: number;
  requires_api_key: number;
  not_installed: number;
  running: number;
  error: number;
  by_phase: Record<number, string[]>;
}

interface MCPListResponse {
  mcps: MCPMetadata[];
  summary: MCPStatusSummary;
}

@Component({
  selector: 'app-mcps',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatChipsModule,
    MatButtonModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
    MatExpansionModule,
    MatBadgeModule,
  ],
  template: \`
    <div class="page-container">
      <div class="page-header">
        <h1><mat-icon>extension</mat-icon> MCP Servers</h1>
        <p class="subtitle">Model Context Protocol integrations for CrewAI agents</p>
      </div>

      @if (loading) {
        <div class="loading-container">
          <mat-spinner></mat-spinner>
        </div>
      } @else {
        <div class="mcps-grid">
          @for (mcp of mcps; track mcp.id) {
            <mat-card class="mcp-card">
              <mat-card-header>
                <mat-icon mat-card-avatar>{{ getMCPIcon(mcp.id) }}</mat-icon>
                <mat-card-title>{{ mcp.name }}</mat-card-title>
                <mat-card-subtitle>{{ mcp.package }}</mat-card-subtitle>
              </mat-card-header>
              <mat-card-content>
                <p>{{ mcp.description }}</p>
                <div class="mcp-info">
                  <mat-chip>Phases: {{ mcp.phases.join(', ') }}</mat-chip>
                  <mat-chip>Tools: {{ mcp.tools.length }}</mat-chip>
                  <mat-chip [class.status-ok]="mcp.status === 'available'">
                    {{ getStatusLabel(mcp.status) }}
                  </mat-chip>
                </div>
              </mat-card-content>
            </mat-card>
          }
        </div>
      }
    </div>
  \`,
  styles: [\`
    .page-container { padding: 24px; }
    .page-header h1 { display: flex; align-items: center; gap: 12px; }
    .subtitle { color: rgba(0,0,0,0.6); margin-bottom: 24px; }
    .loading-container { text-align: center; padding: 48px; }
    .mcps-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 24px; }
    .mcp-card { transition: transform 0.2s; }
    .mcp-card:hover { transform: translateY(-4px); }
    .mcp-info { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 16px; }
    .status-ok { background: #4caf50 !important; color: white !important; }
  \`]
})
export class McpsComponent implements OnInit {
  mcps: MCPMetadata[] = [];
  summary: MCPStatusSummary | null = null;
  loading = true;
  error: string | null = null;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.loadMCPs();
  }

  loadMCPs(): void {
    this.loading = true;
    this.http.get<MCPListResponse>('/api/mcps')
      .pipe(catchError(err => of(null)))
      .subscribe(response => {
        this.loading = false;
        if (response) {
          this.mcps = response.mcps;
          this.summary = response.summary;
        }
      });
  }

  getMCPIcon(id: string): string {
    const icons: Record<string, string> = {
      'sequential_thinking': 'psychology',
      'memory': 'storage',
      'brave_search': 'search',
      'filesystem': 'folder',
      'playwright': 'public',
      'github': 'code',
    };
    return icons[id] || 'extension';
  }

  getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      'available': 'Available',
      'requires_api_key': 'Needs API Key',
    };
    return labels[status] || status;
  }
}
