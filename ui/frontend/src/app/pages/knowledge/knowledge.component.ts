import { Component, OnInit, OnDestroy, ChangeDetectorRef, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTabsModule } from '@angular/material/tabs';
import { MatBadgeModule } from '@angular/material/badge';
import { RouterLink } from '@angular/router';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap, of, catchError } from 'rxjs';

import { marked } from 'marked';
import DOMPurify from 'dompurify';
import {
  ApiService,
  KnowledgeFile,
  VersionedRun,
  VersionArtifact,
} from '../../services/api.service';
import { formatBytes as formatBytesUtil } from '../../shared/phase-utils';
import { PinnedDocs, PINNED_DOCS_KEY } from '../../shared/pinned-docs';
import { ArtifactCacheService } from '../../services/artifact-cache.service';

/** A group of files within a tab. */
interface FileGroup {
  id: string;
  label: string;
  icon: string;
  phase: string;
  description: string;
  files: KnowledgeFile[];
}

/** Tab definition for the category tabs. */
interface KnowledgeTab {
  id: string;
  label: string;
  icon: string;
  count: number;
  lastModified: string | null;
}

/** Source mode: local (current run) or a specific MLflow run. */
type SourceMode = 'local' | 'archived';

@Component({
  selector: 'app-knowledge',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatTableModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatTooltipModule,
    MatSnackBarModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatTabsModule,
    MatBadgeModule,
    RouterLink,
  ],
  template: `
    <div class="page-container">
      <div class="page-header">
        <mat-icon class="page-icon">psychology</mat-icon>
        <div>
          <h1 class="page-title">Knowledge Explorer</h1>
          <p class="page-subtitle">Pipeline artifacts with run versioning via MLflow</p>
        </div>
      </div>

      <!-- ═══ Timeline ═══ -->
      @if (versioningAvailable && archivedRuns.length > 1) {
        <div class="timeline-bar">
          <button class="timeline-toggle" (click)="showTimeline = !showTimeline; cdr.detectChanges()">
            <mat-icon>{{ showTimeline ? 'expand_less' : 'timeline' }}</mat-icon>
            <span>Timeline</span>
          </button>
          @if (showTimeline) {
            <div class="timeline-track">
              <div class="timeline-line"></div>
              @for (run of archivedRuns; track run.mlflow_run_id) {
                <div
                  class="timeline-dot"
                  [class]="'outcome-' + (run.outcome || 'unknown')"
                  [class.timeline-active]="selectedRunId === run.mlflow_run_id"
                  (click)="selectArchivedRunById(run.mlflow_run_id)"
                  [matTooltip]="timelineTooltip(run)"
                ></div>
              }
            </div>
          }
        </div>
      }

      <!-- ═══ Run Selector Bar ═══ -->
      @if (versioningAvailable) {
        <div class="run-selector-bar">
          <div class="run-selector-left">
            <mat-icon class="run-selector-icon">history</mat-icon>
            <span class="run-selector-label">Source:</span>
            <mat-select
              class="run-mat-select"
              [value]="selectedRunId || 'local'"
              (selectionChange)="onRunSelectChange($event.value)"
            >
              <mat-option value="local">
                <span class="run-option">
                  <span class="run-outcome-dot outcome-success"></span>
                  Current Run (Local)
                </span>
              </mat-option>
              @for (run of archivedRuns; track run.mlflow_run_id) {
                <mat-option [value]="run.mlflow_run_id">
                  <span class="run-option">
                    <span class="run-outcome-dot" [class]="'outcome-' + (run.outcome || 'unknown')"></span>
                    <span class="run-option-id">{{ run.pipeline_run_id || run.mlflow_run_id.substring(0, 8) }}</span>
                    <span class="run-option-date">{{ formatRunDate(run.started_at) }}</span>
                    @if (artifactCounts[run.mlflow_run_id] !== undefined) {
                      <span class="run-option-count">{{ artifactCounts[run.mlflow_run_id] }} files</span>
                    }
                  </span>
                </mat-option>
              }
            </mat-select>
          </div>
          <div class="run-selector-right">
            @if (sourceMode === 'archived' && selectedRunId) {
              <a
                [href]="api.getDownloadAllUrl(selectedRunId)"
                mat-stroked-button
                class="download-all-btn"
                matTooltip="Download all artifacts as ZIP"
              >
                <mat-icon>download</mat-icon> ZIP
              </a>
            }
            @if (pinnedDocs) {
              <div class="pinned-chip" matTooltip="Documents pinned from a previous run">
                <mat-icon>push_pin</mat-icon>
                <span>Pinned: {{ pinnedDocs.pipelineRunId || pinnedDocs.runId.substring(0, 8) }}</span>
                <button class="pinned-clear" (click)="unpinDocs()">
                  <mat-icon>close</mat-icon>
                </button>
              </div>
            }
          </div>
        </div>
      }

      <!-- ═══ Archived Run Info Banner ═══ -->
      @if (sourceMode === 'archived' && selectedRunId) {
        <div class="version-banner">
          <mat-icon>info</mat-icon>
          <span>Viewing archived artifacts from run
            <strong>{{ selectedRunLabel }}</strong>
          </span>
          <div class="version-banner-actions">
            @if (!pinnedDocs || pinnedDocs.runId !== selectedRunId) {
              <button mat-stroked-button class="pin-btn" (click)="pinDocs()">
                <mat-icon>push_pin</mat-icon> Pin these docs
              </button>
            }
            <button mat-stroked-button class="back-btn" (click)="backToLocal()">
              <mat-icon>arrow_back</mat-icon> Back to Current
            </button>
          </div>
        </div>
      }

      @if (loading) {
        <div class="loading-center">
          <mat-spinner diameter="36"></mat-spinner>
        </div>
      } @else if (totalFiles === 0 && sourceMode === 'local') {
        <!-- Empty State (local) -->
        <div class="empty-state">
          <mat-icon>psychology</mat-icon>
          <p>No knowledge base found. Run the pipeline to generate architecture documentation.</p>
          <button mat-flat-button color="primary" routerLink="/run">
            <mat-icon>rocket_launch</mat-icon> Run Pipeline
          </button>
        </div>
      } @else if (totalFiles === 0 && sourceMode === 'archived') {
        <!-- Empty State (archived run) -->
        <div class="empty-state">
          <mat-icon>inventory_2</mat-icon>
          <p>Keine Dokumente vorhanden. Dieser Run wurde vor der MLflow-Integration ausgefuehrt und hat keine archivierten Artefakte.</p>
          <button mat-stroked-button (click)="backToLocal()">
            <mat-icon>arrow_back</mat-icon> Back to Current
          </button>
        </div>
      } @else {
        <!-- ═══ Search Bar (local mode only) ═══ -->
        @if (sourceMode === 'local') {
          <div class="search-bar">
            <mat-icon class="search-icon">search</mat-icon>
            <input
              class="search-input"
              placeholder="Search knowledge files..."
              [value]="searchQuery"
              (input)="onSearch($event)"
            />
            @if (searchQuery) {
              <button class="search-clear" (click)="clearSearch()">
                <mat-icon>close</mat-icon>
              </button>
            }
          </div>

          <!-- Search Results -->
          @if (searchQuery && searchResults.length > 0) {
            <div class="search-results">
              <div class="search-results-header">
                <mat-icon>search</mat-icon>
                <span>{{ searchResults.length }} results for "{{ searchQuery }}"</span>
              </div>
              @for (result of searchResults; track $index) {
                <div class="search-result-row" (click)="openSearchResult(result)">
                  <div class="sr-file">
                    <mat-icon class="sr-icon">description</mat-icon>
                    <span class="sr-path">{{ result.file }}</span>
                    <span class="sr-line">:{{ result.line }}</span>
                  </div>
                  <div class="sr-content">{{ result.content }}</div>
                </div>
              }
            </div>
          }
          @if (searchQuery && searchResults.length === 0 && !searchLoading) {
            <div class="search-empty">
              <mat-icon>search_off</mat-icon>
              <span>No results found for "{{ searchQuery }}"</span>
            </div>
          }
        }

        <!-- ═══ Stats Bar ═══ -->
        <div class="stats-bar">
          <div class="stat-item">
            <mat-icon>inventory_2</mat-icon>
            <strong>{{ totalFiles }}</strong> files
          </div>
          <div class="stat-item">
            <mat-icon>storage</mat-icon>
            <strong>{{ formatBytes(totalSize) }}</strong>
          </div>
          @if (docCount > 0) {
            <div class="stat-item stat-docs">
              <mat-icon>menu_book</mat-icon>
              <strong>{{ docCount }}</strong> docs
            </div>
          }
          @if (dataCount > 0) {
            <div class="stat-item stat-data">
              <mat-icon>data_object</mat-icon>
              <strong>{{ dataCount }}</strong> data files
            </div>
          }
        </div>

        <!-- ═══ Category Tabs ═══ -->
        <div class="category-tabs">
          @for (tab of tabs; track tab.id) {
            <button
              class="tab-btn"
              [class.tab-active]="activeTab === tab.id"
              (click)="selectTab(tab.id)"
            >
              <mat-icon class="tab-icon">{{ tab.icon }}</mat-icon>
              <span class="tab-label">{{ tab.label }}</span>
              @if (tab.count > 0) {
                <span class="tab-count">{{ tab.count }}</span>
              }
              @if (tab.lastModified) {
                <span class="tab-modified">{{ timeAgo(tab.lastModified) }}</span>
              }
            </button>
          }
        </div>

        <!-- ═══ Tab Content ═══ -->
        <div class="tab-content">

          <!-- Documents Tab -->
          @if (activeTab === 'documents') {
            @if (documentGroups.length === 0) {
              <div class="tab-empty">
                <mat-icon>description</mat-icon>
                <span>No documents found. Run the <strong>Document</strong> phase to generate Arc42 and C4 documentation.</span>
              </div>
            } @else {
              <!-- Document Group Cards -->
              <div class="doc-cards">
                @for (g of documentGroups; track g.id) {
                  <div
                    class="doc-card"
                    [class.doc-card-active]="activeDocGroup === g.id"
                    (click)="selectDocGroup(g.id)"
                  >
                    <mat-icon class="doc-card-icon">{{ g.icon }}</mat-icon>
                    <div class="doc-card-info">
                      <span class="doc-card-label">{{ g.label }}</span>
                      <span class="doc-card-meta">{{ g.files.length }} chapters &middot; {{ formatBytes(groupSize(g)) }}</span>
                    </div>
                    <mat-icon class="doc-card-arrow">chevron_right</mat-icon>
                  </div>
                }
              </div>

              <!-- Document File List -->
              @if (activeDocGroup) {
                @for (g of documentGroups; track g.id) {
                  @if (activeDocGroup === g.id && g.files.length > 0) {
                    <div class="file-list">
                      @for (file of g.files; track file.path) {
                        <div
                          class="file-row"
                          [class.file-active]="selectedFile === file"
                    [class.file-focused]="isFileFocused(file)"
                          role="button"
                          tabindex="0"
                          (click)="viewFile(file)"
                          (keydown.enter)="viewFile(file)"
                          (keydown.space)="viewFile(file); $event.preventDefault()"
                        >
                          <mat-icon class="file-icon" [class]="'type-' + file.type">{{ fileIcon(file.type) }}</mat-icon>
                          <div class="file-info">
                            <span class="file-name">{{ cleanDocName(file.name) }}</span>
                            <span class="file-path">{{ file.path }}</span>
                          </div>
                          <span class="file-badge" [class]="'badge-' + file.type">{{ file.type }}</span>
                          <span class="file-size">{{ formatBytes(file.size_bytes) }}</span>
                          <mat-icon class="file-arrow">chevron_right</mat-icon>
                        </div>
                      }
                    </div>
                  }
                }
              }
            }
          }

          <!-- Analysis Tab -->
          @if (activeTab === 'analysis') {
            @if (analysisFiles.length === 0) {
              <div class="tab-empty">
                <mat-icon>analytics</mat-icon>
                <span>No analysis data found. Run the <strong>Analyze</strong> phase.</span>
              </div>
            } @else {
              <div class="file-list">
                @for (file of analysisFiles; track file.path) {
                  <div
                    class="file-row"
                    [class.file-active]="selectedFile === file"
                    [class.file-focused]="isFileFocused(file)"
                    role="button"
                    tabindex="0"
                    (click)="viewFile(file)"
                    (keydown.enter)="viewFile(file)"
                    (keydown.space)="viewFile(file); $event.preventDefault()"
                  >
                    <mat-icon class="file-icon" [class]="'type-' + file.type">{{ fileIcon(file.type) }}</mat-icon>
                    <div class="file-info">
                      <span class="file-name">{{ file.name }}</span>
                      <span class="file-path">{{ file.path }}</span>
                    </div>
                    <span class="file-badge" [class]="'badge-' + file.type">{{ file.type }}</span>
                    <span class="file-size">{{ formatBytes(file.size_bytes) }}</span>
                    <mat-icon class="file-arrow">chevron_right</mat-icon>
                  </div>
                }
              </div>
            }
          }

          <!-- Plans Tab -->
          @if (activeTab === 'plans') {
            @if (planFiles.length === 0) {
              <div class="tab-empty">
                <mat-icon>assignment</mat-icon>
                <span>No plans found. Run the <strong>Plan</strong> phase.</span>
              </div>
            } @else {
              <div class="file-list">
                @for (file of planFiles; track file.path) {
                  <div
                    class="file-row"
                    [class.file-active]="selectedFile === file"
                    [class.file-focused]="isFileFocused(file)"
                    role="button"
                    tabindex="0"
                    (click)="viewFile(file)"
                    (keydown.enter)="viewFile(file)"
                    (keydown.space)="viewFile(file); $event.preventDefault()"
                  >
                    <mat-icon class="file-icon" [class]="'type-' + file.type">{{ fileIcon(file.type) }}</mat-icon>
                    <div class="file-info">
                      <span class="file-name">{{ file.name }}</span>
                      <span class="file-path">{{ file.path }}</span>
                    </div>
                    <span class="file-badge" [class]="'badge-' + file.type">{{ file.type }}</span>
                    <span class="file-size">{{ formatBytes(file.size_bytes) }}</span>
                    <mat-icon class="file-arrow">chevron_right</mat-icon>
                  </div>
                }
              </div>
            }
          }

          <!-- Triage Tab -->
          @if (activeTab === 'triage') {
            @if (triageFiles.length === 0) {
              <div class="tab-empty">
                <mat-icon>search</mat-icon>
                <span>No triage results found. Run the <strong>Triage</strong> phase.</span>
              </div>
            } @else {
              <div class="file-list">
                @for (file of triageFiles; track file.path) {
                  <div
                    class="file-row"
                    [class.file-active]="selectedFile === file"
                    [class.file-focused]="isFileFocused(file)"
                    role="button"
                    tabindex="0"
                    (click)="viewFile(file)"
                    (keydown.enter)="viewFile(file)"
                    (keydown.space)="viewFile(file); $event.preventDefault()"
                  >
                    <mat-icon class="file-icon" [class]="'type-' + file.type">{{ fileIcon(file.type) }}</mat-icon>
                    <div class="file-info">
                      <span class="file-name">{{ file.name }}</span>
                      <span class="file-path">{{ file.path }}</span>
                    </div>
                    <span class="file-badge" [class]="'badge-' + file.type">{{ file.type }}</span>
                    <span class="file-size">{{ formatBytes(file.size_bytes) }}</span>
                    <mat-icon class="file-arrow">chevron_right</mat-icon>
                  </div>
                }
              </div>
            }
          }

          <!-- Extract Tab -->
          @if (activeTab === 'extract') {
            @if (extractFiles.length === 0) {
              <div class="tab-empty">
                <mat-icon>data_object</mat-icon>
                <span>No extract data found. Run the <strong>Extract</strong> phase.</span>
              </div>
            } @else {
              <div class="file-list">
                @for (file of extractFiles; track file.path) {
                  <div
                    class="file-row"
                    [class.file-active]="selectedFile === file"
                    [class.file-focused]="isFileFocused(file)"
                    role="button"
                    tabindex="0"
                    (click)="viewFile(file)"
                    (keydown.enter)="viewFile(file)"
                    (keydown.space)="viewFile(file); $event.preventDefault()"
                  >
                    <mat-icon class="file-icon" [class]="'type-' + file.type">{{ fileIcon(file.type) }}</mat-icon>
                    <div class="file-info">
                      <span class="file-name">{{ file.name }}</span>
                      <span class="file-path">{{ file.path }}</span>
                    </div>
                    <span class="file-badge" [class]="'badge-' + file.type">{{ file.type }}</span>
                    <span class="file-size">{{ formatBytes(file.size_bytes) }}</span>
                    <mat-icon class="file-arrow">chevron_right</mat-icon>
                  </div>
                }
              </div>
            }
          }

          <!-- Architecture Tab -->
          @if (activeTab === 'architecture') {
            @if (mermaidLoading) {
              <div class="loading-center" style="padding:40px">
                <mat-spinner diameter="32"></mat-spinner>
              </div>
            } @else if (mermaidError) {
              <div class="tab-empty">
                <mat-icon>error_outline</mat-icon>
                <span>{{ mermaidError }}</span>
              </div>
            } @else if (mermaidSvg) {
              <div class="mermaid-container" [innerHTML]="mermaidSvg"></div>
            } @else {
              <div class="tab-empty">
                <mat-icon>account_tree</mat-icon>
                <span>No architecture diagram available. Run the <strong>Extract</strong> phase first.</span>
              </div>
            }
          }
        </div>

        <!-- ═══ Document Viewer ═══ -->
        @if (selectedFile) {
          <div class="viewer-panel" id="viewer">
            <div class="viewer-header">
              <div class="viewer-title">
                <mat-icon [class]="'type-' + selectedFile.type">{{ fileIcon(selectedFile.type) }}</mat-icon>
                <span>{{ selectedFile.name }}</span>
                <span class="viewer-badge" [class]="'badge-' + selectedFile.type">{{ selectedFile.type }}</span>
              </div>
              <div class="viewer-actions">
                @if (viewMode !== 'rendered' && canRender(selectedFile)) {
                  <button mat-stroked-button (click)="viewMode = 'rendered'" class="mode-btn">
                    <mat-icon>visibility</mat-icon> Rendered
                  </button>
                }
                @if (viewMode !== 'source') {
                  <button mat-stroked-button (click)="viewMode = 'source'" class="mode-btn">
                    <mat-icon>code</mat-icon> Source
                  </button>
                }
                @if (sourceMode === 'archived' && archivedRuns.length > 1) {
                  <button mat-stroked-button (click)="openDiffView()" class="mode-btn" matTooltip="Compare with another run">
                    <mat-icon>compare</mat-icon> Diff
                  </button>
                }
                @if (cachedIndicator) {
                  <span class="cached-chip">cached</span>
                }
                <button
                  mat-icon-button
                  (click)="copyContent()"
                  matTooltip="Copy to clipboard"
                  aria-label="Copy to clipboard"
                >
                  <mat-icon>content_copy</mat-icon>
                </button>
                <button
                  mat-icon-button
                  (click)="downloadContent()"
                  matTooltip="Download file"
                  aria-label="Download file"
                >
                  <mat-icon>download</mat-icon>
                </button>
                <button mat-icon-button (click)="closeViewer()" matTooltip="Close (Esc)" aria-label="Close viewer">
                  <mat-icon>close</mat-icon>
                </button>
              </div>
            </div>
            <div class="viewer-body">
              @if (fileLoading) {
                <div class="loading-center">
                  <mat-spinner diameter="32"></mat-spinner>
                </div>
              } @else if (viewerError) {
                <div class="viewer-error">
                  <mat-icon>error_outline</mat-icon>
                  <span>{{ viewerError }}</span>
                </div>
              } @else if (viewMode === 'rendered' && renderedHtml) {
                <div class="rendered-content markdown-body" [innerHTML]="renderedHtml"></div>
              } @else {
                <pre class="source-content code-viewer">{{ selectedContent }}</pre>
              }
            </div>
          </div>
        }

        <!-- ═══ Diff Viewer ═══ -->
        @if (diffMode && selectedFile) {
          <div class="viewer-panel" style="margin-top:12px">
            <div class="viewer-header">
              <div class="viewer-title">
                <mat-icon>compare</mat-icon>
                <span>Diff: {{ selectedFile.name }}</span>
                <mat-select
                  class="diff-run-select"
                  [value]="diffCompareRunId"
                  (selectionChange)="onDiffRunChange($event.value)"
                  placeholder="Compare with..."
                >
                  @for (run of archivedRuns; track run.mlflow_run_id) {
                    @if (run.mlflow_run_id !== selectedRunId) {
                      <mat-option [value]="run.mlflow_run_id">
                        <span class="run-outcome-dot" [class]="'outcome-' + (run.outcome || 'unknown')"></span>
                        {{ run.pipeline_run_id || run.mlflow_run_id.substring(0, 8) }}
                      </mat-option>
                    }
                  }
                </mat-select>
              </div>
              <button mat-icon-button (click)="closeDiff()" matTooltip="Close diff">
                <mat-icon>close</mat-icon>
              </button>
            </div>
            <div class="viewer-body">
              @if (diffLoading) {
                <div class="loading-center" style="padding:24px">
                  <mat-spinner diameter="28"></mat-spinner>
                </div>
              } @else if (diffLines.length > 0) {
                <pre class="diff-content">@for (line of diffLines; track $index) {<span [class]="'diff-' + line.type">{{ line.text }}
</span>}</pre>
              } @else if (diffCompareRunId) {
                <div class="tab-empty">
                  <mat-icon>check_circle</mat-icon>
                  <span>Keine Unterschiede gefunden</span>
                </div>
              }
            </div>
          </div>
        }
      }
    </div>
  `,
  styles: [
    `
      /* ── Timeline ────────────────────────────────────── */
      .timeline-bar {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;
        padding: 8px 16px;
        background: #fff;
        border: 1px solid var(--cg-gray-100);
        border-radius: 10px;
      }
      .timeline-toggle {
        display: flex;
        align-items: center;
        gap: 4px;
        border: none;
        background: none;
        cursor: pointer;
        font-size: 12px;
        font-weight: 500;
        color: var(--cg-gray-500);
        padding: 4px 8px;
        border-radius: 6px;
        white-space: nowrap;
      }
      .timeline-toggle:hover { background: var(--cg-gray-50); }
      .timeline-toggle .mat-icon { font-size: 18px; width: 18px; height: 18px; }
      .timeline-track {
        display: flex;
        align-items: center;
        gap: 8px;
        flex: 1;
        position: relative;
        padding: 4px 0;
        overflow-x: auto;
      }
      .timeline-line {
        position: absolute;
        top: 50%;
        left: 0;
        right: 0;
        height: 2px;
        background: var(--cg-gray-200);
        z-index: 0;
      }
      .timeline-dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        cursor: pointer;
        z-index: 1;
        flex-shrink: 0;
        transition: transform 0.15s;
        border: 2px solid #fff;
        box-shadow: 0 0 0 1px var(--cg-gray-200);
      }
      .timeline-dot:hover { transform: scale(1.4); }
      .timeline-dot.timeline-active {
        transform: scale(1.5);
        box-shadow: 0 0 0 2px var(--cg-blue);
      }
      .outcome-success { background: var(--cg-success); }
      .outcome-partial { background: var(--cg-warn); }
      .outcome-failed { background: var(--cg-error); }
      .outcome-unknown { background: var(--cg-gray-400); }

      /* ── Run Selector ─────────────────────────────────── */
      .run-selector-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 16px;
        padding: 10px 16px;
        background: #fff;
        border: 1px solid var(--cg-gray-200);
        border-radius: 10px;
        flex-wrap: wrap;
      }
      .run-selector-left {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .run-selector-right {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .run-selector-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
        color: var(--cg-blue);
      }
      .run-selector-label {
        font-size: 13px;
        font-weight: 500;
        color: var(--cg-gray-500);
      }
      .run-mat-select {
        min-width: 320px;
        font-size: 13px;
      }
      .run-option {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
      }
      .run-outcome-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
      }
      .run-option-id {
        font-weight: 500;
        font-family: monospace;
      }
      .run-option-date {
        color: var(--cg-gray-400);
        font-size: 12px;
      }
      .run-option-count {
        color: var(--cg-vibrant);
        font-size: 11px;
        font-weight: 600;
        background: rgba(18, 171, 219, 0.1);
        padding: 0 6px;
        border-radius: 8px;
      }
      .download-all-btn {
        font-size: 12px !important;
        line-height: 28px !important;
        padding: 0 10px !important;
      }
      .download-all-btn .mat-icon {
        font-size: 16px; width: 16px; height: 16px; margin-right: 4px;
      }

      /* ── Pinned Docs Chip ─────────────────────────────── */
      .pinned-chip {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        background: rgba(0, 112, 173, 0.08);
        border: 1px solid rgba(0, 112, 173, 0.2);
        border-radius: 20px;
        font-size: 12px;
        color: var(--cg-blue);
        font-weight: 500;
      }
      .pinned-chip .mat-icon {
        font-size: 14px;
        width: 14px;
        height: 14px;
      }
      .pinned-clear {
        border: none;
        background: none;
        cursor: pointer;
        padding: 0;
        display: flex;
        color: var(--cg-blue);
      }
      .pinned-clear:hover {
        color: var(--cg-error);
      }
      .pinned-clear .mat-icon {
        font-size: 14px;
        width: 14px;
        height: 14px;
      }

      /* ── Version Banner ───────────────────────────────── */
      .version-banner {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 16px;
        margin-bottom: 16px;
        background: rgba(18, 171, 219, 0.08);
        border: 1px solid rgba(18, 171, 219, 0.2);
        border-radius: 10px;
        font-size: 13px;
        color: var(--cg-vibrant);
        flex-wrap: wrap;
      }
      .version-banner .mat-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
      }
      .version-banner-actions {
        margin-left: auto;
        display: flex;
        gap: 8px;
      }
      .pin-btn, .back-btn {
        font-size: 12px !important;
        line-height: 28px !important;
        padding: 0 10px !important;
      }
      .pin-btn .mat-icon, .back-btn .mat-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
        margin-right: 4px;
      }

      /* ── Search ──────────────────────────────────────── */
      .search-bar {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 16px;
        background: #fff;
        border: 1px solid var(--cg-gray-200);
        border-radius: 10px;
        padding: 8px 14px;
        transition: border-color 0.15s;
      }
      .search-bar:focus-within {
        border-color: var(--cg-blue);
      }
      .search-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
        color: var(--cg-gray-400);
      }
      .search-input {
        flex: 1;
        border: none;
        outline: none;
        font-size: 14px;
        background: transparent;
        color: var(--cg-gray-900);
      }
      .search-input::placeholder {
        color: var(--cg-gray-400);
      }
      .search-clear {
        border: none;
        background: none;
        cursor: pointer;
        color: var(--cg-gray-400);
        padding: 0;
        display: flex;
      }
      .search-clear:hover {
        color: var(--cg-gray-600);
      }
      .search-clear .mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
      }
      .search-results {
        background: #fff;
        border-radius: 10px;
        border: 1px solid var(--cg-gray-100);
        margin-bottom: 16px;
        overflow: hidden;
      }
      .search-results-header {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 10px 14px;
        font-size: 13px;
        font-weight: 500;
        color: var(--cg-gray-500);
        border-bottom: 1px solid var(--cg-gray-100);
      }
      .search-results-header .mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
        color: var(--cg-blue);
      }
      .search-result-row {
        padding: 8px 14px;
        cursor: pointer;
        transition: background 0.1s;
        border-bottom: 1px solid var(--cg-gray-50);
      }
      .search-result-row:last-child {
        border-bottom: none;
      }
      .search-result-row:hover {
        background: var(--cg-gray-50);
      }
      .sr-file {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 2px;
      }
      .sr-icon {
        font-size: 14px;
        width: 14px;
        height: 14px;
        color: var(--cg-blue);
      }
      .sr-path {
        font-size: 12px;
        font-family: monospace;
        color: var(--cg-gray-600);
      }
      .sr-line {
        font-size: 11px;
        color: var(--cg-gray-400);
      }
      .sr-content {
        font-size: 12px;
        color: var(--cg-gray-500);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        padding-left: 20px;
      }
      .search-empty {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 16px;
        margin-bottom: 16px;
        color: var(--cg-gray-400);
        font-size: 13px;
      }
      .search-empty .mat-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
      }

      /* ── Stats ────────────────────────────────────────── */
      .stat-docs .mat-icon {
        color: var(--cg-blue);
      }
      .stat-data .mat-icon {
        color: var(--cg-vibrant);
      }

      /* ── Category Tabs ────────────────────────────────── */
      .category-tabs {
        display: flex;
        gap: 4px;
        margin-bottom: 16px;
        padding: 4px;
        background: var(--cg-gray-50);
        border-radius: 12px;
        overflow-x: auto;
      }
      .tab-btn {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 8px 16px;
        border: none;
        border-radius: 8px;
        background: transparent;
        font-size: 13px;
        font-weight: 500;
        color: var(--cg-gray-500);
        cursor: pointer;
        transition: all 0.15s;
        white-space: nowrap;
      }
      .tab-btn:hover {
        background: #fff;
        color: var(--cg-gray-700);
      }
      .tab-btn.tab-active {
        background: #fff;
        color: var(--cg-blue);
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
      }
      .tab-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
      }
      .tab-count {
        background: var(--cg-gray-100);
        padding: 0px 7px;
        border-radius: 10px;
        font-size: 11px;
        font-weight: 600;
      }
      .tab-active .tab-count {
        background: rgba(0, 112, 173, 0.12);
        color: var(--cg-blue);
      }
      .tab-modified {
        font-size: 10px;
        color: var(--cg-gray-400);
        white-space: nowrap;
      }

      /* ── Tab Content ──────────────────────────────────── */
      .tab-content {
        background: #fff;
        border-radius: 14px;
        border: 1px solid var(--cg-gray-100);
        overflow: hidden;
        min-height: 200px;
      }
      .tab-empty {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 40px 24px;
        color: var(--cg-gray-400);
        font-size: 14px;
        justify-content: center;
      }
      .tab-empty .mat-icon {
        font-size: 28px;
        width: 28px;
        height: 28px;
        color: var(--cg-gray-300);
      }

      /* ── Document Cards ───────────────────────────────── */
      .doc-cards {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
        gap: 12px;
        padding: 16px;
      }
      .doc-card {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px;
        border: 1px solid var(--cg-gray-100);
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.15s;
      }
      .doc-card:hover {
        border-color: var(--cg-blue);
        background: rgba(0, 112, 173, 0.03);
      }
      .doc-card-active {
        border-color: var(--cg-blue) !important;
        background: rgba(0, 112, 173, 0.06) !important;
      }
      .doc-card-icon {
        font-size: 28px;
        width: 28px;
        height: 28px;
        color: var(--cg-blue);
      }
      .doc-card-info {
        flex: 1;
        min-width: 0;
      }
      .doc-card-label {
        display: block;
        font-size: 14px;
        font-weight: 500;
        color: var(--cg-gray-900);
      }
      .doc-card-meta {
        display: block;
        font-size: 12px;
        color: var(--cg-gray-400);
        margin-top: 2px;
      }
      .doc-card-arrow {
        font-size: 20px;
        width: 20px;
        height: 20px;
        color: var(--cg-gray-300);
      }

      /* ── File List ────────────────────────────────────── */
      .file-list {
        padding: 0 12px 12px;
      }
      .file-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 12px;
        border-radius: 8px;
        cursor: pointer;
        transition: background 0.1s;
      }
      .file-row:hover {
        background: var(--cg-gray-50);
      }
      .file-active {
        background: rgba(0, 112, 173, 0.06) !important;
      }
      .file-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
        flex-shrink: 0;
      }
      .file-info {
        flex: 1;
        min-width: 0;
      }
      .file-name {
        display: block;
        font-size: 13px;
        font-weight: 500;
        color: var(--cg-gray-900);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .file-path {
        display: block;
        font-size: 11px;
        font-family: monospace;
        color: var(--cg-gray-400);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .file-badge {
        display: inline-block;
        padding: 1px 8px;
        border-radius: 8px;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.3px;
        flex-shrink: 0;
      }
      .file-size {
        font-size: 11px;
        color: var(--cg-gray-400);
        white-space: nowrap;
        flex-shrink: 0;
      }
      .file-arrow {
        font-size: 18px;
        width: 18px;
        height: 18px;
        color: var(--cg-gray-300);
        flex-shrink: 0;
      }

      /* ── Type Colors ──────────────────────────────────── */
      .type-json { color: var(--cg-vibrant); }
      .type-md { color: var(--cg-blue); }
      .type-drawio { color: var(--cg-success); }
      .type-html { color: #e44d26; }
      .type-adoc { color: #a0522d; }
      .type-confluence { color: #0052cc; }
      .type-other { color: var(--cg-gray-500); }

      .badge-json { background: rgba(18, 171, 219, 0.1); color: var(--cg-vibrant); }
      .badge-md { background: rgba(0, 112, 173, 0.1); color: var(--cg-blue); }
      .badge-drawio { background: rgba(40, 167, 69, 0.1); color: var(--cg-success); }
      .badge-html { background: rgba(228, 77, 38, 0.1); color: #e44d26; }
      .badge-adoc { background: rgba(160, 82, 45, 0.1); color: #a0522d; }
      .badge-confluence { background: rgba(0, 82, 204, 0.1); color: #0052cc; }
      .badge-other { background: var(--cg-gray-100); color: var(--cg-gray-500); }

      /* ── Viewer Panel ─────────────────────────────────── */
      .viewer-panel {
        margin-top: 20px;
        background: #fff;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      }
      .viewer-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 20px;
        background: var(--cg-gray-50);
        border-bottom: 1px solid var(--cg-gray-100);
      }
      .viewer-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
        font-weight: 500;
      }
      .viewer-badge {
        padding: 1px 8px;
        border-radius: 8px;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
      }
      .viewer-actions {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .mode-btn {
        font-size: 12px !important;
        line-height: 28px !important;
        padding: 0 10px !important;
      }
      .mode-btn .mat-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
        margin-right: 4px;
      }
      .viewer-body {
        max-height: 70vh;
        overflow: auto;
      }
      .viewer-error {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 24px;
        color: var(--cg-error);
        font-size: 14px;
      }
      .viewer-error .mat-icon {
        font-size: 24px;
        width: 24px;
        height: 24px;
      }
      .source-content {
        margin: 0;
        background: var(--cg-dark);
        color: #eeffff;
        padding: 20px;
        white-space: pre-wrap;
        word-break: break-all;
        font-size: 12px;
        line-height: 1.7;
        min-height: 200px;
      }
      .rendered-content {
        padding: 24px 32px;
        font-size: 14px;
        line-height: 1.7;
        color: var(--cg-gray-900);
      }

      /* ── Mermaid Diagram ──────────────────────────────── */
      .mermaid-container {
        padding: 24px;
        text-align: center;
        overflow-x: auto;
      }
      .mermaid-container svg {
        max-width: 100%;
        height: auto;
      }

      /* ── Diff View ───────────────────────────────────── */
      .diff-run-select {
        min-width: 180px;
        font-size: 12px;
        margin-left: 12px;
      }
      .diff-content {
        margin: 0;
        background: var(--cg-dark);
        color: #eeffff;
        padding: 16px 20px;
        font-size: 12px;
        line-height: 1.6;
        white-space: pre-wrap;
        word-break: break-all;
        min-height: 100px;
      }
      .diff-same { color: #676e95; }
      .diff-add { color: #c3e88d; background: rgba(195, 232, 141, 0.08); }
      .diff-remove { color: #ff5370; background: rgba(255, 83, 112, 0.08); }

      /* ── Cache Indicator ──────────────────────────────── */
      .cached-chip {
        font-size: 10px;
        font-weight: 600;
        color: var(--cg-success);
        background: rgba(40, 167, 69, 0.1);
        padding: 2px 8px;
        border-radius: 8px;
        text-transform: uppercase;
      }

      /* ── Keyboard Focus ───────────────────────────────── */
      .file-focused {
        outline: 2px solid var(--cg-blue);
        outline-offset: -2px;
        background: rgba(0, 112, 173, 0.04) !important;
      }
    `,
  ],
})
export class KnowledgeComponent implements OnInit, OnDestroy {
  private refreshTimer: ReturnType<typeof setInterval> | null = null;
  loading = true;
  totalFiles = 0;
  totalSize = 0;
  docCount = 0;
  dataCount = 0;

