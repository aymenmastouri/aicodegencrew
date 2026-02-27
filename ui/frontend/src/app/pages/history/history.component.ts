import { Component, OnInit, OnDestroy, ChangeDetectorRef, ViewChild, ElementRef } from '@angular/core';
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
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { RouterLink } from '@angular/router';

import { PipelineService, RunHistoryEntry, RunDetail, HistoryStats } from '../../services/pipeline.service';
import {
  humanizePhaseId,
  shortPhase as shortPhaseUtil,
  formatDuration as formatDurationUtil,
  formatNumber as formatNumberUtil,
} from '../../shared/phase-utils';
import { statusLabel } from '../../shared/status';

/** Keys whose values are masked by default in the run-detail environment panel. */
const SECRET_KEY_PATTERNS = [/api[_-]?key/i, /secret/i, /password/i, /token/i, /credential/i, /private[_-]?key/i];

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
    MatCheckboxModule,
    MatSnackBarModule,
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
        @if (selectedForCompare.size === 2) {
          <button mat-flat-button color="primary" (click)="showComparison()">
            <mat-icon>compare_arrows</mat-icon> Compare ({{ selectedForCompare.size }})
          </button>
        } @else if (selectedForCompare.size > 0) {
          <button mat-stroked-button disabled>
            <mat-icon>compare_arrows</mat-icon> Select {{ 2 - selectedForCompare.size }} more
          </button>
        }
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

      <!-- Stats Summary Bar -->
      @if (stats) {
        <div class="stats-bar">
          <div class="stat-item">
            <mat-icon>play_arrow</mat-icon>
            <strong>{{ stats.total_runs }}</strong> runs
          </div>
          <div class="stat-item">
            <mat-icon>restart_alt</mat-icon>
            <strong>{{ stats.total_resets }}</strong> resets
          </div>
          <div class="stat-item">
            <mat-icon>check_circle</mat-icon>
            <strong class="success-text">{{ stats.success_rate }}%</strong> success rate
          </div>
          <div class="stat-item">
            <mat-icon>timer</mat-icon>
            <strong>{{ formatDurationShort(stats.avg_duration_seconds) }}</strong> avg duration
          </div>
          @if (stats.total_tokens > 0) {
            <div class="stat-item">
              <mat-icon>token</mat-icon>
              <strong>{{ formatNumber(stats.total_tokens) }}</strong> total tokens
            </div>
          }
          @if (stats.total_deleted_files > 0) {
            <div class="stat-item">
              <mat-icon>delete_sweep</mat-icon>
              <strong>{{ stats.total_deleted_files }}</strong> files cleaned
            </div>
          }
          @if (stats.most_used_preset) {
            <div class="stat-item">
              <mat-icon>playlist_play</mat-icon>
              <strong>{{ stats.most_used_preset }}</strong>
            </div>
          }
        </div>
      }

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
            <!-- Compare Checkbox Column -->
            <ng-container matColumnDef="compare">
              <th mat-header-cell *matHeaderCellDef class="compare-col"></th>
              <td mat-cell *matCellDef="let row" class="compare-col">
                @if (row.trigger !== 'reset') {
                  <mat-checkbox
                    [checked]="selectedForCompare.has(row.run_id)"
                    (change)="toggleCompareSelection(row.run_id, $event.checked)"
                    (click)="$event.stopPropagation()"
                    [disabled]="!selectedForCompare.has(row.run_id) && selectedForCompare.size >= 2"
                    matTooltip="Select for comparison"
                  ></mat-checkbox>
                }
              </td>
            </ng-container>

            <!-- Trigger Column -->
            <ng-container matColumnDef="trigger">
              <th mat-header-cell *matHeaderCellDef>Type</th>
              <td mat-cell *matCellDef="let row">
                @if (row.trigger === 'reset') {
                  <span class="trigger-chip trigger-reset">
                    <mat-icon class="chip-icon">restart_alt</mat-icon> Reset
                  </span>
                } @else {
                  <span class="trigger-chip trigger-run"> <mat-icon class="chip-icon">play_arrow</mat-icon> Run </span>
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
                <div class="phase-chips-inline">
                  @for (ph of row.phases; track ph) {
                    <span class="phase-chip-sm" [matTooltip]="humanize(ph)">{{ shortPhase(ph) }}</span>
                  }
                </div>
              </td>
            </ng-container>

            <!-- Status Column -->
            <ng-container matColumnDef="status">
              <th mat-header-cell *matHeaderCellDef>Status</th>
              <td mat-cell *matCellDef="let row">
                <span class="status-chip" [class]="'status-' + displayStatus(row)">{{ displayStatusLabel(row) }}</span>
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
                <div>
                  {{ row.duration_seconds ? formatDurationShort(row.duration_seconds) : row.duration || '—' }}
                </div>
                @if (row.trigger === 'reset' && row.deleted_count) {
                  <span class="deleted-badge">
                    <mat-icon class="micro-icon">delete_sweep</mat-icon>
                    {{ row.deleted_count }} files
                  </span>
                }
                @if (row.trigger !== 'reset' && row.total_tokens) {
                  <span class="token-badge">
                    <mat-icon class="micro-icon">token</mat-icon>
                    {{ formatNumber(row.total_tokens) }}
                  </span>
                }
              </td>
            </ng-container>

            <!-- Actions Column -->
            <ng-container matColumnDef="actions">
              <th mat-header-cell *matHeaderCellDef></th>
              <td mat-cell *matCellDef="let row">
                <button
                  mat-icon-button
                  matTooltip="View details"
                  [attr.aria-label]="selectedRun?.run_id === row.run_id ? 'Collapse details' : 'View details'"
                  (click)="toggleDetail(row); $event.stopPropagation()"
                >
                  <mat-icon>{{ selectedRun?.run_id === row.run_id ? 'expand_less' : 'expand_more' }}</mat-icon>
                </button>
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr
              mat-row
              *matRowDef="let row; columns: displayedColumns"
              class="table-row"
              [class.row-selected]="selectedRun?.run_id === row.run_id"
              (click)="toggleDetail(row)"
            ></tr>
          </table>
          <mat-paginator [pageSize]="20" [pageSizeOptions]="[10, 20, 50]" showFirstLastButtons></mat-paginator>
        </div>

        <!-- Comparison Panel -->
        @if (comparisonVisible && comparisonRuns.length === 2) {
          <div class="compare-panel">
            <div class="compare-header">
              <h3 class="compare-title"><mat-icon>compare_arrows</mat-icon> Run Comparison</h3>
              <button mat-icon-button (click)="closeComparison()" matTooltip="Close comparison">
                <mat-icon>close</mat-icon>
              </button>
            </div>
            <div class="compare-grid">
              @for (run of comparisonRuns; track run.run_id) {
                <div class="compare-col-card">
                  <div class="compare-run-id mono-text">{{ run.run_id }}</div>
                  <span class="status-chip" [class]="'status-' + displayStatus(run)">{{ displayStatusLabel(run) }}</span>
                  <div class="compare-meta">
                    {{ run.started_at | date: 'medium' }}
                    @if (run.duration_seconds) {
                      <span>&middot; {{ formatDurationShort(run.duration_seconds) }}</span>
                    }
                  </div>
                  <div class="compare-phases">
                    @for (ph of run.phases; track ph) {
                      <span class="phase-chip-sm" [matTooltip]="humanize(ph)">{{ shortPhase(ph) }}</span>
                    }
                  </div>
                </div>
              }
            </div>
            @if (comparisonDetails.length === 2) {
              <h4 class="compare-section-title">Phase-by-Phase Comparison</h4>
              <div class="compare-table">
                <div class="ct-header">
                  <span class="ct-phase">Phase</span>
                  <span class="ct-status">{{ comparisonRuns[0].run_id }}</span>
                  <span class="ct-status">{{ comparisonRuns[1].run_id }}</span>
                  <span class="ct-delta">Delta</span>
                </div>
                @for (row of comparisonPhaseRows; track row.phase) {
                  <div class="ct-row">
                    <span class="ct-phase">{{ row.phase }}</span>
                    <span class="ct-status">
                      <span class="status-chip status-sm" [class]="'status-' + row.status1">{{ row.status1 }}</span>
                      @if (row.duration1) {
                        <span class="ct-dur">{{ formatDurationShort(row.duration1) }}</span>
                      }
                    </span>
                    <span class="ct-status">
                      <span class="status-chip status-sm" [class]="'status-' + row.status2">{{ row.status2 }}</span>
                      @if (row.duration2) {
                        <span class="ct-dur">{{ formatDurationShort(row.duration2) }}</span>
                      }
                    </span>
                    <span class="ct-delta" [class.delta-better]="row.delta < 0" [class.delta-worse]="row.delta > 0">
                      @if (row.delta !== 0 && (row.duration1 || row.duration2)) {
                        {{ row.delta > 0 ? '+' : '' }}{{ formatDurationShort(row.delta) }}
                      } @else {
                        —
                      }
                    </span>
                  </div>
                }
              </div>
            }
          </div>
        }

        <!-- Detail Panel -->
        @if (selectedRun) {
          <div class="detail-panel" #detailPanel>
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
                    <span class="status-chip status-lg" [class]="'status-' + displayStatus(detail)">{{
                      displayStatusLabel(detail)
                    }}</span>
                    @if (detail.duration) {
                      <span class="detail-duration">{{ detail.duration }}</span>
                    }
                  </div>
                </div>
              </div>

              <!-- Phase Timeline -->
              @if (detail.phase_results.length > 0) {
                <div class="detail-section">
                  <h3 class="detail-section-title"><mat-icon>account_tree</mat-icon> Phase Results</h3>
                  <div class="phase-timeline">
                    @for (phase of detail.phase_results; track $index) {
                      <div class="timeline-item" [class]="'tl-' + displayPhaseStatus(phase.status || 'unknown')">
                        <div class="tl-dot">
                          <mat-icon class="tl-icon">
                            {{ phaseStatusIcon(phase.status || 'unknown') }}
                          </mat-icon>
                        </div>
                        <div class="tl-content">
                          <div class="tl-header">
                            <span class="tl-name">{{
                              phase.name || humanize(phase.phase_id || '') || 'Phase ' + $index
                            }}</span>
                            <span
                              class="status-chip status-sm"
                              [class]="'status-' + displayPhaseStatus(phase.status || 'unknown')"
                            >
                              {{ displayPhaseStatus(phase.status || 'unknown') }}
                            </span>
                            @if (phase.duration || phase.duration_seconds) {
                              <span class="tl-duration">{{ phase.duration || phase.duration_seconds + 's' }}</span>
                            }
                          </div>
                          @if (phase.output_files && phase.output_files.length > 0) {
                            <div class="tl-files">
                              @for (file of phase.output_files; track file) {
                                <span class="file-chip">
                                  <mat-icon class="chip-icon">description</mat-icon>
                                  {{ getFileName(file) }}
                                </span>
                              }
                            </div>
                          }
                          @if (phase.error) {
                            <div class="tl-error">{{ phase.error }}</div>
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
                  <h3 class="detail-section-title"><mat-icon>monitoring</mat-icon> Metrics Events</h3>
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
                  <h3 class="detail-section-title"><mat-icon>settings</mat-icon> Environment</h3>
                  <div class="env-grid">
                    @for (key of objectKeys(detail.environment); track key) {
                      <div class="env-item">
                        <span class="env-key">{{ key }}</span>
                        <span class="env-value env-value-row">
                          @if (isSecretKey(key) && !revealedKeys.has(key)) {
                            <span class="env-masked">••••••••••••</span>
                            <button class="env-reveal-btn" matTooltip="Reveal value" (click)="toggleReveal(key)">
                              <mat-icon class="env-reveal-icon">visibility</mat-icon>
                            </button>
                          } @else {
                            <span>{{ detail.environment[key] }}</span>
                            @if (isSecretKey(key)) {
                              <button class="env-reveal-btn" matTooltip="Hide value" (click)="toggleReveal(key)">
                                <mat-icon class="env-reveal-icon">visibility_off</mat-icon>
                              </button>
                            }
                          }
                        </span>
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
        overflow-x: auto;
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
      /* Phase chips inline */
      .phase-chips-inline {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
      }
      .phase-chip-sm {
        display: inline-block;
        padding: 1px 7px;
        border-radius: 8px;
        font-size: 10px;
        font-weight: 500;
        background: var(--cg-gray-100);
        color: var(--cg-gray-600);
        white-space: nowrap;
      }
      /* Deleted badge */
      .deleted-badge {
        display: inline-flex;
        align-items: center;
        gap: 2px;
        font-size: 11px;
        color: var(--cg-error, #dc3545);
        opacity: 0.75;
      }
      /* Token badge */
      .token-badge {
        display: inline-flex;
        align-items: center;
        gap: 2px;
        font-size: 11px;
        color: var(--cg-gray-400);
      }
      .micro-icon {
        font-size: 12px;
        width: 12px;
        height: 12px;
      }
      /* Success text */
      .success-text {
        color: var(--cg-success, #28a745);
      }

      /* Chip icon size */
      .chip-icon {
        font-size: 14px;
        width: 14px;
        height: 14px;
      }

      /* Compare checkbox column */
      .compare-col {
        width: 40px;
        padding-right: 0 !important;
      }

      /* Comparison Panel */
      .compare-panel {
        margin-top: 16px;
        background: #fff;
        border-radius: 12px;
        padding: 24px;
        border: 1px solid rgba(0, 112, 173, 0.15);
      }
      .compare-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
      }
      .compare-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 16px;
        font-weight: 500;
        margin: 0;
        color: var(--cg-gray-900);
      }
      .compare-title .mat-icon {
        color: var(--cg-blue);
      }
      .compare-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        margin-bottom: 20px;
      }
      .compare-col-card {
        padding: 14px;
        border-radius: 10px;
        background: var(--cg-gray-50);
        border: 1px solid var(--cg-gray-100);
      }
      .compare-run-id {
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 6px;
      }
      .compare-meta {
        font-size: 12px;
        color: var(--cg-gray-500);
        margin-top: 6px;
      }
      .compare-phases {
        display: flex;
        gap: 4px;
        flex-wrap: wrap;
        margin-top: 8px;
      }
      .compare-section-title {
        font-size: 14px;
        font-weight: 500;
        margin: 0 0 10px;
        color: var(--cg-gray-700);
      }
      .compare-table {
        border: 1px solid var(--cg-gray-100);
        border-radius: 8px;
        overflow: hidden;
      }
      .ct-header {
        display: grid;
        grid-template-columns: 1.5fr 2fr 2fr 1fr;
        gap: 8px;
        padding: 8px 14px;
        background: var(--cg-gray-50);
        font-size: 11px;
        font-weight: 600;
        color: var(--cg-gray-500);
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }
      .ct-row {
        display: grid;
        grid-template-columns: 1.5fr 2fr 2fr 1fr;
        gap: 8px;
        padding: 8px 14px;
        font-size: 13px;
        border-top: 1px solid var(--cg-gray-50);
        align-items: center;
      }
      .ct-phase {
        font-weight: 500;
      }
      .ct-status {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .ct-dur {
        font-size: 11px;
        font-family: monospace;
        color: var(--cg-gray-500);
      }
      .ct-delta {
        font-size: 12px;
        font-family: monospace;
      }
      .delta-better {
        color: var(--cg-success);
      }
      .delta-worse {
        color: var(--cg-error);
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
      .tl-partial .tl-icon {
        color: var(--cg-warn, #f57c00);
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
      .env-value-row {
        display: flex;
        align-items: center;
        gap: 4px;
        flex: 1;
        min-width: 0;
      }
      .env-masked {
        letter-spacing: 2px;
        color: var(--cg-gray-400);
      }
      .env-reveal-btn {
        background: none;
        border: none;
        cursor: pointer;
        padding: 0;
        display: flex;
        align-items: center;
        color: var(--cg-gray-400);
        flex-shrink: 0;
      }
      .env-reveal-btn:hover {
        color: var(--cg-blue);
      }
      .env-reveal-icon {
        font-size: 14px;
        width: 14px;
        height: 14px;
      }
    `,
  ],
})
export class HistoryComponent implements OnInit, OnDestroy {
  loading = true;
  allEntries: RunHistoryEntry[] = [];
  dataSource = new MatTableDataSource<RunHistoryEntry>([]);
  displayedColumns = ['compare', 'trigger', 'run_id', 'preset', 'phases', 'status', 'started_at', 'duration', 'actions'];

  activeFilter = 'all';
  searchTerm = '';
  filters = [
    { value: 'all', label: 'All', icon: 'list', count: null as number | null },
    { value: 'run', label: 'Runs', icon: 'play_arrow', count: null as number | null },
    { value: 'reset', label: 'Resets', icon: 'restart_alt', count: null as number | null },
    { value: 'failed', label: 'Failed', icon: 'error', count: null as number | null },
  ];

  stats: HistoryStats | null = null;

  selectedRun: RunHistoryEntry | null = null;
  detail: RunDetail | null = null;
  detailLoading = false;

  /** Keys currently revealed in the environment panel (populated by user click). */
  revealedKeys = new Set<string>();

  /** Run comparison */
  selectedForCompare = new Set<string>();
  comparisonVisible = false;
  comparisonRuns: RunHistoryEntry[] = [];
  comparisonDetails: RunDetail[] = [];
  comparisonPhaseRows: { phase: string; status1: string; status2: string; duration1: number; duration2: number; delta: number }[] = [];

  private refreshTimer: ReturnType<typeof setInterval> | null = null;

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild('detailPanel') detailPanelRef!: ElementRef<HTMLElement>;

  constructor(
    private pipelineSvc: PipelineService,
    private cdr: ChangeDetectorRef,
    private snackBar: MatSnackBar,
  ) {}

  humanize(phaseId: string): string {
    return humanizePhaseId(phaseId);
  }

  displayStatus(entry: { status: string; run_outcome?: string }): string {
    if (!entry) return 'unknown';
    if (entry.status !== 'completed') return entry.status ?? 'unknown';
    if (entry.run_outcome === 'partial') return 'partial';
    if (entry.run_outcome === 'all_skipped') return 'success'; // green — "already current" is a success
    return entry.status;
  }

  displayStatusLabel(entry: { status: string; run_outcome?: string }): string {
    if (!entry) return 'Unknown';
    if (entry.run_outcome === 'all_skipped') return 'already current';
    return statusLabel(this.displayStatus(entry));
  }

  displayPhaseStatus(status: string): string {
    if (status === 'success') return 'completed';
    return status;
  }

  phaseStatusIcon(status: string): string {
    const normalized = this.displayPhaseStatus(status);
    if (normalized === 'completed') return 'check_circle';
    if (normalized === 'partial') return 'warning';
    if (normalized === 'failed') return 'error';
    if (normalized === 'skipped') return 'skip_next';
    return 'radio_button_unchecked';
  }

  ngOnInit(): void {
    this.loadHistory();
    this.loadStats();
    this.refreshTimer = setInterval(() => {
      this.loadHistory();
      this.loadStats();
    }, 30000);
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

  loadStats(): void {
    this.pipelineSvc.getHistoryStats().subscribe({
      next: (s) => {
        this.stats = s;
        this.cdr.markForCheck();
      },
      error: () => {
        // Stats are non-critical, fail silently
      },
    });
  }

  formatDurationShort(seconds: number): string {
    return formatDurationUtil(seconds);
  }

  formatNumber(n: number): string {
    return formatNumberUtil(n);
  }

  shortPhase(phaseId: string): string {
    return shortPhaseUtil(phaseId);
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

  toggleCompareSelection(runId: string, checked: boolean): void {
    if (checked) {
      if (this.selectedForCompare.size < 2) {
        this.selectedForCompare.add(runId);
      }
    } else {
      this.selectedForCompare.delete(runId);
    }
  }

  showComparison(): void {
    const ids = [...this.selectedForCompare];
    this.comparisonRuns = ids
      .map((id) => this.allEntries.find((e) => e.run_id === id))
      .filter((e): e is RunHistoryEntry => !!e);

    this.comparisonDetails = [];
    this.comparisonPhaseRows = [];
    this.comparisonVisible = true;

    // Fetch details for both runs — only build comparison when BOTH succeed
    let loaded = 0;
    let failed = 0;
    for (const runId of ids) {
      this.pipelineSvc.getRunDetail(runId).subscribe({
        next: (d) => {
          this.comparisonDetails.push(d);
          loaded++;
          if (loaded === 2) {
            this.buildComparisonRows();
          }
          this.cdr.markForCheck();
        },
        error: () => {
          failed++;
          if (loaded + failed === ids.length && loaded < 2) {
            this.comparisonVisible = false;
            this.snackBar.open('Could not load run details for comparison', 'OK', { duration: 4000 });
          }
          this.cdr.markForCheck();
        },
      });
    }
    this.cdr.markForCheck();
  }

  closeComparison(): void {
    this.comparisonVisible = false;
    this.selectedForCompare.clear();
  }

  private buildComparisonRows(): void {
    if (this.comparisonDetails.length < 2) return;
    const d1 = this.comparisonDetails[0];
    const d2 = this.comparisonDetails[1];
    const phases1 = new Map((d1.phase_results || []).map((p) => [p.phase_id || p.name, p]));
    const phases2 = new Map((d2.phase_results || []).map((p) => [p.phase_id || p.name, p]));
    const allPhases = new Set([...phases1.keys(), ...phases2.keys()]);

    this.comparisonPhaseRows = [...allPhases].map((phase) => {
      const p1 = phases1.get(phase);
      const p2 = phases2.get(phase);
      const dur1 = p1?.duration_seconds || 0;
      const dur2 = p2?.duration_seconds || 0;
      return {
        phase: p1?.name || p2?.name || this.humanize(phase ?? ''),
        status1: this.displayPhaseStatus(p1?.status || '—'),
        status2: this.displayPhaseStatus(p2?.status || '—'),
        duration1: dur1,
        duration2: dur2,
        delta: dur2 - dur1,
      };
    });
  }

  toggleDetail(row: RunHistoryEntry): void {
    if (this.selectedRun?.run_id === row.run_id) {
      this.selectedRun = null;
      this.detail = null;
      return;
    }
    this.selectedRun = row;
    this.detail = null;
    this.revealedKeys.clear();
    this.detailLoading = true;
    this.cdr.markForCheck();
    // Scroll detail panel into view after Angular renders it
    setTimeout(() => {
      this.detailPanelRef?.nativeElement?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 50);

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
          run_outcome: row.run_outcome,
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
    return (this.detail.metrics_events ?? []).filter((e) => e['event'] === type).length;
  }

  getFileName(path: string): string {
    return path.split('/').pop() || path.split('\\').pop() || path;
  }

  objectKeys(obj: Record<string, unknown>): string[] {
    return Object.keys(obj);
  }

  isSecretKey(key: string): boolean {
    return SECRET_KEY_PATTERNS.some((re) => re.test(key));
  }

  toggleReveal(key: string): void {
    if (this.revealedKeys.has(key)) {
      this.revealedKeys.delete(key);
    } else {
      this.revealedKeys.add(key);
    }
    this.cdr.markForCheck();
  }
}
