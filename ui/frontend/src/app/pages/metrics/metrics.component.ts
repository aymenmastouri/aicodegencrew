import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { FormsModule } from '@angular/forms';

import { ApiService, MetricsSummary } from '../../services/api.service';

@Component({
  selector: 'app-metrics',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatTableModule,
    MatChipsModule,
    MatSelectModule,
    MatProgressSpinnerModule,
    FormsModule,
  ],
  template: `
    <div class="page-container">
      <div class="page-header">
        <mat-icon class="page-icon">monitoring</mat-icon>
        <div>
          <h1 class="page-title">Metrics</h1>
          <p class="page-subtitle">Pipeline execution events and performance data</p>
        </div>
      </div>

      @if (loading) {
        <div class="loading-center">
          <mat-spinner diameter="36"></mat-spinner>
        </div>
      } @else if (summary) {
        <!-- Stats Bar -->
        <div class="stats-bar">
          <div class="stat-item">
            <mat-icon>event</mat-icon>
            <strong>{{ summary.total_events }}</strong> events
          </div>
          <div class="stat-item">
            <mat-icon>fingerprint</mat-icon>
            <strong>{{ summary.run_ids.length }}</strong> runs
          </div>
          <div class="stat-item filter-item">
            <mat-form-field appearance="outline" class="filter-field">
              <mat-label>Filter by event</mat-label>
              <mat-select [(ngModel)]="selectedEvent" (selectionChange)="loadMetrics()">
                <mat-option [value]="null">All events</mat-option>
                @for (evt of eventTypes; track evt) {
                  <mat-option [value]="evt">{{ evt }}</mat-option>
                }
              </mat-select>
            </mat-form-field>
          </div>
        </div>

        <mat-card>
          <mat-card-content>
            @if (summary.events.length === 0) {
              <div class="empty-inline">
                <mat-icon>filter_list</mat-icon>
                <span>No events match this filter.</span>
              </div>
            } @else {
              <table mat-table [dataSource]="summary.events" class="metrics-table">
                <ng-container matColumnDef="timestamp">
                  <th mat-header-cell *matHeaderCellDef>Time</th>
                  <td mat-cell *matCellDef="let e" class="mono">
                    {{ e.timestamp | slice: 11 : 19 }}
                  </td>
                </ng-container>
                <ng-container matColumnDef="event">
                  <th mat-header-cell *matHeaderCellDef>Event</th>
                  <td mat-cell *matCellDef="let e">
                    <span class="event-badge" [class]="eventClass(e.event)">{{ e.event }}</span>
                  </td>
                </ng-container>
                <ng-container matColumnDef="data">
                  <th mat-header-cell *matHeaderCellDef>Data</th>
                  <td mat-cell *matCellDef="let e" class="mono data-cell">
                    {{ formatData(e.data) }}
                  </td>
                </ng-container>
                <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
                <tr mat-row *matRowDef="let row; columns: displayedColumns"></tr>
              </table>
            }
          </mat-card-content>
        </mat-card>
      } @else {
        <div class="empty-state">
          <mat-icon>monitoring</mat-icon>
          <p>No metrics data available. Run the pipeline to generate metrics.</p>
        </div>
      }
    </div>
  `,
  styles: [
    `
      .filter-item {
        padding: 4px 16px;
      }
      .filter-field {
        margin: 0;
      }
      .filter-field ::ng-deep .mat-mdc-form-field-subscript-wrapper {
        display: none;
      }
      .metrics-table {
        width: 100%;
      }
      .metrics-table tr.mat-mdc-row:hover {
        background: rgba(0, 112, 173, 0.03);
      }
      .event-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 10px;
        font-size: 11px;
        font-weight: 600;
        font-family: monospace;
        background: var(--cg-gray-100);
        color: var(--cg-gray-900);
      }
      .event-start {
        background: rgba(0, 112, 173, 0.1);
        color: var(--cg-blue);
      }
      .event-complete {
        background: rgba(40, 167, 69, 0.1);
        color: var(--cg-success);
      }
      .event-failed {
        background: rgba(220, 53, 69, 0.1);
        color: var(--cg-error);
      }
      .data-cell {
        max-width: 500px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 12px;
      }
    `,
  ],
})
export class MetricsComponent implements OnInit, OnDestroy {
  private refreshTimer: ReturnType<typeof setInterval> | null = null;
  summary: MetricsSummary | null = null;
  selectedEvent: string | null = null;
  eventTypes: string[] = [];
  displayedColumns = ['timestamp', 'event', 'data'];
  loading = true;

  constructor(
    private api: ApiService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.loadMetrics();
    // Background refresh: never show spinner — data updates silently
    this.refreshTimer = setInterval(() => this._fetchMetrics(), 10000);
  }

  ngOnDestroy(): void {
    if (this.refreshTimer) clearInterval(this.refreshTimer);
  }

  /** Public: called by template (filter change) — shows spinner. */
  loadMetrics(): void {
    this.loading = true;
    this.cdr.markForCheck();
    this._fetchMetrics();
  }

  /** Private: fetches data without touching loading state (background refresh). */
  private _fetchMetrics(): void {
    this.api.getMetrics(500, this.selectedEvent || undefined).subscribe({
      next: (s) => {
        this.summary = s;
        if (!this.eventTypes.length) {
          this.eventTypes = [...new Set(s.events.map((e) => e.event))].sort();
        }
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.cdr.markForCheck();
      },
    });
  }

  eventClass(event: string): string {
    if (event.includes('start')) return 'event-start';
    if (event.includes('complete')) return 'event-complete';
    if (event.includes('failed') || event.includes('error')) return 'event-failed';
    return '';
  }

  formatData(data: Record<string, unknown>): string {
    const entries = Object.entries(data)
      .filter(([k]) => k !== 'run_id')
      .map(([k, v]) => {
        if (v === null || v === undefined) return `${k}=—`;
        if (typeof v === 'object') return `${k}=${JSON.stringify(v)}`;
        return `${k}=${v}`;
      });
    return entries.join(', ');
  }
}