  // ── Run Versioning ──────────────────────────────────
  versioningAvailable = false;
  archivedRuns: VersionedRun[] = [];
  sourceMode: SourceMode = 'local';
  selectedRunId: string | null = null;
  selectedRunLabel = '';
  pinnedDocs: PinnedDocs | null = null;
  private archivedArtifacts: VersionArtifact[] = [];
  artifactCounts: Record<string, number> = {};
  showTimeline = false;

  // ── Architecture Diagram ───────────────────────────
  mermaidDiagram: string | null = null;
  mermaidSvg: SafeHtml | null = null;
  mermaidLoading = false;
  mermaidError: string | null = null;

  // ── Keyboard Navigation ────────────────────────────
  focusedFileIndex = -1;

  // ── Diff View ──────────────────────────────────────
  diffMode = false;
  diffCompareRunId: string | null = null;
  diffLines: { type: 'same' | 'add' | 'remove'; text: string }[] = [];
  diffLoading = false;

  // ── Offline Cache ──────────────────────────────────
  cachedIndicator = false;

  // ── Tabs ────────────────────────────────────────────
  activeTab = 'documents';
  tabs: KnowledgeTab[] = [];

  // ── Documents tab ───────────────────────────────────
  documentGroups: FileGroup[] = [];
  activeDocGroup = '';

