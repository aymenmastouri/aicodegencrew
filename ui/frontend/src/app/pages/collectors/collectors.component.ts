import { Component, OnInit, ChangeDetectorRef, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatExpansionModule } from '@angular/material/expansion';

import { ApiService, CollectorInfo, CollectorListResponse } from '../../services/api.service';
import { formatBytes as formatBytesUtil } from '../../shared/phase-utils';

@Component({
  selector: 'app-collectors',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    MatCardModule,
    MatTableModule,
    MatIconModule,
    MatButtonModule,
    MatChipsModule,
    MatSlideToggleModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatSnackBarModule,
    MatExpansionModule,
  ],
  template: `
    <div class="page-container">
      <div class="page-header">
        <mat-icon class="page-icon">hub</mat-icon>
        <div>
          <h1 class="page-title">Collectors</h1>
          <p class="page-subtitle">View and manage architecture fact collectors</p>
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
            <mat-icon>layers</mat-icon>
            <span class="stat-value">{{ data?.total ?? 0 }}</span>
            <span class="stat-label">Total Collectors</span>
          </div>
          <div class="stat-item">
            <mat-icon>check_circle</mat-icon>
            <span class="stat-value">{{ data?.enabled_count ?? 0 }}</span>
            <span class="stat-label">Enabled</span>
          </div>
          <div class="stat-item">
            <mat-icon>category</mat-icon>
            <span class="stat-value">{{ dimensionCount }}</span>
            <span class="stat-label">Dimensions</span>
          </div>
          <div class="stat-item">
            <mat-icon>data_object</mat-icon>
            <span class="stat-value">{{ totalFacts }}</span>
            <span class="stat-label">Total Facts</span>
          </div>
        </div>

        <!-- Collectors Table -->
        <mat-card class="table-card">
          <table mat-table [dataSource]="collectors" class="collectors-table">
            <!-- Step Column -->
            <ng-container matColumnDef="step">
              <th mat-header-cell *matHeaderCellDef>Step</th>
              <td mat-cell *matCellDef="let c">
                <span class="step-badge" [class.step-core]="c.category === 'core'">
                  {{ c.step }}
                </span>
              </td>
            </ng-container>

            <!-- Name Column -->
            <ng-container matColumnDef="name">
              <th mat-header-cell *matHeaderCellDef>Collector</th>
              <td mat-cell *matCellDef="let c">
                <div class="collector-name">{{ c.name }}</div>
                <div class="collector-desc">{{ c.description }}</div>
              </td>
            </ng-container>

            <!-- Dimension Column -->
            <ng-container matColumnDef="dimension">
              <th mat-header-cell *matHeaderCellDef>Dimension</th>
              <td mat-cell *matCellDef="let c">
                <span class="chip dimension-chip">{{ c.dimension }}</span>
              </td>
            </ng-container>

            <!-- Category Column -->
            <ng-container matColumnDef="category">
              <th mat-header-cell *matHeaderCellDef>Category</th>
              <td mat-cell *matCellDef="let c">
                <span class="chip" [class.chip-core]="c.category === 'core'" [class.chip-optional]="c.category === 'optional'">
                  @if (c.category === 'core') {
                    <mat-icon class="chip-icon">lock</mat-icon>
                  }
                  {{ c.category }}
                </span>
              </td>
            </ng-container>

            <!-- Fact Count Column -->
            <ng-container matColumnDef="fact_count">
              <th mat-header-cell *matHeaderCellDef>Facts</th>
              <td mat-cell *matCellDef="let c">
                <span class="fact-count" [class.no-data]="c.fact_count === null">
                  {{ c.fact_count !== null ? c.fact_count : '\u2014' }}
                </span>
              </td>
            </ng-container>

            <!-- Status Column -->
            <ng-container matColumnDef="status">
              <th mat-header-cell *matHeaderCellDef>Status</th>
              <td mat-cell *matCellDef="let c">
                @if (!c.can_disable) {
                  <span class="chip chip-core">
                    <mat-icon class="chip-icon">lock</mat-icon>
                    always on
                  </span>
                } @else {
                  <mat-slide-toggle
                    [checked]="c.enabled"
                    (change)="onToggle(c, $event.checked)"
                    [disabled]="toggling === c.id"
                    color="primary"
                  ></mat-slide-toggle>
                }
              </td>
            </ng-container>

            <!-- Actions Column -->
            <ng-container matColumnDef="actions">
              <th mat-header-cell *matHeaderCellDef></th>
              <td mat-cell *matCellDef="let c">
                @if (c.fact_count !== null) {
                  <button mat-icon-button matTooltip="View output" (click)="toggleOutput(c); $event.stopPropagation()">
                    <mat-icon>{{ expandedId === c.id ? 'expand_less' : 'visibility' }}</mat-icon>
                  </button>
                }
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr
              mat-row
              *matRowDef="let row; columns: displayedColumns"
              class="collector-row"
              [class.expanded-row]="expandedId === row.id"
              (click)="onRowClick(row)"
            ></tr>
          </table>
        </mat-card>

        <!-- Output Preview Panel -->
        @if (expandedId && outputData) {
          <mat-card class="output-card" id="collector-output">
            <mat-card-header>
              <mat-icon mat-card-avatar>data_object</mat-icon>
              <mat-card-title>{{ expandedId }} output</mat-card-title>
              <mat-card-subtitle>
                {{ outputFactCount }} facts &middot; {{ formatBytes(outputFileSize) }}
              </mat-card-subtitle>
            </mat-card-header>
            <mat-card-content>
              <pre class="output-json">{{ outputPreview }}</pre>
            </mat-card-content>
            <mat-card-actions align="end">
              <button mat-button (click)="closeOutput()">
                Close
              </button>
            </mat-card-actions>
          </mat-card>
        }

        @if (expandedId && outputLoading) {
          <div class="loading-center" style="padding: 24px 0">
            <mat-spinner diameter="32"></mat-spinner>
          </div>
        }
      }
    </div>
  `,
  styles: [
    `
      /* Table */
      .table-card {
        overflow: hidden;
      }
      .collectors-table {
        width: 100%;
      }
      .collector-row {
        cursor: pointer;
      }
      .collector-row:hover {
        background: rgba(0, 112, 173, 0.03);
      }
      .expanded-row {
        background: rgba(18, 171, 219, 0.06) !important;
      }

      /* Step badge */
      .step-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background: var(--cg-gray-200);
        font-size: 12px;
        font-weight: 700;
        color: var(--cg-gray-500);
      }
      .step-core {
        background: var(--cg-vibrant);
        color: white;
      }

      /* Collector info */
      .collector-name {
        font-weight: 600;
        font-size: 13px;
        color: var(--cg-navy);
      }
      .collector-desc {
        font-size: 11px;
        color: var(--cg-gray-400);
        margin-top: 2px;
      }

      /* Chips */
      .chip {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.3px;
      }
      .chip-icon {
        font-size: 13px !important;
        width: 13px !important;
        height: 13px !important;
      }
      .chip-core {
        background: rgba(18, 171, 219, 0.12);
        color: var(--cg-vibrant);
      }
      .chip-optional {
        background: var(--cg-gray-100);
        color: var(--cg-gray-400);
      }
      .dimension-chip {
        background: rgba(18, 171, 219, 0.08);
        color: var(--cg-vibrant);
      }

      /* Fact count */
      .fact-count {
        font-weight: 600;
        font-size: 14px;
        color: var(--cg-navy);
      }
      .no-data {
        color: var(--cg-gray-300);
      }

      /* Output preview */
      .output-card {
        margin-top: 16px;
      }
      .output-json {
        max-height: 500px;
        overflow: auto;
        background: var(--cg-dark);
        color: #eeffff;
        padding: 16px;
        border-radius: 8px;
        font-size: 12px;
        line-height: 1.5;
        white-space: pre-wrap;
        word-break: break-word;
      }
    `,
  ],
})
export class CollectorsComponent implements OnInit {
  loading = true;
  data: CollectorListResponse | null = null;
  collectors: CollectorInfo[] = [];
  displayedColumns = ['step', 'name', 'dimension', 'category', 'fact_count', 'status', 'actions'];

