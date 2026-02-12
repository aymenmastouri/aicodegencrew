import { Component, OnInit, OnDestroy, ChangeDetectorRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator } from '@angular/material/paginator';
import { MatTableDataSource } from '@angular/material/table';
import { RouterLink } from '@angular/router';

import { PipelineService, RunHistoryEntry, RunDetail } from '../../services/pipeline.service';

@Component({
  selector: 'app-history',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatTableModule,
    MatPaginatorModule,
    RouterLink,
  ],
  template: `
    <div class="page-container">
      <div class="page-header">
        <mat-icon class="page-icon">history</mat-icon>
        <div>
          <h1 class="page-title">Run History</h1>
          <p class="page-subtitle">Pipeline execution and reset history with detailed outcomes</p>
        </div>
        <span class="flex-1"></span>
        <button mat-stroked-button color="primary" routerLink="/run">
          <mat-icon>rocket_launch</mat-icon> Run Pipeline
        </button>
      </div>

      <!-- Filter Bar -->
      <div class="filter-bar">
        @for (f of filters; track f.value) {
          <button class="filter-chip" [class.filter-active]="activeFilter === f.value" (click)="setFilter(f.value)">
            <mat-icon class="filter-icon">{{ f.icon }}</mat-icon>
            {{ f.label }}
            @if (f.count !== null) {
              <span class="filter-count">{{ f.count }}</span>
            }
          </button>
        }
        <span class="flex-1"></span>
        <input class="search-input" placeholder="Search by run ID..." [value]="searchTerm" (input)="onSearch($event)" />
      </div>

      <!-- Loading -->
      @if (loading) {
        <div class="loading-center">
          <mat-spinner diameter="36"></mat-spinner>
        </div>
      } @else if (dataSource.data.length === 0) {
        <div class="empty-state">
          <mat-icon class="empty-icon">history</mat-icon>
          <p>No history entries yet. Run a pipeline to see results here.</p>
          <button mat-flat-button color="primary" routerLink="/run">
            <mat-icon>rocket_launch</mat-icon> Run Pipeline
          </button>
        </div>
      } @else {
        <!-- Master Table -->
        <div class="table-card">
          <table mat-table [dataSource]="dataSource" class="history-table">
            <!-- Trigger Column -->
            <ng-container matColumnDef="trigger">
              <th mat-header-cell *matHeaderCellDef>Type</th>
              <td mat-cell *matCellDef="let row">
                @if (row.trigger === 'reset') {
                  <span class="trigger-chip trigger-reset">
                    <mat-icon class="chip-icon">restart_alt</mat-icon> Reset
                  </span>
                } @else {
                  <span class="trigger-chip trigger-run">
                    <mat-icon class="chip-icon">play_arrow</mat-icon> Run
                  </span>
                }
              </td>
            </ng-container>

            <!-- Run ID Column -->
            <ng-container matColumnDef="run_id">
              <th mat-header-cell *matHeaderCellDef>Run ID</th>
              <td mat-cell *matCellDef="let row">
                <span class="mono-text">{{ row.run_id }}</span>
              </td>
            </ng-container>

            <!-- Preset Column -->
            <ng-container matColumnDef="preset">
              <th mat-header-cell *matHeaderCellDef>Preset</th>
              <td mat-cell *matCellDef="let row">
                {{ row.preset || '—' }}
              </td>
            </ng-container>

            <!-- Phases Column -->
            <ng-container matColumnDef="phases">
              <th mat-header-cell *matHeaderCellDef>Phases</th>
              <td mat-cell *matCellDef="let row">
                <span class="phase-count">{{ row.phases.length }} phase{{ row.phases.length !== 1 ? 's' : '' }}</span>
              </td>
            </ng-container>

            <!-- Status Column -->
            <ng-container matColumnDef="status">
              <th mat-header-cell *matHeaderCellDef>Status</th>
              <td mat-cell *matCellDef="let row">
                <span class="status-chip" [class]="'status-' + row.status">{{ row.status }}</span>
              </td>
            </ng-container>

            <!-- Started Column -->
            <ng-container matColumnDef="started_at">
              <th mat-header-cell *matHeaderCellDef>Started</th>
              <td mat-cell *matCellDef="let row">
                {{ row.started_at | date: 'medium' }}
              </td>
            </ng-container>

            <!-- Duration Column -->
            <ng-container matColumnDef="duration">
              <th mat-header-cell *matHeaderCellDef>Duration</th>
              <td mat-cell *matCellDef="let row">
                {{ row.duration || '—' }}
              </td>
            </ng-container>

            <!-- Actions Column -->
            <ng-container matColumnDef="actions">
              <th mat-header-cell *matHeaderCellDef></th>
              <td mat-cell *matCellDef="let row">
                <button mat-icon-button matTooltip="View details" (click)="toggleDetail(row); $event.stopPropagation()">
                  <mat-icon>{{ selectedRun?.run_id === row.run_id ? 'expand_less' : 'expand_more' }}</mat-icon>
                </button>
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns"
              class="table-row" [class.row-selected]="selectedRun?.run_id === row.run_id"
              (click)="toggleDetail(row)"></tr>
          </table>
          <mat-paginator [pageSize]="20" [pageSizeOptions]="[10, 20, 50]" showFirstLastButtons></mat-paginator>
        </div>

        <!-- Detail Panel -->
        @if (selectedRun) {
          <div class="detail-panel">
            @if (detailLoading) {
              <div class="loading-center">
                <mat-spinner diameter="32"></mat-spinner>
              </div>
            } @else if (detail) {
              <!-- Header Card -->
              <div class="detail-header">
                <div class="detail-header-main">
                  <div>
                    <div class="detail-run-id">{{ detail.run_id }}</div>
                    <div class="detail-meta">
                      @if (detail.preset) {
                        <span class="detail-preset">{{ detail.preset }}</span>
                      }
                      <span class="detail-time">{{ detail.started_at | date: 'medium' }}</span>
                      @if (detail.completed_at) {
                        <span class="detail-time">→ {{ detail.completed_at | date: 'medium' }}</span>
                      }
                    </div>
                  </div>
                  <div class="detail-header-right">
                    <span class="status-chip status-lg" [class]="'status-' + detail.status">{{ detail.status }}</span>
                    @if (detail.duration) {
                      <span class="detail-duration">{{ detail.duration }}</span>
                    }
                  </div>
                </div>
              </div>

              <!-- Phase Timeline -->
              @if (detail.phase_results.length > 0) {
                <div class="detail-section">
                  <h3 class="detail-section-title">
                    <mat-icon>account_tree</mat-icon> Phase Results
                  </h3>
                  <div class="phase-timeline">
                    @for (phase of detail.phase_results; track $index) {
                      <div class="timeline-item" [class]="'tl-' + (phase['status'] || 'unknown')">
                        <div class="tl-dot">
                          <mat-icon class="tl-icon">
                            {{ phase['status'] === 'completed' ? 'check_circle' :
                               phase['status'] === 'failed' ? 'error' :
                               phase['status'] === 'skipped' ? 'skip_next' : 'radio_button_unchecked' }}
                          </mat-icon>
                        </div>
                        <div class="tl-content">
                          <div class="tl-header">
                            <span class="tl-name">{{ phase['phase_id'] || phase['name'] || 'Phase ' + $index }}</span>
                            <span class="status-chip status-sm" [class]="'status-' + (phase['status'] || 'unknown')">
                              {{ phase['status'] || 'unknown' }}
                            </span>
                            @if (phase['duration'] || phase['duration_seconds']) {
                              <span class="tl-duration">{{ phase['duration'] || (phase['duration_seconds'] + 's') }}</span>
                            }
                          </div>
                          @if (phase['output_files'] && phase['output_files'].length > 0) {
                            <div class="tl-files">
                              @for (file of phase['output_files']; track file) {
                                <span class="file-chip">
                                  <mat-icon class="chip-icon">description</mat-icon>
                                  {{ getFileName(file) }}
                                </span>
                              }
                            </div>
                          }
                          @if (phase['error']) {
                            <div class="tl-error">{{ phase['error'] }}</div>
                          }
                        </div>
                      </div>
                    }
                  </div>
                </div>
              }

              <!-- Metrics Summary -->
              @if (detail.metrics_events.length > 0) {
                <div class="detail-section">
                  <h3 class="detail-section-title">
                    <mat-icon>monitoring</mat-icon> Metrics Events
                  </h3>
                  <div class="metrics-grid">
                    <div class="metric-card">
                      <div class="metric-value">{{ detail.metrics_events.length }}</div>
                      <div class="metric-label">Total Events</div>
                    </div>
                    <div class="metric-card">
                      <div class="metric-value">{{ countEventType('phase_complete') }}</div>
                      <div class="metric-label">Phases Completed</div>
                    </div>
                    <div class="metric-card">
                      <div class="metric-value">{{ countEventType('mini_crew_complete') }}</div>
                      <div class="metric-label">Crew Executions</div>
                    </div>
                    <div class="metric-card">
                      <div class="metric-value">{{ countEventType('phase_failed') }}</div>
                      <div class="metric-label">Failures</div>
                    </div>
                  </div>
                </div>
              }

              <!-- Environment -->
              @if (detail.environment && objectKeys(detail.environment).length > 0) {
                <div class="detail-section">
                  <h3 class="detail-section-title">
                    <mat-icon>settings</mat-icon> Environment
                  </h3>
                  <div class="env-grid">
                    @for (key of objectKeys(detail.environment); track key) {
                      <div class="env-item">
                        <span class="env-key">{{ key }}</span>
                        <span class="env-value">{{ detail.environment[key] }}</span>
                      </div>
                    }
                  </div>
                </div>
              }
            }
          </div>
        }
      }
    </div>
  `,
  styles: [
    `
      /* Filter Bar */
      .filter-bar {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 16px;
        flex-wrap: wrap;
      }
      .filter-chip {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 6px 14px;
        border-radius: 20px;
        border: 1px solid var(--cg-gray-200);
        background: #fff;
        font-size: 13px;
        cursor: pointer;
        transition: all 0.15s;
        color: var(--cg-gray-500);
      }
      .filter-chip:hover {
        border-color: var(--cg-blue);
        color: var(--cg-blue);
      }
      .filter-active {
        background: rgba(0, 112, 173, 0.08);
        border-color: var(--cg-blue);
        color: var(--cg-blue);
        font-weight: 500;
      }
      .filter-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
      }
      .filter-count {
        background: var(--cg-gray-100);
        padding: 1px 6px;
        border-radius: 10px;
        font-size: 11px;
        font-weight: 600;
      }
      .filter-active .filter-count {
        background: rgba(0, 112, 173, 0.15);
      }
      .search-input {
        padding: 6px 14px;
        border: 1px solid var(--cg-gray-200);
        border-radius: 20px;
        font-size: 13px;
        outline: none;
        width: 220px;
        transition: border-color 0.15s;
      }
      .search-input:focus {
        border-color: var(--cg-blue);
      }

      /* Table */
      .table-card {
        background: #fff;
        border-radius: 12px;
        overflow: hidden;
      }
      .history-table {
        width: 100%;
      }
      .table-row {
        cursor: pointer;
        transition: background 0.1s;
      }
      .table-row:hover {
        background: var(--cg-gray-50);
      }
      .row-selected {
        background: rgba(0, 112, 173, 0.04) !important;
      }
      .mono-text {
        font-family: monospace;
        font-size: 12px;
        color: var(--cg-gray-500);
      }
      .phase-count {
        font-size: 13px;
        color: var(--cg-gray-500);
      }

      /* Chip icon size */
      .chip-icon {
        font-size: 14px;
        width: 14px;
        height: 14px;
      }

      /* Detail Panel */
      .detail-panel {
        margin-top: 16px;
        background: #fff;
        border-radius: 12px;
        padding: 24px;
        border: 1px solid var(--cg-gray-100);
      }
      .detail-header {
        margin-bottom: 24px;
        padding-bottom: 16px;
        border-bottom: 1px solid var(--cg-gray-100);
      }
      .detail-header-main {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
      }
      .detail-run-id {
        font-family: monospace;
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 4px;
      }
      .detail-meta {
        display: flex;
        gap: 12px;
        font-size: 13px;
        color: var(--cg-gray-500);
      }
      .detail-preset {
        font-weight: 500;
        color: var(--cg-blue);
      }
      .detail-header-right {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      .detail-duration {
        font-family: monospace;
        font-size: 14px;
        color: var(--cg-gray-500);
      }

      /* Detail Sections */
      .detail-section {
        margin-bottom: 24px;
      }
      .detail-section:last-child {
        margin-bottom: 0;
      }
      .detail-section-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 15px;
        font-weight: 500;
        margin: 0 0 12px;
        color: var(--cg-gray-900);
      }
      .detail-section-title .mat-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
        color: var(--cg-blue);
      }

      /* Phase Timeline */
      .phase-timeline {
        position: relative;
        padding-left: 24px;
      }
      .phase-timeline::before {
        content: '';
        position: absolute;
        left: 11px;
        top: 0;
        bottom: 0;
        width: 2px;
        background: var(--cg-gray-200);
      }
      .timeline-item {
        display: flex;
        gap: 12px;
        padding: 8px 0;
        position: relative;
      }
      .tl-dot {
        position: absolute;
        left: -24px;
        top: 10px;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #fff;
        z-index: 1;
      }
      .tl-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
      }
      .tl-completed .tl-icon {
        color: var(--cg-success, #28a745);
      }
      .tl-failed .tl-icon {
        color: var(--cg-error, #dc3545);
      }
      .tl-skipped .tl-icon {
        color: var(--cg-gray-300);
      }
      .tl-content {
        flex: 1;
        padding: 4px 0;
      }
      .tl-header {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
      }
      .tl-name {
        font-weight: 500;
        font-size: 14px;
      }
      .tl-duration {
        font-family: monospace;
        font-size: 12px;
        color: var(--cg-gray-500);
      }
      .tl-files {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 6px;
      }
      .file-chip {
        display: inline-flex;
        align-items: center;
        gap: 3px;
        padding: 2px 8px;
        border-radius: 6px;
        background: var(--cg-gray-50);
        font-size: 11px;
        font-family: monospace;
        color: var(--cg-gray-500);
      }
      .tl-error {
        margin-top: 6px;
        padding: 8px 12px;
        border-radius: 8px;
        background: rgba(220, 53, 69, 0.06);
        color: var(--cg-error, #dc3545);
        font-size: 13px;
        font-family: monospace;
        white-space: pre-wrap;
      }

      /* Metrics Grid */
      .metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
        gap: 12px;
      }
      .metric-card {
        padding: 16px;
        border-radius: 10px;
        background: var(--cg-gray-50);
        text-align: center;
      }
      .metric-value {
        font-size: 24px;
        font-weight: 600;
        color: var(--cg-navy);
      }
      .metric-label {
        font-size: 12px;
        color: var(--cg-gray-500);
        margin-top: 4px;
      }

      /* Environment Grid */
      .env-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 8px;
      }
      .env-item {
        display: flex;
        gap: 8px;
        padding: 6px 12px;
        border-radius: 8px;
        background: var(--cg-gray-50);
        font-size: 13px;
        overflow: hidden;
      }
      .env-key {
        font-weight: 500;
        color: var(--cg-gray-500);
        white-space: nowrap;
      }
      .env-value {
        font-family: monospace;
        font-size: 12px;
        color: var(--cg-gray-900);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    `,
  ],
})
export class HistoryComponent implements OnInit, OnDestroy {
  loading = true;
  allEntries: RunHistoryEntry[] = [];
  dataSource = new MatTableDataSource<RunHistoryEntry>([]);
  displayedColumns = ['trigger', 'run_id', 'preset', 'phases', 'status', 'started_at', 'duration', 'actions'];