  // ── Other tab data ──────────────────────────────────
  analysisFiles: KnowledgeFile[] = [];
  planFiles: KnowledgeFile[] = [];
  triageFiles: KnowledgeFile[] = [];
  extractFiles: KnowledgeFile[] = [];

  // ── Viewer ──────────────────────────────────────────
  selectedFile: KnowledgeFile | null = null;
  selectedContent: string | null = null;
  renderedHtml: SafeHtml | null = null;
  viewMode: 'source' | 'rendered' = 'rendered';
  fileLoading = false;
  viewerError: string | null = null;

  // ── Search ──────────────────────────────────────────
  searchQuery = '';
  searchResults: { file: string; line: number; content: string }[] = [];
  searchLoading = false;
  private searchSubject = new Subject<string>();

  constructor(
    public api: ApiService,
    public cdr: ChangeDetectorRef,
    private sanitizer: DomSanitizer,
    private snackBar: MatSnackBar,
    private cache: ArtifactCacheService,
  ) {}

  @HostListener('document:keydown', ['$event'])
  onKeyDown(event: KeyboardEvent): void {
    const tag = (event.target as HTMLElement)?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

    switch (event.key) {
      case 'Escape':
        if (this.selectedFile) this.closeViewer();
        break;
      case 'ArrowLeft':
        event.preventDefault();
        this.navigateTab(-1);
        break;
      case 'ArrowRight':
        event.preventDefault();
        this.navigateTab(1);
        break;
      case 'ArrowDown':
        event.preventDefault();
        this.navigateFile(1);
        break;
      case 'ArrowUp':
        event.preventDefault();
        this.navigateFile(-1);
        break;
      case 'Enter':
        if (this.focusedFileIndex >= 0) {
          event.preventDefault();
          this.openFocusedFile();
        }
        break;
    }
  }