  toggling: string | null = null;
  expandedId: string | null = null;
  outputData: unknown = null;
  outputLoading = false;
  outputFactCount = 0;
  outputFileSize = 0;

  get dimensionCount(): number {
    if (!this.collectors.length) return 0;
    return new Set(this.collectors.map((c) => c.dimension)).size;
  }

  get totalFacts(): number {
    return this.collectors.reduce((sum, c) => sum + (c.fact_count ?? 0), 0);
  }

  get outputPreview(): string {
    if (!this.outputData) return '';
    const json = JSON.stringify(this.outputData, null, 2);
    // Truncate to ~200 lines for performance
    const lines = json.split('\n');
    if (lines.length > 200) {
      return lines.slice(0, 200).join('\n') + '\n\n... (' + (lines.length - 200) + ' more lines)';
    }
    return json;
  }

  constructor(
    private api: ApiService,
    private snack: MatSnackBar,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.api.getCollectors().subscribe({
      next: (res) => {
        this.data = res;
        this.collectors = res.collectors;
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.snack.open('Failed to load collectors', 'Dismiss', { duration: 4000 });
        this.cdr.markForCheck();
      },
    });
  }

  onToggle(collector: CollectorInfo, enabled: boolean): void {
    this.toggling = collector.id;
    this.api.toggleCollector(collector.id, enabled).subscribe({
      next: (updated) => {
        // Update in-place
        const idx = this.collectors.findIndex((c) => c.id === collector.id);
        if (idx >= 0) this.collectors[idx] = updated;
        // Update stats
        if (this.data) {
          this.data.enabled_count = this.collectors.filter((c) => c.enabled).length;
        }
        this.toggling = null;
        this.snack.open(
          `${collector.name} ${enabled ? 'enabled' : 'disabled'}`,
          'OK',
          { duration: 2500 },
        );
        this.cdr.markForCheck();
      },
      error: () => {
        this.toggling = null;
        this.snack.open(`Failed to toggle ${collector.name}`, 'Dismiss', { duration: 4000 });
        this.cdr.markForCheck();
      },
    });
  }

  onRowClick(collector: CollectorInfo): void {
    if (collector.fact_count !== null) {
      this.toggleOutput(collector);
    }
  }

  toggleOutput(collector: CollectorInfo): void {
    if (this.expandedId === collector.id) {
      this.expandedId = null;
      this.outputData = null;
      this.cdr.markForCheck();
      return;
    }

    this.expandedId = collector.id;
    this.outputData = null;
    this.outputLoading = true;
    this.cdr.markForCheck();

    this.api.getCollectorOutput(collector.id).subscribe({
      next: (res) => {
        this.outputData = res.data;
        this.outputFactCount = res.fact_count;
        this.outputFileSize = res.file_size_bytes;
        this.outputLoading = false;
        this.cdr.markForCheck();
        setTimeout(() => document.getElementById('collector-output')?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
      },
      error: () => {
        this.outputLoading = false;
        this.expandedId = null;
        this.snack.open('Failed to load output', 'Dismiss', { duration: 4000 });
        this.cdr.markForCheck();
      },
    });
  }

  closeOutput(): void {
    this.expandedId = null;
    this.outputData = null;
    this.cdr.markForCheck();
  }

  formatBytes(bytes: number): string {
    return formatBytesUtil(bytes);
  }
}
