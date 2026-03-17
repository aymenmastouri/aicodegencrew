import { Component, OnInit, OnDestroy, ChangeDetectorRef, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
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
import { MatTabsModule } from '@angular/material/tabs';
import { MatBadgeModule } from '@angular/material/badge';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

import {
  ApiService,
  CollectorInfo,
  CollectorListResponse,
  EcosystemInfo,
  EcosystemListResponse,
} from '../../services/api.service';
import { formatBytes as formatBytesUtil } from '../../shared/phase-utils';

/** All 16 architecture dimensions in display order */
const ALL_DIMENSIONS: string[] = [
  'system',
  'containers',
  'components',
  'interfaces',
  'data_model',
  'runtime',
  'infrastructure',
  'dependencies',
  'workflows',
  'tech_versions',
  'security_details',
  'validation',
  'tests',
  'error_handling',
  'build_system',
  'evidence',
];

/** Cross-cutting dimensions that span all ecosystems */
const CROSS_CUTTING_DIMENSIONS = new Set([
  'system',
  'infrastructure',
  'evidence',
]);

@Component({
  selector: 'app-collectors',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    FormsModule,
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
    MatTabsModule,
    MatBadgeModule,
    MatFormFieldModule,
    MatInputModule,
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
            <mat-icon>account_tree</mat-icon>
            <span class="stat-value">{{ data?.specialist_count ?? 0 }}</span>
            <span class="stat-label">Specialists</span>
          </div>
          <div class="stat-item">
            <mat-icon>data_object</mat-icon>
            <span class="stat-value">{{ totalFacts }}</span>
            <span class="stat-label">Total Facts</span>
          </div>
          <div class="stat-item">
            <mat-icon>eco</mat-icon>
            <span class="stat-value">{{ ecoData?.active_count ?? 0 }}/{{ ecoData?.total ?? 0 }}</span>
            <span class="stat-label">Ecosystems</span>
          </div>
        </div>

        <!-- Tabs: Collectors + Coverage Matrix + Ecosystems -->
        <mat-tab-group animationDuration="200ms" class="collectors-tabs">

          <!-- Tab 1: Collectors Table -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">list</mat-icon>
              Collectors
            </ng-template>

            <mat-card class="table-card tab-content">
              <table mat-table [dataSource]="collectors" class="collectors-table">
                <ng-container matColumnDef="step">
                  <th mat-header-cell *matHeaderCellDef>Step</th>
                  <td mat-cell *matCellDef="let c">
                    <span class="step-badge" [class.step-core]="c.category === 'core'">{{ c.step }}</span>
                  </td>
                </ng-container>

                <ng-container matColumnDef="name">
                  <th mat-header-cell *matHeaderCellDef>Collector</th>
                  <td mat-cell *matCellDef="let c">
                    <div class="collector-name">{{ c.name }}</div>
                    <div class="collector-desc">{{ c.description }}</div>
                  </td>
                </ng-container>

                <ng-container matColumnDef="dimension">
                  <th mat-header-cell *matHeaderCellDef>Dimension</th>
                  <td mat-cell *matCellDef="let c">
                    <span class="chip dimension-chip">{{ c.dimension }}</span>
                  </td>
                </ng-container>

                <ng-container matColumnDef="ecosystems">
                  <th mat-header-cell *matHeaderCellDef>Ecosystems</th>
                  <td mat-cell *matCellDef="let c">
                    @if (c.ecosystems.length === 0) {
                      <span class="chip chip-crosscut">all</span>
                    } @else {
                      <div class="eco-chips-cell">
                        @for (eid of c.ecosystems; track eid) {
                          <span class="chip chip-eco" [class.chip-eco-active]="isEcoActive(eid)">{{ ecoShortName(eid) }}</span>
                        }
                      </div>
                    }
                  </td>
                </ng-container>

                <ng-container matColumnDef="delegation">
                  <th mat-header-cell *matHeaderCellDef>Delegation</th>
                  <td mat-cell *matCellDef="let c">
                    @if (c.specialist_count > 0) {
                      <span class="delegation-badge" [matTooltip]="'Delegates to ' + c.specialist_count + ' ecosystem specialists'">
                        <mat-icon class="delegation-icon">arrow_forward</mat-icon>
                        {{ c.specialist_count }}
                      </span>
                    } @else {
                      <span class="delegation-direct" matTooltip="Cross-cutting collector, runs directly">direct</span>
                    }
                  </td>
                </ng-container>

                <ng-container matColumnDef="category">
                  <th mat-header-cell *matHeaderCellDef>Category</th>
                  <td mat-cell *matCellDef="let c">
                    <span class="chip" [class.chip-core]="c.category === 'core'" [class.chip-optional]="c.category === 'optional'">
                      @if (c.category === 'core') { <mat-icon class="chip-icon">lock</mat-icon> }
                      {{ c.category }}
                    </span>
                  </td>
                </ng-container>

                <ng-container matColumnDef="fact_count">
                  <th mat-header-cell *matHeaderCellDef>Facts</th>
                  <td mat-cell *matCellDef="let c">
                    <span class="fact-count" [class.no-data]="c.fact_count === null">
                      {{ c.fact_count !== null ? c.fact_count : '\u2014' }}
                    </span>
                  </td>
                </ng-container>

                <ng-container matColumnDef="status">
                  <th mat-header-cell *matHeaderCellDef>Status</th>
                  <td mat-cell *matCellDef="let c">
                    @if (!c.can_disable) {
                      <span class="chip chip-core"><mat-icon class="chip-icon">lock</mat-icon> always on</span>
                    } @else {
                      <mat-slide-toggle [checked]="c.enabled" (change)="onToggle(c, $event.checked)" [disabled]="toggling === c.id" color="primary"></mat-slide-toggle>
                    }
                  </td>
                </ng-container>

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
                <tr mat-row *matRowDef="let row; columns: displayedColumns" class="collector-row" [class.expanded-row]="expandedId === row.id" (click)="onRowClick(row)"></tr>
              </table>
            </mat-card>

            @if (expandedId && outputData) {
              <mat-card class="output-card" id="collector-output">
                <mat-card-header>
                  <mat-icon mat-card-avatar>data_object</mat-icon>
                  <mat-card-title>{{ expandedId }} output</mat-card-title>
                  <mat-card-subtitle>{{ outputFactCount }} facts &middot; {{ formatBytes(outputFileSize) }}</mat-card-subtitle>
                </mat-card-header>
                <mat-card-content>
                  <pre class="output-json">{{ outputPreview }}</pre>
                </mat-card-content>
                <mat-card-actions align="end">
                  <button mat-button (click)="closeOutput()">Close</button>
                </mat-card-actions>
              </mat-card>
            }
            @if (expandedId && outputLoading) {
              <div class="loading-center" style="padding: 24px 0"><mat-spinner diameter="32"></mat-spinner></div>
            }
          </mat-tab>

          <!-- Tab 2: Coverage Matrix -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">grid_on</mat-icon>
              Coverage Matrix
            </ng-template>

            <div class="tab-content">
              <mat-card class="matrix-card">
                <mat-card-header>
                  <mat-icon mat-card-avatar>grid_on</mat-icon>
                  <mat-card-title>Dimension x Ecosystem Coverage</mat-card-title>
                  <mat-card-subtitle>
                    {{ allDimensions.length }} dimensions across {{ ecosystems.length }} ecosystems
                    &mdash; showing which ecosystem specialists cover each dimension
                  </mat-card-subtitle>
                </mat-card-header>
                <mat-card-content>
                  <div class="matrix-scroll">
                    <table class="coverage-matrix">
                      <thead>
                        <tr>
                          <th class="matrix-dim-header">Dimension</th>
                          @for (eco of ecosystems; track eco.id) {
                            <th class="matrix-eco-header" [class.matrix-eco-active]="eco.detected && eco.enabled" [class.matrix-eco-disabled]="!eco.enabled">
                              <mat-icon class="matrix-eco-icon" [class.eco-active]="eco.detected && eco.enabled" [class.eco-inactive]="!eco.detected || !eco.enabled">
                                {{ ecoIcon(eco.id) }}
                              </mat-icon>
                              <span class="matrix-eco-name">{{ ecoShortName(eco.id) }}</span>
                              @if (!eco.enabled) {
                                <span class="matrix-disabled-label">disabled</span>
                              }
                            </th>
                          }
                          <th class="matrix-facts-header">Facts</th>
                        </tr>
                      </thead>
                      <tbody>
                        @for (dim of allDimensions; track dim) {
                          <tr class="matrix-row" [class.matrix-row-crosscut]="isCrossCutting(dim)">
                            <td class="matrix-dim-cell">
                              <span class="chip dimension-chip">{{ dim }}</span>
                            </td>
                            @if (isCrossCutting(dim)) {
                              <td class="matrix-cell matrix-cell-crosscut" [attr.colspan]="ecosystems.length">
                                <span class="chip chip-crosscut">
                                  <mat-icon class="chip-icon">public</mat-icon>
                                  all ecosystems
                                </span>
                              </td>
                            } @else {
                              @for (eco of ecosystems; track eco.id) {
                                <td class="matrix-cell" [class.matrix-col-active]="eco.detected && eco.enabled" [class.matrix-col-disabled]="!eco.enabled">
                                  @if (!eco.enabled) {
                                    <mat-icon class="matrix-disabled-icon">block</mat-icon>
                                  } @else if (ecoDimensions(eco).has(dim)) {
                                    <mat-icon class="matrix-check">check_circle</mat-icon>
                                  } @else {
                                    <mat-icon class="matrix-empty">remove</mat-icon>
                                  }
                                </td>
                              }
                            }
                            <td class="matrix-facts-cell">
                              <span class="fact-count" [class.no-data]="getDimensionFactCount(dim) === 0">
                                {{ getDimensionFactCount(dim) || '\u2014' }}
                              </span>
                            </td>
                          </tr>
                        }
                      </tbody>
                    </table>
                  </div>
                </mat-card-content>
              </mat-card>

              <!-- Matrix Legend -->
              <div class="matrix-legend">
                <div class="legend-item">
                  <mat-icon class="matrix-check" style="font-size: 16px; width: 16px; height: 16px;">check_circle</mat-icon>
                  <span>Ecosystem has specialist</span>
                </div>
                <div class="legend-item">
                  <mat-icon class="matrix-empty" style="font-size: 16px; width: 16px; height: 16px;">remove</mat-icon>
                  <span>Not supported</span>
                </div>
                <div class="legend-item">
                  <span class="chip chip-crosscut" style="font-size: 10px; padding: 1px 6px;">all ecosystems</span>
                  <span>Cross-cutting dimension</span>
                </div>
              </div>
            </div>
          </mat-tab>

          <!-- Ecosystem Tabs -->
          @for (eco of ecosystems; track eco.id) {
            <mat-tab [disabled]="false">
              <ng-template mat-tab-label>
                <mat-icon class="tab-icon" [class.eco-active]="eco.detected && eco.enabled" [class.eco-inactive]="!eco.detected || !eco.enabled">
                  {{ ecoIcon(eco.id) }}
                </mat-icon>
                <span [class.eco-label-disabled]="!eco.enabled">{{ eco.name }}</span>
                @if (!eco.enabled) {
                  <span class="tab-badge disabled">disabled</span>
                } @else if (eco.detected) {
                  <span class="tab-badge active">active</span>
                }
              </ng-template>

              <div class="eco-panel tab-content" [class.eco-panel-disabled]="!eco.enabled">
                <!-- Detection Status + Controls -->
                <div class="eco-status-bar">
                  <span class="chip" [class.chip-active]="eco.detected && eco.enabled" [class.chip-inactive]="!eco.detected || !eco.enabled">
                    <mat-icon class="chip-icon">{{ !eco.enabled ? 'block' : eco.detected ? 'check_circle' : 'cancel' }}</mat-icon>
                    {{ !eco.enabled ? 'Disabled' : eco.detected ? 'Detected' : 'Not detected' }}
                  </span>
                  <mat-slide-toggle
                    [checked]="eco.enabled"
                    (change)="onEcoToggle(eco, $event.checked)"
                    [disabled]="ecoToggling === eco.id"
                    color="primary"
                    matTooltip="Enable or disable this ecosystem">
                  </mat-slide-toggle>
                  <div class="eco-priority-control">
                    <span class="eco-priority-label">Priority</span>
                    <input type="number" class="eco-priority-input"
                      [value]="eco.priority" min="1" max="999"
                      #priorityInput
                      (keydown.enter)="onPriorityChange(eco, +priorityInput.value)"
                      [disabled]="ecoToggling === eco.id">
                    <button mat-icon-button class="eco-priority-save"
                      (click)="onPriorityChange(eco, +priorityInput.value)"
                      [disabled]="ecoToggling === eco.id"
                      matTooltip="Save priority">
                      <mat-icon>save</mat-icon>
                    </button>
                  </div>
                </div>

                <!-- Dimension Coverage Card -->
                <mat-card class="eco-card eco-card-full coverage-card">
                  <mat-card-header>
                    <mat-icon mat-card-avatar>verified</mat-icon>
                    <mat-card-title>Dimension Coverage</mat-card-title>
                    <mat-card-subtitle>
                      {{ ecoDimensions(eco).size }} of {{ allDimensions.length }} dimensions supported
                      &mdash; {{ eco.specialist_count }} specialist collector{{ eco.specialist_count !== 1 ? 's' : '' }}
                    </mat-card-subtitle>
                  </mat-card-header>
                  <mat-card-content>
                    <!-- Progress bar -->
                    <div class="coverage-bar-container">
                      <div class="coverage-bar-track">
                        <div class="coverage-bar-fill" [style.width.%]="getCoveragePercent(eco)"></div>
                      </div>
                      <span class="coverage-bar-label">{{ getCoveragePercent(eco) }}%</span>
                    </div>

                    <!-- Dimension chips -->
                    <div class="coverage-chips">
                      @for (dim of allDimensions; track dim) {
                        <span class="chip"
                          [class.coverage-chip-active]="ecoDimensions(eco).has(dim) && getDimensionFactCount(dim) > 0"
                          [class.coverage-chip-supported]="ecoDimensions(eco).has(dim) && getDimensionFactCount(dim) === 0"
                          [class.coverage-chip-unsupported]="!ecoDimensions(eco).has(dim)"
                          [matTooltip]="ecoDimensions(eco).has(dim) ? 'Supported' : 'Not supported'">
                          {{ dim }}
                        </span>
                      }
                    </div>

                    <!-- Legend -->
                    <div class="coverage-legend">
                      <span class="coverage-legend-item">
                        <span class="coverage-dot coverage-dot-active"></span> Has facts
                      </span>
                      <span class="coverage-legend-item">
                        <span class="coverage-dot coverage-dot-supported"></span> Supported
                      </span>
                      <span class="coverage-legend-item">
                        <span class="coverage-dot coverage-dot-unsupported"></span> Not supported
                      </span>
                    </div>
                  </mat-card-content>
                </mat-card>

                <!-- Two-column grid -->
                <div class="eco-grid">

                  <!-- Marker Files -->
                  <mat-card class="eco-card">
                    <mat-card-header>
                      <mat-icon mat-card-avatar>search</mat-icon>
                      <mat-card-title>Marker Files</mat-card-title>
                      <mat-card-subtitle>Build files that indicate this ecosystem</mat-card-subtitle>
                    </mat-card-header>
                    <mat-card-content>
                      <div class="eco-list">
                        @for (m of eco.marker_files; track m.filename) {
                          <div class="eco-list-item">
                            <code>{{ m.filename }}</code>
                            <span class="eco-list-label">{{ m.framework_label }}</span>
                          </div>
                        }
                      </div>
                    </mat-card-content>
                  </mat-card>

                  <!-- File Extensions -->
                  <mat-card class="eco-card">
                    <mat-card-header>
                      <mat-icon mat-card-avatar>description</mat-icon>
                      <mat-card-title>File Extensions</mat-card-title>
                      <mat-card-subtitle>Source, excluded, and skipped directories</mat-card-subtitle>
                    </mat-card-header>
                    <mat-card-content>
                      <div class="ext-section">
                        <span class="ext-label">Source</span>
                        <div class="ext-chips">
                          @for (e of eco.source_extensions; track e) {
                            <span class="chip chip-ext">{{ e }}</span>
                          }
                        </div>
                      </div>
                      <div class="ext-section">
                        <span class="ext-label">Excluded</span>
                        <div class="ext-chips">
                          @for (e of eco.exclude_extensions; track e) {
                            <span class="chip chip-exclude">{{ e }}</span>
                          }
                        </div>
                      </div>
                      <div class="ext-section">
                        <span class="ext-label">Skip Directories</span>
                        <div class="ext-chips">
                          @for (d of eco.skip_directories; track d) {
                            <span class="chip chip-skip">{{ d }}/</span>
                          }
                        </div>
                      </div>
                    </mat-card-content>
                  </mat-card>

                  <!-- Detected Containers -->
                  <mat-card class="eco-card">
                    <mat-card-header>
                      <mat-icon mat-card-avatar>inventory_2</mat-icon>
                      <mat-card-title>Containers</mat-card-title>
                      <mat-card-subtitle>{{ eco.containers.length }} deployable unit{{ eco.containers.length !== 1 ? 's' : '' }} detected</mat-card-subtitle>
                    </mat-card-header>
                    <mat-card-content>
                      @if (eco.containers.length === 0) {
                        <p class="eco-empty">No containers detected</p>
                      } @else {
                        <div class="eco-list">
                          @for (c of eco.containers; track c['name']) {
                            <div class="eco-list-item">
                              <strong>{{ c['name'] }}</strong>
                              <span class="chip dimension-chip">{{ c['type'] }}</span>
                              <span class="eco-list-label">{{ c['technology'] }}</span>
                            </div>
                          }
                        </div>
                      }
                    </mat-card-content>
                  </mat-card>

                  <!-- Detected Versions -->
                  <mat-card class="eco-card">
                    <mat-card-header>
                      <mat-icon mat-card-avatar>update</mat-icon>
                      <mat-card-title>Tech Versions</mat-card-title>
                      <mat-card-subtitle>{{ eco.versions.length }} version{{ eco.versions.length !== 1 ? 's' : '' }} extracted</mat-card-subtitle>
                    </mat-card-header>
                    <mat-card-content>
                      @if (eco.versions.length === 0) {
                        <p class="eco-empty">No versions extracted</p>
                      } @else {
                        <div class="eco-list">
                          @for (v of eco.versions; track v['technology']) {
                            <div class="eco-list-item">
                              <strong>{{ v['technology'] }}</strong>
                              <code class="version-badge">{{ v['version'] }}</code>
                              <span class="eco-list-label">{{ v['category'] }}</span>
                            </div>
                          }
                        </div>
                      }
                    </mat-card-content>
                  </mat-card>

                </div>

                <!-- Component Technologies -->
                @if (eco.component_technologies.length > 0) {
                  <mat-card class="eco-card eco-card-full">
                    <mat-card-header>
                      <mat-icon mat-card-avatar>widgets</mat-icon>
                      <mat-card-title>Component Technologies</mat-card-title>
                      <mat-card-subtitle>Containers with these technologies are routed to this ecosystem</mat-card-subtitle>
                    </mat-card-header>
                    <mat-card-content>
                      <div class="ext-chips">
                        @for (t of eco.component_technologies; track t) {
                          <span class="chip dimension-chip">{{ t }}</span>
                        }
                      </div>
                    </mat-card-content>
                  </mat-card>
                }
              </div>
            </mat-tab>
          }
        </mat-tab-group>
      }
    </div>
  `,
  styles: [
    `
      /* Tabs */
      .collectors-tabs { margin-top: 8px; }
      .tab-icon { margin-right: 6px; font-size: 18px !important; width: 18px !important; height: 18px !important; }
      .tab-badge { margin-left: 6px; font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; padding: 1px 6px; border-radius: 8px; }
      .tab-badge.active { background: rgba(76, 175, 80, 0.15); color: #2e7d32; }
      .tab-badge.disabled { background: rgba(244, 67, 54, 0.12); color: #c62828; }
      .eco-label-disabled { opacity: 0.5; }
      .tab-content { margin-top: 16px; }
      .eco-active { color: #2e7d32 !important; }
      .eco-inactive { color: var(--cg-gray-300) !important; }

      /* Table */
      .table-card { overflow: hidden; }
      .collectors-table { width: 100%; }
      .collector-row { cursor: pointer; }
      .collector-row:hover { background: rgba(0, 112, 173, 0.03); }
      .expanded-row { background: rgba(18, 171, 219, 0.06) !important; }

      /* Step badge */
      .step-badge { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 50%; background: var(--cg-gray-200); font-size: 12px; font-weight: 700; color: var(--cg-gray-500); }
      .step-core { background: var(--cg-vibrant); color: white; }

      /* Collector info */
      .collector-name { font-weight: 600; font-size: 13px; color: var(--cg-navy); }
      .collector-desc { font-size: 11px; color: var(--cg-gray-400); margin-top: 2px; }

      /* Chips */
      .chip { display: inline-flex; align-items: center; gap: 4px; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }
      .chip-icon { font-size: 13px !important; width: 13px !important; height: 13px !important; }
      .chip-core { background: rgba(18, 171, 219, 0.12); color: var(--cg-vibrant); }
      .chip-optional { background: var(--cg-gray-100); color: var(--cg-gray-400); }
      .dimension-chip { background: rgba(18, 171, 219, 0.08); color: var(--cg-vibrant); }
      .chip-active { background: rgba(76, 175, 80, 0.12); color: #2e7d32; }
      .chip-inactive { background: var(--cg-gray-100); color: var(--cg-gray-400); }
      .eco-chips-cell { display: flex; flex-wrap: wrap; gap: 3px; }
      .chip-eco { background: var(--cg-gray-100); color: var(--cg-gray-500); font-size: 10px; padding: 2px 7px; }
      .chip-eco-active { background: rgba(76, 175, 80, 0.12); color: #2e7d32; }
      .chip-crosscut { background: rgba(156, 39, 176, 0.08); color: #7b1fa2; font-size: 10px; padding: 2px 7px; }
      .chip-ext { background: rgba(18, 171, 219, 0.08); color: var(--cg-vibrant); font-family: monospace; font-size: 11px; text-transform: none; }
      .chip-exclude { background: rgba(244, 67, 54, 0.08); color: #c62828; font-family: monospace; font-size: 11px; text-transform: none; }
      .chip-skip { background: rgba(255, 152, 0, 0.08); color: #e65100; font-family: monospace; font-size: 11px; text-transform: none; }

      /* Delegation column */
      .delegation-badge {
        display: inline-flex; align-items: center; gap: 3px;
        padding: 2px 8px; border-radius: 10px;
        background: rgba(18, 112, 173, 0.08); color: #1270ad;
        font-size: 12px; font-weight: 700; cursor: default;
      }
      .delegation-icon { font-size: 14px !important; width: 14px !important; height: 14px !important; }
      .delegation-direct {
        font-size: 11px; font-weight: 600; color: var(--cg-gray-400);
        text-transform: uppercase; letter-spacing: 0.3px; cursor: default;
      }

      /* Fact count */
      .fact-count { font-weight: 600; font-size: 14px; color: var(--cg-navy); }
      .no-data { color: var(--cg-gray-300); }

      /* Output preview */
      .output-card { margin-top: 16px; }
      .output-json { max-height: 500px; overflow: auto; background: var(--cg-dark); color: #eeffff; padding: 16px; border-radius: 8px; font-size: 12px; line-height: 1.5; white-space: pre-wrap; word-break: break-word; }

      /* ── Coverage Matrix ── */
      .matrix-card { border-radius: 12px; }
      .matrix-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }

      .coverage-matrix {
        width: 100%; border-collapse: separate; border-spacing: 0;
        font-size: 13px; min-width: 500px;
      }

      .coverage-matrix thead { position: sticky; top: 0; z-index: 2; }

      .matrix-dim-header {
        text-align: left; padding: 10px 16px; font-weight: 700; font-size: 11px;
        text-transform: uppercase; letter-spacing: 0.5px; color: var(--cg-gray-500);
        background: var(--cg-gray-50, #fafafa); border-bottom: 2px solid var(--cg-gray-200);
      }
      .matrix-eco-header {
        text-align: center; padding: 10px 12px; min-width: 80px;
        background: var(--cg-gray-50, #fafafa); border-bottom: 2px solid var(--cg-gray-200);
        vertical-align: middle;
      }
      .matrix-eco-header.matrix-eco-active {
        background: rgba(76, 175, 80, 0.06);
      }
      .matrix-eco-icon {
        font-size: 18px !important; width: 18px !important; height: 18px !important;
        display: block; margin: 0 auto 2px;
      }
      .matrix-eco-name {
        font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px;
        color: var(--cg-gray-600);
      }
      .matrix-facts-header {
        text-align: center; padding: 10px 12px; font-weight: 700; font-size: 11px;
        text-transform: uppercase; letter-spacing: 0.5px; color: var(--cg-gray-500);
        background: var(--cg-gray-50, #fafafa); border-bottom: 2px solid var(--cg-gray-200);
      }

      .matrix-row { transition: background 0.15s ease; }
      .matrix-row:hover { background: rgba(18, 112, 173, 0.03); }
      .matrix-row-crosscut { background: rgba(156, 39, 176, 0.02); }
      .matrix-row-crosscut:hover { background: rgba(156, 39, 176, 0.05); }

      .matrix-dim-cell {
        padding: 8px 16px; border-bottom: 1px solid var(--cg-gray-100);
        white-space: nowrap;
      }
      .matrix-cell {
        text-align: center; padding: 8px 12px;
        border-bottom: 1px solid var(--cg-gray-100);
      }
      .matrix-cell.matrix-col-active { background: rgba(76, 175, 80, 0.02); }
      .matrix-cell-crosscut {
        text-align: center; padding: 8px 12px;
        border-bottom: 1px solid var(--cg-gray-100);
      }
      .matrix-facts-cell {
        text-align: center; padding: 8px 12px;
        border-bottom: 1px solid var(--cg-gray-100);
      }

      .matrix-check { color: #2e7d32; font-size: 20px !important; width: 20px !important; height: 20px !important; }
      .matrix-empty { color: var(--cg-gray-200); font-size: 20px !important; width: 20px !important; height: 20px !important; }

      .matrix-legend {
        display: flex; gap: 20px; align-items: center;
        padding: 12px 0 0; margin-top: 8px;
        font-size: 12px; color: var(--cg-gray-500);
      }
      .legend-item { display: flex; align-items: center; gap: 6px; }

      /* ── Ecosystem Dimension Coverage Card ── */
      .coverage-card { margin-bottom: 16px; border-radius: 12px; }

      .coverage-bar-container {
        display: flex; align-items: center; gap: 12px; margin-bottom: 16px;
      }
      .coverage-bar-track {
        flex: 1; height: 8px; border-radius: 4px;
        background: var(--cg-gray-100); overflow: hidden;
      }
      .coverage-bar-fill {
        height: 100%; border-radius: 4px;
        background: linear-gradient(90deg, #1270ad, #2e7d32);
        transition: width 0.4s ease;
      }
      .coverage-bar-label {
        font-size: 14px; font-weight: 700; color: var(--cg-navy);
        min-width: 40px; text-align: right;
      }

      .coverage-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
      .coverage-chip-active { background: rgba(76, 175, 80, 0.15); color: #2e7d32; }
      .coverage-chip-supported { background: rgba(18, 112, 173, 0.12); color: #1270ad; }
      .coverage-chip-unsupported { background: var(--cg-gray-100); color: var(--cg-gray-300); }

      .coverage-legend {
        display: flex; gap: 16px; font-size: 11px; color: var(--cg-gray-500);
      }
      .coverage-legend-item { display: flex; align-items: center; gap: 5px; }
      .coverage-dot {
        display: inline-block; width: 8px; height: 8px; border-radius: 50%;
      }
      .coverage-dot-active { background: #2e7d32; }
      .coverage-dot-supported { background: #1270ad; }
      .coverage-dot-unsupported { background: var(--cg-gray-300); }

      /* Ecosystem panels */
      .eco-panel-disabled { opacity: 0.6; }
      .eco-status-bar { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
      .eco-priority-control {
        display: inline-flex; align-items: center; gap: 6px;
        margin-left: auto;
      }
      .eco-priority-label { font-size: 12px; color: var(--cg-gray-400); font-weight: 600; }
      .eco-priority-input {
        width: 60px; padding: 4px 8px; border: 1px solid var(--cg-gray-200);
        border-radius: 6px; font-size: 13px; font-weight: 600;
        color: var(--cg-navy); text-align: center; background: transparent;
      }
      .eco-priority-input:focus { outline: none; border-color: var(--cg-vibrant); }
      .eco-priority-save { transform: scale(0.8); }

      /* Matrix disabled column */
      .matrix-eco-disabled { opacity: 0.5; }
      .matrix-disabled-label {
        display: block; font-size: 9px; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.3px; color: #c62828; margin-top: 2px;
      }
      .matrix-col-disabled { background: rgba(0, 0, 0, 0.03); }
      .matrix-disabled-icon { color: var(--cg-gray-300); font-size: 18px !important; width: 18px !important; height: 18px !important; }
      .eco-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
      @media (max-width: 900px) { .eco-grid { grid-template-columns: 1fr; } }
      .eco-card { border-radius: 12px; }
      .eco-card-full { grid-column: 1 / -1; margin-top: 8px; }
      .eco-list { display: flex; flex-direction: column; gap: 8px; }
      .eco-list-item { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid var(--cg-gray-100); font-size: 13px; }
      .eco-list-item:last-child { border-bottom: none; }
      .eco-list-label { color: var(--cg-gray-400); font-size: 11px; margin-left: auto; }
      .eco-empty { color: var(--cg-gray-300); font-size: 13px; font-style: italic; }
      .ext-section { margin-bottom: 12px; }
      .ext-section:last-child { margin-bottom: 0; }
      .ext-label { display: block; font-size: 11px; font-weight: 600; color: var(--cg-gray-400); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
      .ext-chips { display: flex; flex-wrap: wrap; gap: 4px; }
      .version-badge { background: var(--cg-gray-100); padding: 1px 8px; border-radius: 8px; font-size: 12px; font-weight: 600; color: var(--cg-navy); }
    `,
  ],
})
export class CollectorsComponent implements OnInit, OnDestroy {
  private refreshTimer: ReturnType<typeof setInterval> | null = null;
  loading = true;
  data: CollectorListResponse | null = null;
  collectors: CollectorInfo[] = [];
  displayedColumns = ['step', 'name', 'dimension', 'ecosystems', 'delegation', 'category', 'fact_count', 'status', 'actions'];

  /** All 16 architecture dimensions in canonical order */
  allDimensions = ALL_DIMENSIONS;

  // Ecosystem data
  ecoData: EcosystemListResponse | null = null;
  ecosystems: EcosystemInfo[] = [];

  toggling: string | null = null;
  ecoToggling: string | null = null;
  expandedId: string | null = null;
  outputData: unknown = null;
  outputLoading = false;
  outputFactCount = 0;
  outputFileSize = 0;

  /** Cached dimension sets per ecosystem id */
  private ecoDimensionCache = new Map<string, Set<string>>();

  private readonly ecoIcons: Record<string, string> = {
    java_jvm: 'coffee',
    javascript_typescript: 'javascript',
    python: 'code',
    c_cpp: 'memory',
  };

  private readonly ecoShortNames: Record<string, string> = {
    java_jvm: 'Java',
    javascript_typescript: 'JS/TS',
    python: 'Python',
    c_cpp: 'C/C++',
  };

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
    this.refreshTimer = setInterval(() => this.load(), 15000);
  }

  ngOnDestroy(): void {
    if (this.refreshTimer) clearInterval(this.refreshTimer);
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

    this.api.getEcosystems().subscribe({
      next: (res) => {
        this.ecoData = res;
        this.ecosystems = res.ecosystems;
        this.ecoDimensionCache.clear();
        this.cdr.markForCheck();
      },
      error: () => {
        // Non-critical - ecosystem tab just won't show data
      },
    });
  }

  ecoIcon(id: string): string {
    return this.ecoIcons[id] ?? 'eco';
  }

  ecoShortName(id: string): string {
    return this.ecoShortNames[id] ?? id;
  }

  isEcoActive(id: string): boolean {
    return this.ecoData?.active_ids?.includes(id) ?? false;
  }

  /** Get the set of supported dimensions for an ecosystem (cached) */
  ecoDimensions(eco: EcosystemInfo): Set<string> {
    let cached = this.ecoDimensionCache.get(eco.id);
    if (!cached) {
      cached = new Set(eco.dimensions ?? []);
      this.ecoDimensionCache.set(eco.id, cached);
    }
    return cached;
  }

  /** Check if a dimension is cross-cutting (spans all ecosystems) */
  isCrossCutting(dim: string): boolean {
    return CROSS_CUTTING_DIMENSIONS.has(dim);
  }

  /** Get total fact count for a given dimension across all collectors */
  getDimensionFactCount(dim: string): number {
    return this.collectors
      .filter((c) => c.dimension === dim)
      .reduce((sum, c) => sum + (c.fact_count ?? 0), 0);
  }

  /** Get coverage percentage for an ecosystem */
  getCoveragePercent(eco: EcosystemInfo): number {
    if (this.allDimensions.length === 0) return 0;
    const supported = this.ecoDimensions(eco).size;
    return Math.round((supported / this.allDimensions.length) * 100);
  }

  onEcoToggle(eco: EcosystemInfo, enabled: boolean): void {
    this.ecoToggling = eco.id;
    this.api.toggleEcosystem(eco.id, enabled).subscribe({
      next: (updated) => {
        const idx = this.ecosystems.findIndex((e) => e.id === eco.id);
        if (idx >= 0) this.ecosystems[idx] = updated;
        this.ecoToggling = null;
        this.snack.open(`${eco.name} ${enabled ? 'enabled' : 'disabled'}`, 'OK', { duration: 2500 });
        this.ecoDimensionCache.clear();
        this.cdr.markForCheck();
      },
      error: () => {
        this.ecoToggling = null;
        this.snack.open(`Failed to toggle ${eco.name}`, 'Dismiss', { duration: 4000 });
        this.cdr.markForCheck();
      },
    });
  }

  onPriorityChange(eco: EcosystemInfo, priority: number): void {
    if (!priority || priority < 1 || priority > 999) {
      this.snack.open('Priority must be between 1 and 999', 'Dismiss', { duration: 3000 });
      return;
    }
    if (priority === eco.priority) return;

    this.ecoToggling = eco.id;
    this.api.updateEcosystemPriority(eco.id, priority).subscribe({
      next: (updated) => {
        const idx = this.ecosystems.findIndex((e) => e.id === eco.id);
        if (idx >= 0) this.ecosystems[idx] = updated;
        this.ecoToggling = null;
        this.snack.open(`${eco.name} priority updated to ${priority}`, 'OK', { duration: 2500 });
        this.cdr.markForCheck();
      },
      error: () => {
        this.ecoToggling = null;
        this.snack.open(`Failed to update ${eco.name} priority`, 'Dismiss', { duration: 4000 });
        this.cdr.markForCheck();
      },
    });
  }

  onToggle(collector: CollectorInfo, enabled: boolean): void {
    this.toggling = collector.id;
    this.api.toggleCollector(collector.id, enabled).subscribe({
      next: (updated) => {
        const idx = this.collectors.findIndex((c) => c.id === collector.id);
        if (idx >= 0) this.collectors[idx] = updated;
        if (this.data) {
          this.data.enabled_count = this.collectors.filter((c) => c.enabled).length;
        }
        this.toggling = null;
        this.snack.open(`${collector.name} ${enabled ? 'enabled' : 'disabled'}`, 'OK', { duration: 2500 });
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
        setTimeout(() =>
          document.getElementById('collector-output')?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
        );
      },
      error: () => {
        this.outputLoading = false;
        this.expandedId = null;
        this.outputData = null;
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