  ngOnInit(): void {
    // Load pinned docs from localStorage
    this.loadPinnedDocs();

    // Load versioning status and local knowledge in parallel
    this.api.getVersionStatus().subscribe({
      next: (status) => {
        this.versioningAvailable = status.available;
        if (status.available) {
          this.loadArchivedRuns();
        }
        this.cdr.detectChanges();
      },
      error: () => {
        this.versioningAvailable = false;
      },
    });

    this.loadKnowledge();
    this.refreshTimer = setInterval(() => {
      if (this.sourceMode === 'local') {
        this.loadKnowledge();
      }
    }, 10000);

    // Search pipeline
    this.searchSubject
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        switchMap((q) => {
          if (q.length < 2) {
            return of([]);
          }
          this.searchLoading = true;
          return this.api.searchKnowledge(q).pipe(catchError(() => of([])));
        }),
      )
      .subscribe((results) => {
        this.searchResults = results;
        this.searchLoading = false;
        this.cdr.detectChanges();
      });
  }

  ngOnDestroy(): void {
    if (this.refreshTimer) clearInterval(this.refreshTimer);
    this.searchSubject.complete();
  }

  // ─── Data Loading ──────────────────────────────────────────────

  private loadKnowledge(): void {
    this.api.getKnowledgeFiles().subscribe({
      next: (s) => {
        this.categorizeLocal(s.files);
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  private loadArchivedRuns(): void {
    this.api.getVersionedRuns(10).subscribe({
      next: (data) => {
        this.archivedRuns = data.runs;
        this.cdr.detectChanges();
        // Lazy-load artifact counts in background
        if (data.runs.length > 0) {
          const ids = data.runs.map((r) => r.mlflow_run_id);
          this.api.getArtifactCounts(ids).subscribe({
            next: (counts) => {
              this.artifactCounts = counts;
              this.cdr.detectChanges();
            },
            error: () => {},
          });
        }
      },
      error: () => {},
    });
  }

  private clearAllFiles(): void {
    this.documentGroups = [];
    this.activeDocGroup = '';
    this.analysisFiles = [];
    this.planFiles = [];
    this.triageFiles = [];
    this.extractFiles = [];
    this.totalFiles = 0;
    this.totalSize = 0;
    this.docCount = 0;
    this.dataCount = 0;
    this.tabs = [];
  }

  private loadArchivedFiles(runId: string): void {
    this.loading = true;
    this.clearAllFiles();
    this.cdr.detectChanges();

    this.api.getVersionFiles(runId).subscribe({
      next: (data) => {
        this.archivedArtifacts = data.files;
        if (data.files.length === 0) {
          this.updateTabs();
        } else {
          this.categorizeArchived(data.files);
        }
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.loading = false;
        this.updateTabs();
        this.snackBar.open('Keine Dokumente vorhanden fuer diesen Run', 'OK', { duration: 3000 });
        this.cdr.detectChanges();
      },
    });
  }

  // ─── Categorization ────────────────────────────────────────────

  private categorizeLocal(files: KnowledgeFile[]): void {
    // Documents
    const arc42 = this.sortArc42(
      files.filter(
        (f) => this.inDir(f, 'document/arc42') || this.inDir(f, 'phase3_synthesis/arc42') || this.inDir(f, 'arc42'),
      ),
    );
    const c4 = this.sortC4(
      files.filter(
        (f) =>
          this.inDir(f, 'document/c4') ||
          this.inDir(f, 'phase3_synthesis/c4') ||
          (this.inDir(f, 'c4') && !this.inDir(f, 'arc42')),
      ),
    );
    const quality = files.filter((f) => this.inDir(f, 'document/quality') || this.inDir(f, 'phase3_synthesis/quality'));
    const synthOther = files.filter(
      (f) =>
        (this.inDir(f, 'document') || this.inDir(f, 'phase3_synthesis')) &&
        !arc42.includes(f) &&
        !c4.includes(f) &&
        !quality.includes(f),
    );

    this.documentGroups = [
      {
        id: 'arc42', label: 'Arc42 Documentation', icon: 'menu_book',
        phase: 'Document', description: 'Arc42 architecture template chapters', files: arc42,
      },
      {
        id: 'c4', label: 'C4 Model', icon: 'account_tree',
        phase: 'Document', description: 'C4 diagrams (context, container, component, deployment)', files: c4,
      },
      ...(quality.length > 0 ? [{
        id: 'quality', label: 'Quality', icon: 'verified',
        phase: 'Document', description: 'Quality assessment reports', files: quality,
      }] : []),
      ...(synthOther.length > 0 ? [{
        id: 'synth-other', label: 'Other Synthesis', icon: 'description',
        phase: 'Document', description: 'Additional synthesis artifacts', files: synthOther,
      }] : []),
    ].filter((g) => g.files.length > 0);

    if (this.documentGroups.length > 0 && !this.documentGroups.find((g) => g.id === this.activeDocGroup)) {
      this.activeDocGroup = this.documentGroups[0].id;
    }

    // Analysis
    this.analysisFiles = files.filter((f) => this.inDir(f, 'analyze') || this.inDir(f, 'phase2_analysis'));

    // Plans
    this.planFiles = files.filter((f) => this.inDir(f, 'plan') || this.inDir(f, 'phase4_planning'));

    // Triage
    this.triageFiles = files.filter((f) => this.inDir(f, 'triage'));

    // Extract
    this.extractFiles = files.filter((f) => this.inDir(f, 'extract') || this.inDir(f, 'phase1_facts'));

    // Stats
    const allDocs = [...arc42, ...c4, ...quality, ...synthOther];
    this.totalFiles = files.length;
    this.totalSize = files.reduce((sum, f) => sum + f.size_bytes, 0);
    this.docCount = allDocs.length;
    this.dataCount = this.analysisFiles.length + this.planFiles.length + this.triageFiles.length + this.extractFiles.length;

    this.updateTabs();
  }

  private categorizeArchived(artifacts: VersionArtifact[]): void {
    // Map MLflow artifact paths to KnowledgeFile-like objects
    const toKF = (a: VersionArtifact): KnowledgeFile => {
      const name = a.path.split('/').pop() || a.path;
      const ext = name.includes('.') ? name.substring(name.lastIndexOf('.')) : '';
      const typeMap: Record<string, string> = {
        '.json': 'json', '.md': 'md', '.drawio': 'drawio',
        '.html': 'html', '.adoc': 'adoc', '.yaml': 'yaml', '.yml': 'yaml',
      };
      return {
        path: a.path,
        name,
        size_bytes: a.file_size,
        modified: '',
        type: typeMap[ext.toLowerCase()] || 'other',
      };
    };

    const files = artifacts.map(toKF);

    // Documents (MLflow path: documents/arc42/*, documents/c4/*)
    const arc42 = this.sortArc42(files.filter((f) => this.inDir(f, 'documents/arc42')));
    const c4 = this.sortC4(files.filter((f) => this.inDir(f, 'documents/c4')));
    const docOther = files.filter(
      (f) => this.inDir(f, 'documents') && !arc42.includes(f) && !c4.includes(f),
    );

    this.documentGroups = [
      { id: 'arc42', label: 'Arc42 Documentation', icon: 'menu_book',
        phase: 'Document', description: 'Arc42 architecture template chapters', files: arc42 },
      { id: 'c4', label: 'C4 Model', icon: 'account_tree',
        phase: 'Document', description: 'C4 diagrams', files: c4 },
      ...(docOther.length > 0 ? [{
        id: 'doc-other', label: 'Other Documents', icon: 'description',
        phase: 'Document', description: 'Additional document artifacts', files: docOther,
      }] : []),
    ].filter((g) => g.files.length > 0);

    if (this.documentGroups.length > 0) {
      this.activeDocGroup = this.documentGroups[0].id;
    }

    // Analysis (MLflow path: analysis/*)
    this.analysisFiles = files.filter((f) => this.inDir(f, 'analysis'));

    // Plans (MLflow path: plans/*)
    this.planFiles = files.filter((f) => this.inDir(f, 'plans'));

    // Triage (MLflow path: triage/*)
    this.triageFiles = files.filter((f) => this.inDir(f, 'triage'));

    // Extract (remaining artifacts not in the above categories)
    const classified = new Set([
      ...arc42, ...c4, ...docOther,
      ...this.analysisFiles, ...this.planFiles, ...this.triageFiles,
    ]);
    this.extractFiles = files.filter((f) => !classified.has(f));

    // Stats
    this.totalFiles = files.length;
    this.totalSize = files.reduce((sum, f) => sum + f.size_bytes, 0);
    this.docCount = arc42.length + c4.length + docOther.length;
    this.dataCount = this.analysisFiles.length + this.planFiles.length + this.triageFiles.length + this.extractFiles.length;

    this.updateTabs();
  }

  private updateTabs(): void {
    const allDocs = this.documentGroups.flatMap((g) => g.files);
    this.tabs = [
      { id: 'documents', label: 'Documents', icon: 'description', count: this.docCount, lastModified: this.newestModified(allDocs) },
      { id: 'analysis', label: 'Analysis', icon: 'analytics', count: this.analysisFiles.length, lastModified: this.newestModified(this.analysisFiles) },
      { id: 'plans', label: 'Plans', icon: 'assignment', count: this.planFiles.length, lastModified: this.newestModified(this.planFiles) },
      { id: 'triage', label: 'Triage', icon: 'search', count: this.triageFiles.length, lastModified: this.newestModified(this.triageFiles) },
      { id: 'extract', label: 'Extract', icon: 'data_object', count: this.extractFiles.length, lastModified: this.newestModified(this.extractFiles) },
      { id: 'architecture', label: 'Architecture', icon: 'account_tree', count: 0, lastModified: null },
    ];
  }

  private newestModified(files: KnowledgeFile[]): string | null {
    const dates = files.map((f) => f.modified).filter(Boolean);
    if (dates.length === 0) return null;
    return dates.sort().reverse()[0];
  }

  // ─── Run Selector ──────────────────────────────────────────────

  onRunSelectChange(value: string): void {
    if (value === 'local') {
      this.backToLocal();
    } else {
      this.selectArchivedRunById(value);
    }
  }

  selectArchivedRunById(runId: string): void {
    this.sourceMode = 'archived';
    this.selectedRunId = runId;
    this.closeViewer();
    this.clearSearch();

    const run = this.archivedRuns.find((r) => r.mlflow_run_id === runId);
    this.selectedRunLabel = run
      ? `${run.pipeline_run_id || runId.substring(0, 8)} — ${this.formatRunDate(run.started_at)}`
      : runId.substring(0, 8);

    this.loadArchivedFiles(runId);
  }

  backToLocal(): void {
    this.sourceMode = 'local';
    this.selectedRunId = null;
    this.selectedRunLabel = '';
    this.archivedArtifacts = [];
    this.closeViewer();
    this.loadKnowledge();
  }

  // ─── Pin Documents ─────────────────────────────────────────────

  pinDocs(): void {
    if (!this.selectedRunId) return;
    const run = this.archivedRuns.find((r) => r.mlflow_run_id === this.selectedRunId);
    this.pinnedDocs = {
      runId: this.selectedRunId,
      pipelineRunId: run?.pipeline_run_id || null,
      startedAt: run?.started_at || null,
      pinnedAt: new Date().toISOString(),
    };
    localStorage.setItem(PINNED_DOCS_KEY, JSON.stringify(this.pinnedDocs));
    this.snackBar.open('Documents pinned. Document phase can be skipped in next run.', 'OK', { duration: 4000 });
    this.cdr.detectChanges();
  }

  unpinDocs(): void {
    this.pinnedDocs = null;
    localStorage.removeItem(PINNED_DOCS_KEY);
    this.cdr.detectChanges();
  }

  private loadPinnedDocs(): void {
    try {
      const raw = localStorage.getItem(PINNED_DOCS_KEY);
      if (raw) {
        this.pinnedDocs = JSON.parse(raw);
      }
    } catch {
      this.pinnedDocs = null;
    }
  }

  // ─── Search ────────────────────────────────────────────────────

  onSearch(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.searchQuery = value;
    this.searchSubject.next(value);
  }

  clearSearch(): void {
    this.searchQuery = '';
    this.searchResults = [];
    this.searchSubject.next('');
  }

  openSearchResult(result: { file: string; line: number; content: string }): void {
    const path = result.file.replace(/\\/g, '/');
    const fakeFile: KnowledgeFile = {
      path,
      name: path.split('/').pop() || path,
      size_bytes: 0,
      modified: '',
      type: path.endsWith('.json') ? 'json' : path.endsWith('.md') ? 'md' : 'other',
    };
    this.viewFile(fakeFile);
  }

  // ─── Tab Navigation ────────────────────────────────────────────

  selectTab(tabId: string): void {
    this.activeTab = tabId;
    this.focusedFileIndex = -1;
    this.closeViewer();
    if (tabId === 'architecture' && !this.mermaidDiagram && !this.mermaidLoading) {
      this.loadMermaidDiagram();
    }
    this.cdr.detectChanges();
  }

  selectDocGroup(id: string): void {
    this.activeDocGroup = this.activeDocGroup === id ? '' : id;
    this.closeViewer();
    this.cdr.detectChanges();
  }

  // ─── File Viewer ───────────────────────────────────────────────

  viewFile(file: KnowledgeFile): void {
    this.selectedFile = file;
    this.fileLoading = true;
    this.selectedContent = null;
    this.renderedHtml = null;
    this.viewerError = null;
    this.cachedIndicator = false;
    this.diffMode = false;
    this.viewMode = this.canRender(file) ? 'rendered' : 'source';
    this.cdr.detectChanges();

    // Try cache first for archived runs
    if (this.sourceMode === 'archived' && this.selectedRunId) {
      this.cache.get(this.selectedRunId, file.path).then((cached) => {
        if (cached) {
          this.cachedIndicator = true;
          this.onFileContentLoaded(file, cached);
          return;
        }
        this.fetchFileContent(file);
      });
    } else {
      this.fetchFileContent(file);
    }
  }

  private fetchFileContent(file: KnowledgeFile): void {
    const content$ =
      this.sourceMode === 'archived' && this.selectedRunId
        ? this.api.getVersionFile(this.selectedRunId, file.path)
        : this.api.getKnowledgeFile(file.path);

    content$.subscribe({
      next: (content) => {
        const text = typeof content === 'string' ? content : JSON.stringify(content, null, 2);
        // Store in cache for archived runs
        if (this.sourceMode === 'archived' && this.selectedRunId) {
          this.cache.put(this.selectedRunId, file.path, text);
        }
        this.onFileContentLoaded(file, text);
      },
      error: (err) => {
        this.viewerError = `Failed to load file: ${err.error?.detail || err.message || 'Unknown error'}`;
        this.fileLoading = false;
        this.cdr.detectChanges();
      },
    });
  }

  private onFileContentLoaded(file: KnowledgeFile, text: string): void {
    this.selectedContent = text;
    if (this.canRender(file)) {
      this.renderContent(file, text);
    }
    this.fileLoading = false;
    this.cdr.detectChanges();
    setTimeout(() => document.getElementById('viewer')?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  }

  closeViewer(): void {
    this.selectedFile = null;
    this.selectedContent = null;
    this.renderedHtml = null;
    this.viewerError = null;
  }

  copyContent(): void {
    if (!this.selectedContent) return;
    navigator.clipboard.writeText(this.selectedContent).then(
      () => this.snackBar.open('Copied to clipboard', 'OK', { duration: 2000 }),
      () => this.snackBar.open('Failed to copy', 'OK', { duration: 3000 }),
    );
  }

  downloadContent(): void {
    if (!this.selectedFile || !this.selectedContent) return;
    const mimeMap: Record<string, string> = {
      json: 'application/json', md: 'text/markdown', html: 'text/html',
      adoc: 'text/asciidoc', xml: 'application/xml',
    };
    const mime = mimeMap[this.selectedFile.type] || 'text/plain';
    const blob = new Blob([this.selectedContent], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = this.selectedFile.name;
    a.click();
    URL.revokeObjectURL(url);
  }

  // ─── Rendering ─────────────────────────────────────────────────

  private sanitizeHtml(html: string): SafeHtml {
    const clean = DOMPurify.sanitize(html, {
      ALLOWED_TAGS: [
        'h1','h2','h3','h4','h5','h6','p','br','hr','ul','ol','li',
        'strong','em','b','i','u','s','code','pre','blockquote',
        'table','thead','tbody','tr','th','td','a','img','span','div',
        'dl','dt','dd','sub','sup','mark','details','summary',
      ],
      ALLOWED_ATTR: ['href','src','alt','title','class','style','id','target','rel','width','height'],
      ALLOW_DATA_ATTR: false,
    });
    return this.sanitizer.bypassSecurityTrustHtml(clean);
  }

  private renderContent(file: KnowledgeFile, text: string): void {
    if (file.type === 'md') {
      const html = marked.parse(text) as string;
      this.renderedHtml = this.sanitizeHtml(html);
    } else if (file.type === 'html') {
      this.renderedHtml = this.sanitizeHtml(text);
    } else if (file.type === 'json') {
      const highlighted = this.highlightJson(text);
      this.renderedHtml = this.sanitizeHtml(`<pre class="json-viewer">${highlighted}</pre>`);
    } else if (file.type === 'adoc') {
      this.renderedHtml = this.sanitizeHtml(this.renderAsciidoc(text));
    } else if (file.type === 'drawio') {
      this.renderedHtml = this.sanitizeHtml(this.renderDrawioInfo(text, file.name));
    } else if (file.type === 'confluence') {
      this.renderedHtml = this.sanitizeHtml(this.renderConfluence(text));
    }
  }

  private highlightJson(json: string): string {
    return json
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"([^"\\]*(\\.[^"\\]*)*)"\s*:/g, '<span class="json-key">"$1"</span>:')
      .replace(/:\s*"([^"\\]*(\\.[^"\\]*)*)"/g, ': <span class="json-string">"$1"</span>')
      .replace(/:\s*(\d+\.?\d*)/g, ': <span class="json-number">$1</span>')
      .replace(/:\s*(true|false)/g, ': <span class="json-bool">$1</span>')
      .replace(/:\s*(null)/g, ': <span class="json-null">$1</span>');
  }

  canRender(file: KnowledgeFile): boolean {
    return ['md', 'html', 'json', 'adoc', 'drawio', 'confluence'].includes(file.type);
  }

  private renderAsciidoc(text: string): string {
    const html = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/^={4}\s+(.+)$/gm, '<h4>$1</h4>')
      .replace(/^={3}\s+(.+)$/gm, '<h3>$1</h3>')
      .replace(/^={2}\s+(.+)$/gm, '<h2>$1</h2>')
      .replace(/^=\s+(.+)$/gm, '<h1>$1</h1>')
      .replace(/\*([^*]+)\*/g, '<strong>$1</strong>')
      .replace(/_([^_]+)_/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/link:([^[]+)\[([^\]]+)\]/g, '<a href="$1">$2</a>')
      .replace(/^\*\s+(.+)$/gm, '<li>$1</li>')
      .replace(/^\|(.+)\|$/gm, (_match, content) => {
        const cells = content
          .split('|')
          .map((c: string) => `<td>${c.trim()}</td>`)
          .join('');
        return `<tr>${cells}</tr>`;
      })
      .replace(/\n\n/g, '</p><p>');
    return `<div class="markdown-body"><p>${html}</p></div>`;
  }

  private renderDrawioInfo(xml: string, filename: string): string {
    const cellCount = (xml.match(/<mxCell/g) || []).length;
    return `
      <div style="text-align:center;padding:32px 24px">
        <div style="margin-bottom:16px">
          <svg width="64" height="64" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#F08705"/>
          <text x="32" y="42" fill="white" font-size="24" font-weight="bold" text-anchor="middle">.io</text></svg>
        </div>
        <h3 style="font-size:18px;margin:0 0 8px">${this.esc(filename)}</h3>
        <p style="font-size:13px;color:#6c757d;margin:0 0 8px">${cellCount} elements &middot; DrawIO XML diagram</p>
        <p style="font-size:13px;color:#6c757d;margin:0 0 16px">Open in <strong>draw.io</strong> or <strong>diagrams.net</strong> for interactive editing.</p>
        <div style="text-align:left">
          <pre class="json-viewer">${this.esc(xml.substring(0, 2000))}${xml.length > 2000 ? '\n...(truncated)' : ''}</pre>
        </div>
      </div>`;
  }

  private renderConfluence(text: string): string {
    const lines = text.split('\n');
    let html = '';
    let inTable = false;
    let inCode = false;

    for (const line of lines) {
      const trimmed = line.trim();
      if (/^\{code(:.*)?\}$/.test(trimmed)) {
        if (inCode) {
          html += '</code></pre>';
          inCode = false;
        } else {
          if (inTable) { html += '</tbody></table>'; inTable = false; }
          html += '<pre class="json-viewer"><code>';
          inCode = true;
        }
        continue;
      }
      if (inCode) { html += this.esc(line) + '\n'; continue; }
      if (trimmed === '----') {
        if (inTable) { html += '</tbody></table>'; inTable = false; }
        html += '<hr>';
        continue;
      }
      const hm = trimmed.match(/^h([1-6])\.\s+(.+)$/);
      if (hm) {
        if (inTable) { html += '</tbody></table>'; inTable = false; }
        html += `<h${hm[1]}>${this.cfInline(this.esc(hm[2]))}</h${hm[1]}>`;
        continue;
      }
      if (/^\|\|.+\|\|$/.test(trimmed)) {
        if (!inTable) { html += '<table><tbody>'; inTable = true; }
        const cells = trimmed.slice(2, -2).split('||').map((c) => `<th>${this.cfInline(this.esc(c.trim()))}</th>`).join('');
        html += `<tr>${cells}</tr>`;
        continue;
      }
      if (/^\|[^|].+\|$/.test(trimmed)) {
        if (!inTable) { html += '<table><tbody>'; inTable = true; }
        const cells = trimmed.slice(1, -1).split('|').map((c) => `<td>${this.cfInline(this.esc(c.trim()))}</td>`).join('');
        html += `<tr>${cells}</tr>`;
        continue;
      }
      if (inTable) { html += '</tbody></table>'; inTable = false; }
      if (/^\*\s+/.test(trimmed)) { html += `<li>${this.cfInline(this.esc(trimmed.replace(/^\*\s+/, '')))}</li>`; continue; }
      if (/^#\s+/.test(trimmed)) { html += `<li>${this.cfInline(this.esc(trimmed.replace(/^#\s+/, '')))}</li>`; continue; }
      if (trimmed === '') continue;
      html += `<p>${this.cfInline(this.esc(trimmed))}</p>`;
    }
    if (inTable) html += '</tbody></table>';
    if (inCode) html += '</code></pre>';
    return `<div class="markdown-body">${html}</div>`;
  }

  private esc(s: string): string {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  private cfInline(s: string): string {
    return s
      .replace(/\{\{([^}]+)\}\}/g, '<code>$1</code>')
      .replace(/\*([^*]+)\*/g, '<strong>$1</strong>')
      .replace(/_([^_]+)_/g, '<em>$1</em>')
      .replace(/\[([^\]|]+)\|([^\]]+)\]/g, '<a href="$2">$1</a>')
      .replace(/\[([^\]]+)\]/g, '<a href="$1">$1</a>');
  }

  // ─── Helpers ───────────────────────────────────────────────────

  private inDir(file: KnowledgeFile, dir: string): boolean {
    const normalized = file.path.replace(/\\/g, '/');
    return normalized.startsWith(dir + '/') || normalized.startsWith(dir + '\\');
  }

  private sortArc42(files: KnowledgeFile[]): KnowledgeFile[] {
    return files.sort((a, b) => {
      const numA = parseInt(a.name.match(/^(\d+)/)?.[1] || '99');
      const numB = parseInt(b.name.match(/^(\d+)/)?.[1] || '99');
      if (numA !== numB) return numA - numB;
      return a.name.localeCompare(b.name);
    });
  }

  private sortC4(files: KnowledgeFile[]): KnowledgeFile[] {
    const order: Record<string, number> = { context: 0, container: 1, component: 2, deployment: 3 };
    return files.sort((a, b) => {
      const la = a.name.toLowerCase();
      const lb = b.name.toLowerCase();
      const oa = Object.entries(order).find(([k]) => la.includes(k))?.[1] ?? 9;
      const ob = Object.entries(order).find(([k]) => lb.includes(k))?.[1] ?? 9;
      if (oa !== ob) return oa - ob;
      return a.name.localeCompare(b.name);
    });
  }

  cleanDocName(name: string): string {
    const m = name.match(/^(\d+)[-_](.+?)\.(\w+)$/);
    if (m) {
      const title = m[2].replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
      return `${m[1]} — ${title}`;
    }
    return name
      .replace(/\.\w+$/, '')
      .replace(/[-_]/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }

  fileIcon(type: string): string {
    switch (type) {
      case 'json': return 'data_object';
      case 'md': return 'article';
      case 'drawio': return 'architecture';
      case 'html': return 'web';
      case 'adoc': return 'description';
      case 'confluence': return 'edit_document';
      default: return 'insert_drive_file';
    }
  }

  formatBytes(bytes: number): string {
    return formatBytesUtil(bytes);
  }

  groupSize(group: FileGroup): number {
    return group.files.reduce((sum, f) => sum + f.size_bytes, 0);
  }

  formatRunDate(dateStr: string | null): string {
    if (!dateStr) return 'Unknown date';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' }) +
        ' ' + d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return dateStr;
    }
  }

  // ─── Item 3: Time Ago ──────────────────────────────────────────

  timeAgo(dateStr: string | null): string {
    if (!dateStr) return '';
    const diff = Date.now() - new Date(dateStr).getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return 'gerade eben';
    if (minutes < 60) return `vor ${minutes} Min.`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `vor ${hours} Std.`;
    const days = Math.floor(hours / 24);
    return `vor ${days} Tagen`;
  }

  // ─── Item 4: Keyboard Navigation ──────────────────────────────

  private navigateTab(delta: number): void {
    const idx = this.tabs.findIndex((t) => t.id === this.activeTab);
    const next = Math.max(0, Math.min(this.tabs.length - 1, idx + delta));
    if (next !== idx) {
      this.selectTab(this.tabs[next].id);
    }
  }

  private getCurrentTabFiles(): KnowledgeFile[] {
    switch (this.activeTab) {
      case 'documents': {
        const g = this.documentGroups.find((gr) => gr.id === this.activeDocGroup);
        return g?.files || [];
      }
      case 'analysis': return this.analysisFiles;
      case 'plans': return this.planFiles;
      case 'triage': return this.triageFiles;
      case 'extract': return this.extractFiles;
      default: return [];
    }
  }

  private navigateFile(delta: number): void {
    const files = this.getCurrentTabFiles();
    if (files.length === 0) return;
    this.focusedFileIndex = Math.max(0, Math.min(files.length - 1, this.focusedFileIndex + delta));
    this.cdr.detectChanges();
  }

  private openFocusedFile(): void {
    const files = this.getCurrentTabFiles();
    if (this.focusedFileIndex >= 0 && this.focusedFileIndex < files.length) {
      this.viewFile(files[this.focusedFileIndex]);
    }
  }

  isFileFocused(file: KnowledgeFile): boolean {
    const files = this.getCurrentTabFiles();
    return this.focusedFileIndex >= 0 && files[this.focusedFileIndex] === file;
  }

  // ─── Item 7: Architecture Diagram ─────────────────────────────

  private loadMermaidDiagram(): void {
    if (this.sourceMode === 'archived') {
      this.mermaidError = 'Architektur-Diagramm ist nur im lokalen Modus verfuegbar';
      this.cdr.detectChanges();
      return;
    }
    this.mermaidLoading = true;
    this.cdr.detectChanges();
    this.api.getArchitectureDiagram().subscribe({
      next: (data) => {
        this.mermaidDiagram = data.mermaid;
        this.renderMermaid(data.mermaid);
        this.mermaidLoading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.mermaidError = 'Fehler beim Laden des Architektur-Diagramms';
        this.mermaidLoading = false;
        this.cdr.detectChanges();
      },
    });
  }

  private async renderMermaid(code: string): Promise<void> {
    try {
      const mermaid = await import('mermaid');
      mermaid.default.initialize({ startOnLoad: false, theme: 'default' });
      const { svg } = await mermaid.default.render('arch-diagram', code);
      this.mermaidSvg = this.sanitizer.bypassSecurityTrustHtml(svg);
      this.cdr.detectChanges();
    } catch {
      this.mermaidError = 'Fehler beim Rendern des Diagramms';
      this.cdr.detectChanges();
    }
  }

  // ─── Item 10: Timeline ─────────────────────────────────────────

  timelineTooltip(run: VersionedRun): string {
    const id = run.pipeline_run_id || run.mlflow_run_id.substring(0, 8);
    const date = this.formatRunDate(run.started_at);
    const outcome = run.outcome || run.status;
    const count = this.artifactCounts[run.mlflow_run_id];
    return `${id} — ${date} — ${outcome}${count !== undefined ? ` — ${count} files` : ''}`;
  }

  // ─── Item 5: Diff View ─────────────────────────────────────────

  openDiffView(): void {
    this.diffMode = true;
    this.diffCompareRunId = null;
    this.diffLines = [];
    this.cdr.detectChanges();
  }

  closeDiff(): void {
    this.diffMode = false;
    this.diffCompareRunId = null;
    this.diffLines = [];
    this.cdr.detectChanges();
  }

  onDiffRunChange(runId: string): void {
    if (!this.selectedFile || !runId) return;
    this.diffCompareRunId = runId;
    this.diffLoading = true;
    this.cdr.detectChanges();

    this.api.getVersionFile(runId, this.selectedFile.path).subscribe({
      next: (content) => {
        const compareText = typeof content === 'string' ? content : JSON.stringify(content, null, 2);
        this.computeDiff(this.selectedContent || '', compareText);
        this.diffLoading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.diffLines = [{ type: 'remove', text: 'Datei nicht in diesem Run vorhanden' }];
        this.diffLoading = false;
        this.cdr.detectChanges();
      },
    });
  }

  private computeDiff(current: string, compare: string): void {
    const linesA = current.split('\n');
    const linesB = compare.split('\n');
    this.diffLines = [];

    // Simple line-by-line diff (unified style)
    const maxLen = Math.max(linesA.length, linesB.length);
    let ia = 0;
    let ib = 0;

    while (ia < linesA.length || ib < linesB.length) {
      if (ia < linesA.length && ib < linesB.length && linesA[ia] === linesB[ib]) {
        this.diffLines.push({ type: 'same', text: '  ' + linesA[ia] });
        ia++;
        ib++;
      } else {
        // Look ahead to find sync point
        let syncA = -1;
        let syncB = -1;
        for (let look = 1; look < 10 && look + ia < linesA.length; look++) {
          if (ib < linesB.length && linesA[ia + look] === linesB[ib]) {
            syncA = ia + look;
            break;
          }
        }
        for (let look = 1; look < 10 && look + ib < linesB.length; look++) {
          if (ia < linesA.length && linesB[ib + look] === linesA[ia]) {
            syncB = ib + look;
            break;
          }
        }

        if (syncA >= 0 && (syncB < 0 || syncA - ia <= syncB - ib)) {
          // Lines removed in compare
          while (ia < syncA) {
            this.diffLines.push({ type: 'add', text: '+ ' + linesA[ia] });
            ia++;
          }
        } else if (syncB >= 0) {
          // Lines added in compare
          while (ib < syncB) {
            this.diffLines.push({ type: 'remove', text: '- ' + linesB[ib] });
            ib++;
          }
        } else {
          // No sync, emit both
          if (ia < linesA.length) {
            this.diffLines.push({ type: 'add', text: '+ ' + linesA[ia] });
            ia++;
          }
          if (ib < linesB.length) {
            this.diffLines.push({ type: 'remove', text: '- ' + linesB[ib] });
            ib++;
          }
        }
      }

      if (this.diffLines.length > 5000) break; // Safety limit
    }
  }
}