  activeFilter = 'all';
  searchTerm = '';
  filters = [
    { value: 'all', label: 'All', icon: 'list', count: null as number | null },
    { value: 'run', label: 'Runs', icon: 'play_arrow', count: null as number | null },
    { value: 'reset', label: 'Resets', icon: 'restart_alt', count: null as number | null },
    { value: 'failed', label: 'Failed', icon: 'error', count: null as number | null },
  ];

  selectedRun: RunHistoryEntry | null = null;
  detail: RunDetail | null = null;
  detailLoading = false;

  private refreshTimer: ReturnType<typeof setInterval> | null = null;

  @ViewChild(MatPaginator) paginator!: MatPaginator;

  constructor(
    private pipelineSvc: PipelineService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.loadHistory();
    this.refreshTimer = setInterval(() => this.loadHistory(), 30000);
  }

  ngOnDestroy(): void {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
    }
  }

  loadHistory(): void {
    this.pipelineSvc.getHistory().subscribe({
      next: (entries) => {
        this.allEntries = entries;
        this.updateCounts();
        this.applyFilters();
        this.loading = false;
        this.cdr.markForCheck();
        // Attach paginator after data is set
        setTimeout(() => {
          if (this.paginator) {
            this.dataSource.paginator = this.paginator;
          }
        });
      },
      error: () => {
        this.loading = false;
        this.cdr.markForCheck();
      },
    });
  }

  setFilter(value: string): void {
    this.activeFilter = value;
    this.applyFilters();
  }

  onSearch(event: Event): void {
    this.searchTerm = (event.target as HTMLInputElement).value;
    this.applyFilters();
  }

  applyFilters(): void {
    let filtered = [...this.allEntries];

    if (this.activeFilter === 'run') {
      filtered = filtered.filter((e) => e.trigger !== 'reset');
    } else if (this.activeFilter === 'reset') {
      filtered = filtered.filter((e) => e.trigger === 'reset');
    } else if (this.activeFilter === 'failed') {
      filtered = filtered.filter((e) => e.status === 'failed');
    }

    if (this.searchTerm) {
      const term = this.searchTerm.toLowerCase();
      filtered = filtered.filter((e) => e.run_id.toLowerCase().includes(term));
    }

    this.dataSource.data = filtered;
  }

  updateCounts(): void {
    this.filters[0].count = this.allEntries.length;
    this.filters[1].count = this.allEntries.filter((e) => e.trigger !== 'reset').length;
    this.filters[2].count = this.allEntries.filter((e) => e.trigger === 'reset').length;
    this.filters[3].count = this.allEntries.filter((e) => e.status === 'failed').length;
  }

  toggleDetail(row: RunHistoryEntry): void {
    if (this.selectedRun?.run_id === row.run_id) {
      this.selectedRun = null;
      this.detail = null;
      return;
    }
    this.selectedRun = row;
    this.detail = null;
    this.detailLoading = true;
    this.cdr.markForCheck();

    this.pipelineSvc.getRunDetail(row.run_id).subscribe({
      next: (d) => {
        this.detail = d;
        this.detailLoading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        // Fallback: build detail from the list entry
        this.detail = {
          run_id: row.run_id,
          status: row.status,
          preset: row.preset,
          phases: row.phases,
          started_at: row.started_at,
          completed_at: row.completed_at,
          duration: row.duration,
          duration_seconds: row.duration_seconds,
          trigger: row.trigger || 'pipeline',
          phase_results: row.phase_results || [],
          metrics_events: [],
          environment: {},
        };
        this.detailLoading = false;
        this.cdr.markForCheck();
      },
    });
  }

  countEventType(type: string): number {
    if (!this.detail) return 0;
    return this.detail.metrics_events.filter((e) => e['event'] === type).length;
  }

  getFileName(path: string): string {
    return path.split('/').pop() || path.split('\\').pop() || path;
  }

  objectKeys(obj: Record<string, any>): string[] {
    return Object.keys(obj);
  }
}
