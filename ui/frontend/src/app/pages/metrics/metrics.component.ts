import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatSelectModule } from '@angular/material/select';
import { FormsModule } from '@angular/forms';

import { ApiService, MetricEvent, MetricsSummary } from '../../services/api.service';

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
    FormsModule,
  ],
  template: `
    <div class="page-container">
      <h1 class="page-title">Metrics</h1>

      @if (summary) {
        <div class="filter-bar">
          <mat-card>
            <mat-card-content class="filter-content">
              <span><strong>{{ summary.total_events }}</strong> events</span>
              <span><strong>{{ summary.run_ids.length }}</strong> runs</span>
              <mat-form-field>
                <mat-label>Filter by event</mat-label>
                <mat-select [(ngModel)]="selectedEvent" (selectionChange)="loadMetrics()">
                  <mat-option [value]="null">All events</mat-option>
                  @for (evt of eventTypes; track evt) {
                    <mat-option [value]="evt">{{ evt }}</mat-option>
                  }
                </mat-select>
              </mat-form-field>
            </mat-card-content>
          </mat-card>
        </div>

        <mat-card>
          <mat-card-content>
            <table mat-table [dataSource]="summary.events" class="metrics-table">
              <ng-container matColumnDef="timestamp">
                <th mat-header-cell *matHeaderCellDef>Time</th>
                <td mat-cell *matCellDef="let e" class="mono">
                  {{ e.timestamp | slice:11:19 }}
                </td>
              </ng-container>
              <ng-container matColumnDef="event">
                <th mat-header-cell *matHeaderCellDef>Event</th>
                <td mat-cell *matCellDef="let e">
                  <mat-chip>{{ e.event }}</mat-chip>
                </td>
              </ng-container>
              <ng-container matColumnDef="data">
                <th mat-header-cell *matHeaderCellDef>Data</th>
                <td mat-cell *matCellDef="let e" class="mono data-cell">
                  {{ formatData(e.data) }}
                </td>
              </ng-container>
              <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
              <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
            </table>
          </mat-card-content>
        </mat-card>
      }
    </div>
  `,
  styles: [`
    .filter-bar { margin-bottom: 16px; }
    .filter-content {
      display: flex;
      align-items: center;
      gap: 24px;
    }
    .metrics-table { width: 100%; }
    .data-cell {
      max-width: 500px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  `],
})
export class MetricsComponent implements OnInit {
  summary: MetricsSummary | null = null;
  selectedEvent: string | null = null;
  eventTypes: string[] = [];
  displayedColumns = ['timestamp', 'event', 'data'];

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.loadMetrics();
  }

  loadMetrics(): void {
    this.api.getMetrics(500, this.selectedEvent || undefined).subscribe(s => {
      this.summary = s;
      if (!this.eventTypes.length) {
        this.eventTypes = [...new Set(s.events.map(e => e.event))].sort();
      }
    });
  }

  formatData(data: Record<string, unknown>): string {
    const entries = Object.entries(data)
      .filter(([k]) => k !== 'run_id')
      .map(([k, v]) => `${k}=${v}`);
    return entries.join(', ');
  }
}
