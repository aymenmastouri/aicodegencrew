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
import { RouterLink } from '@angular/router';

import { marked } from 'marked';
import { ApiService, KnowledgeFile } from '../../services/api.service';
import { formatBytes as formatBytesUtil } from '../../shared/phase-utils';

/** A group of files within a section. */
interface FileGroup {
  id: string;
  label: string;
  icon: string;
  phase: string;
  description: string;
  files: KnowledgeFile[];
}

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
    RouterLink,
  ],
  template: `
    <div class="page-container">
      <div class="page-header">
        <mat-icon class="page-icon">psychology</mat-icon>
        <div>
          <h1 class="page-title">Knowledge Explorer</h1>
          <p class="page-subtitle">Architecture documentation, analysis data & development artifacts</p>
        </div>
      </div>

      @if (loading) {
        <div class="loading-center">
          <mat-spinner diameter="36"></mat-spinner>
        </div>
      } @else if (totalFiles === 0) {
        <!-- Empty State -->
        <div class="empty-state">
          <mat-icon>psychology</mat-icon>
          <p>No knowledge base found. Run the pipeline to generate architecture documentation.</p>
          <button mat-flat-button color="primary" routerLink="/run">
            <mat-icon>rocket_launch</mat-icon> Run Pipeline
          </button>
        </div>
      } @else {
        <!-- Stats Bar -->
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
          @if (diagramCount > 0) {
            <div class="stat-item stat-diagrams">
              <mat-icon>architecture</mat-icon>
              <strong>{{ diagramCount }}</strong> diagrams
            </div>
          }
        </div>

        <!-- ═══════ SECTION 1: Architecture Documentation ═══════ -->
        @if (archGroups.length > 0) {
          <div class="section-card section-arch">
            <div class="section-head">
              <div class="section-icon-wrap arch-icon-wrap">
                <mat-icon>menu_book</mat-icon>
              </div>
              <div>
                <h2 class="section-title">Architecture Documentation</h2>
                <p class="section-sub">Arc42 template & C4 model — the primary architecture deliverables</p>
              </div>
            </div>

            <!-- Group Selector -->
            <div class="group-nav">
              @for (g of archGroups; track g.id) {
                <button
                  class="group-chip"
                  [class.group-active]="activeArchGroup === g.id"
                  (click)="selectArchGroup(g.id)"
                >
                  <mat-icon class="group-chip-icon">{{ g.icon }}</mat-icon>
                  {{ g.label }}
                  <span class="group-chip-count">{{ g.files.length }}</span>
                </button>
              }
            </div>

            <!-- Files -->
            @for (g of archGroups; track g.id) {
              @if (activeArchGroup === g.id) {
                @if (g.files.length === 0) {
                  <div class="section-empty">
                    <mat-icon>draft</mat-icon>
                    <span>No {{ g.label | lowercase }} generated yet. Run the <strong>Synthesis</strong> phase.</span>
                  </div>
                } @else {
                  <div class="doc-list">
                    @for (file of g.files; track file.path) {
                      <div
                        class="doc-row"
                        [class.doc-active]="selectedFile === file"
                        role="button"
                        tabindex="0"
                        (click)="viewFile(file)"
                        (keydown.enter)="viewFile(file)"
                        (keydown.space)="viewFile(file); $event.preventDefault()"
                      >
                        <mat-icon class="doc-icon" [class]="'type-' + file.type">{{ fileIcon(file.type) }}</mat-icon>
                        <div class="doc-info">
                          <span class="doc-name">{{ cleanDocName(file.name) }}</span>
                          <span class="doc-path">{{ file.path }}</span>
                        </div>
                        <span class="doc-badge" [class]="'badge-' + file.type">{{ file.type }}</span>
                        <span class="doc-size">{{ formatBytes(file.size_bytes) }}</span>
                        <mat-icon class="doc-arrow">chevron_right</mat-icon>
                      </div>
                    }
                  </div>
                }
              }
            }
          </div>
        }

        <!-- ═══════ SECTION 2: Pipeline Data ═══════ -->
        @if (dataGroups.length > 0) {
          <div class="section-card section-data">
            <div class="section-head">
              <div class="section-icon-wrap data-icon-wrap">
                <mat-icon>analytics</mat-icon>
              </div>
              <div>
                <h2 class="section-title">Development Artifacts</h2>
                <p class="section-sub">Development plans, code generation reports & delivery artifacts</p>
              </div>
            </div>

            <div class="data-groups">
              @for (g of dataGroups; track g.id) {
                <div class="data-group">
                  <div
                    class="dg-header"
                    role="button"
                    tabindex="0"
                    (click)="toggleDataGroup(g.id)"
                    (keydown.enter)="toggleDataGroup(g.id)"
                    (keydown.space)="toggleDataGroup(g.id); $event.preventDefault()"
                  >
                    <mat-icon class="dg-icon">{{ g.icon }}</mat-icon>
                    <span class="dg-label">{{ g.label }}</span>
                    <span class="dg-phase">{{ g.phase }}</span>
                    <span class="dg-count">{{ g.files.length }}</span>
                    <mat-icon class="dg-chevron">{{
                      expandedDataGroups.has(g.id) ? 'expand_less' : 'expand_more'
                    }}</mat-icon>
                  </div>
                  @if (expandedDataGroups.has(g.id)) {
                    <div class="dg-files">
                      @for (file of g.files; track file.path) {
                        <div
                          class="dg-file"
                          [class.doc-active]="selectedFile === file"
                          role="button"
                          tabindex="0"
                          (click)="viewFile(file)"
                          (keydown.enter)="viewFile(file)"
                          (keydown.space)="viewFile(file); $event.preventDefault()"
                        >
                          <mat-icon class="dg-file-icon" [class]="'type-' + file.type">{{
                            fileIcon(file.type)
                          }}</mat-icon>
                          <span class="dg-file-name">{{ file.name }}</span>
                          <span class="dg-file-size">{{ formatBytes(file.size_bytes) }}</span>
                        </div>
                      }
                    </div>
                  }
                </div>
              }
            </div>
          </div>
        }

        <!-- ═══════ SECTION 3: Other Files ═══════ -->
        @if (otherFiles.length > 0) {
          <div class="section-card section-other">
            <div class="section-head">
              <div class="section-icon-wrap other-icon-wrap">
                <mat-icon>folder</mat-icon>
              </div>
              <div>
                <h2 class="section-title">Other Files</h2>
                <p class="section-sub">Uncategorized knowledge artifacts</p>
              </div>
            </div>
            <div class="doc-list">
              @for (file of otherFiles; track file.path) {
                <div
                  class="doc-row"
                  [class.doc-active]="selectedFile === file"
                  role="button"
                  tabindex="0"
                  (click)="viewFile(file)"
                  (keydown.enter)="viewFile(file)"
                  (keydown.space)="viewFile(file); $event.preventDefault()"
                >
                  <mat-icon class="doc-icon" [class]="'type-' + file.type">{{ fileIcon(file.type) }}</mat-icon>
                  <div class="doc-info">
                    <span class="doc-name">{{ file.name }}</span>
                    <span class="doc-path">{{ file.path }}</span>
                  </div>
                  <span class="doc-badge" [class]="'badge-' + file.type">{{ file.type }}</span>
                  <span class="doc-size">{{ formatBytes(file.size_bytes) }}</span>
                  <mat-icon class="doc-arrow">chevron_right</mat-icon>
                </div>
              }
            </div>
          </div>
        }

        <!-- ═══════ DOCUMENT VIEWER ═══════ -->
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
              } @else if (viewMode === 'rendered' && renderedHtml) {
                <div class="rendered-content markdown-body" [innerHTML]="renderedHtml"></div>
              } @else {
                <pre class="source-content code-viewer">{{ selectedContent }}</pre>
              }
            </div>
          </div>
        }
      }
    </div>
  `,
  styles: [
    `
      /* ── Stats icons ─────────────────────────────────── */
      .stat-docs .mat-icon {
        color: var(--cg-blue);
      }
      .stat-data .mat-icon {
        color: var(--cg-vibrant);
      }
      .stat-diagrams .mat-icon {
        color: var(--cg-success);
      }

      /* ── Section Cards ───────────────────────────────── */
      .section-card {
        background: #fff;
        border-radius: 14px;
        margin-bottom: 20px;
        overflow: hidden;
        border: 1px solid var(--cg-gray-100);
      }
      .section-head {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 20px 24px 16px;
      }
      .section-icon-wrap {
        width: 42px;
        height: 42px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
      }
      .section-icon-wrap .mat-icon {
        font-size: 22px;
        width: 22px;
        height: 22px;
        color: #fff;
      }
      .arch-icon-wrap {
        background: var(--cg-blue);
      }
      .data-icon-wrap {
        background: var(--cg-vibrant);
      }
      .other-icon-wrap {
        background: var(--cg-gray-400);
      }
      .section-title {
        font-size: 16px;
        font-weight: 500;
        margin: 0;
        color: var(--cg-gray-900);
      }
      .section-sub {
        font-size: 12px;
        color: var(--cg-gray-500);
        margin: 2px 0 0;
      }

      /* ── Group Navigation (arch section) ─────────────── */
      .group-nav {
        display: flex;
        gap: 8px;
        padding: 0 24px 12px;
        flex-wrap: wrap;
      }
      .group-chip {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 5px 14px;
        border-radius: 20px;
        border: 1px solid var(--cg-gray-200);
        background: #fff;
        font-size: 13px;
        cursor: pointer;
        transition: all 0.15s;
        color: var(--cg-gray-500);
      }
      .group-chip:hover {
        border-color: var(--cg-blue);
        color: var(--cg-blue);
      }
      .group-active {
        background: rgba(0, 112, 173, 0.08);
        border-color: var(--cg-blue);
        color: var(--cg-blue);
        font-weight: 500;
      }
      .group-chip-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
      }
      .group-chip-count {
        background: var(--cg-gray-100);
        padding: 0px 6px;
        border-radius: 10px;
        font-size: 11px;
        font-weight: 600;
      }
      .group-active .group-chip-count {
        background: rgba(0, 112, 173, 0.15);
      }

      /* ── Document List (arch + other) ────────────────── */
      .doc-list {
        padding: 0 12px 12px;
      }
      .doc-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 12px;
        border-radius: 8px;
        cursor: pointer;
        transition: background 0.1s;
      }
      .doc-row:hover {
        background: var(--cg-gray-50);
      }
      .doc-active {
        background: rgba(0, 112, 173, 0.06) !important;
      }
      .doc-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
        flex-shrink: 0;
      }
      .doc-info {
        flex: 1;
        min-width: 0;
      }
      .doc-name {
        display: block;
        font-size: 13px;
        font-weight: 500;
        color: var(--cg-gray-900);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .doc-path {
        display: block;
        font-size: 11px;
        font-family: monospace;
        color: var(--cg-gray-400);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .doc-badge {
        display: inline-block;
        padding: 1px 8px;
        border-radius: 8px;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.3px;
        flex-shrink: 0;
      }
      .doc-size {
        font-size: 11px;
        color: var(--cg-gray-400);
        white-space: nowrap;
        flex-shrink: 0;
      }
      .doc-arrow {
        font-size: 18px;
        width: 18px;
        height: 18px;
        color: var(--cg-gray-300);
        flex-shrink: 0;
      }

      /* ── Section Empty ───────────────────────────────── */
      .section-empty {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 20px 24px;
        color: var(--cg-gray-400);
        font-size: 13px;
      }
      .section-empty .mat-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
        color: var(--cg-gray-300);
      }

      /* ── Data Groups (accordion) ─────────────────────── */
      .data-groups {
        padding: 0 12px 12px;
      }
      .data-group {
        border-radius: 8px;
        overflow: hidden;
        margin-bottom: 2px;
      }
      .dg-header {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 12px;
        cursor: pointer;
        border-radius: 8px;
        transition: background 0.1s;
      }
      .dg-header:hover {
        background: var(--cg-gray-50);
      }
      .dg-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
        color: var(--cg-vibrant);
      }
      .dg-label {
        font-size: 13px;
        font-weight: 500;
        color: var(--cg-gray-900);
      }
      .dg-phase {
        font-size: 11px;
        color: var(--cg-gray-400);
        flex: 1;
      }
      .dg-count {
        font-size: 12px;
        font-weight: 600;
        color: var(--cg-gray-500);
        background: var(--cg-gray-100);
        padding: 0 7px;
        border-radius: 10px;
      }
      .dg-chevron {
        font-size: 20px;
        width: 20px;
        height: 20px;
        color: var(--cg-gray-300);
      }
      .dg-files {
        padding: 0 0 4px 18px;
      }
      .dg-file {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 7px 12px;
        border-radius: 6px;
        cursor: pointer;
        transition: background 0.1s;
      }
      .dg-file:hover {
        background: var(--cg-gray-50);
      }
      .dg-file-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
      }
      .dg-file-name {
        flex: 1;
        font-size: 12px;
        font-family: monospace;
        color: var(--cg-gray-600);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .dg-file-size {
        font-size: 11px;
        color: var(--cg-gray-400);
        white-space: nowrap;
        flex-shrink: 0;
      }

      /* ── Type Colors ─────────────────────────────────── */
      .type-json {
        color: var(--cg-vibrant);
      }
      .type-md {
        color: var(--cg-blue);
      }
      .type-drawio {
        color: var(--cg-success);
      }
      .type-html {
        color: #e44d26;
      }
      .type-adoc {
        color: #a0522d;
      }
      .type-confluence {
        color: #0052cc;
      }
      .type-other {
        color: var(--cg-gray-500);
      }

      .badge-json {
        background: rgba(18, 171, 219, 0.1);
        color: var(--cg-vibrant);
      }
      .badge-md {
        background: rgba(0, 112, 173, 0.1);
        color: var(--cg-blue);
      }
      .badge-drawio {
        background: rgba(40, 167, 69, 0.1);
        color: var(--cg-success);
      }
      .badge-html {
        background: rgba(228, 77, 38, 0.1);
        color: #e44d26;
      }
      .badge-adoc {
        background: rgba(160, 82, 45, 0.1);
        color: #a0522d;
      }
      .badge-confluence {
        background: rgba(0, 82, 204, 0.1);
        color: #0052cc;
      }
      .badge-other {
        background: var(--cg-gray-100);
        color: var(--cg-gray-500);
      }

      /* ── Viewer Panel ────────────────────────────────── */
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
  diagramCount = 0;

  archGroups: FileGroup[] = [];
  activeArchGroup = '';

  dataGroups: FileGroup[] = [];
  expandedDataGroups = new Set<string>();
  internalFiles: KnowledgeFile[] = [];

  otherFiles: KnowledgeFile[] = [];

  selectedFile: KnowledgeFile | null = null;
  selectedContent: string | null = null;
  renderedHtml: SafeHtml | null = null;
  viewMode: 'source' | 'rendered' = 'rendered';
  fileLoading = false;

  constructor(
    private api: ApiService,
    private cdr: ChangeDetectorRef,
    private sanitizer: DomSanitizer,
    private snackBar: MatSnackBar,
  ) {}

  @HostListener('document:keydown.escape')
  onEscapeKey(): void {
    if (this.selectedFile) this.closeViewer();
  }

  ngOnInit(): void {
    this.loadKnowledge();
    this.refreshTimer = setInterval(() => this.loadKnowledge(), 10000);
  }

  ngOnDestroy(): void {
    if (this.refreshTimer) clearInterval(this.refreshTimer);
  }

  private loadKnowledge(): void {
    this.api.getKnowledgeFiles().subscribe({
      next: (s) => {
        this.categorize(s.files);
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.cdr.markForCheck();
      },
    });
  }

  // ─── Categorization ─────────────────────────────────────────────
  private categorize(files: KnowledgeFile[]): void {
    // Architecture Documentation (document / legacy phase3_synthesis)
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

    this.archGroups = [
      {
        id: 'arc42',
        label: 'Arc42 Docs',
        icon: 'menu_book',
        phase: 'Phase 3',
        description: 'Arc42 architecture template chapters',
        files: arc42,
      },
      {
        id: 'c4',
        label: 'C4 Model',
        icon: 'account_tree',
        phase: 'Phase 3',
        description: 'C4 diagrams (context, container, component, deployment)',
        files: c4,
      },
      ...(quality.length > 0
        ? [
            {
              id: 'quality',
              label: 'Quality',
              icon: 'verified',
              phase: 'Phase 3',
              description: 'Quality assessment reports',
              files: quality,
            },
          ]
        : []),
      ...(synthOther.length > 0
        ? [
            {
              id: 'synth-other',
              label: 'Other Synthesis',
              icon: 'description',
              phase: 'Phase 3',
              description: 'Additional synthesis artifacts',
              files: synthOther,
            },
          ]
        : []),
    ].filter((g) => g.files.length > 0);

    if (this.archGroups.length > 0) {
      this.activeArchGroup = this.archGroups[0].id;
    }

    // Internal pipeline data (hidden — not user-facing)
    const facts = files.filter((f) => this.inDir(f, 'extract') || this.inDir(f, 'phase1_facts'));
    const analysis = files.filter((f) => this.inDir(f, 'analyze') || this.inDir(f, 'phase2_analysis'));
    this.internalFiles = [...facts, ...analysis];

    // Development Artifacts (user-facing outputs only)
    const plans = files.filter((f) => this.inDir(f, 'plan') || this.inDir(f, 'phase4_planning'));
    const codegen = files.filter((f) => this.inDir(f, 'implement') || this.inDir(f, 'phase5_codegen'));
    const testing = files.filter((f) => this.inDir(f, 'verify') || this.inDir(f, 'phase6_testing'));
    const deployment = files.filter((f) => this.inDir(f, 'deliver') || this.inDir(f, 'phase7_deployment'));

    this.dataGroups = [
      {
        id: 'plans',
        label: 'Development Plans',
        icon: 'assignment',
        phase: 'Plan',
        description: 'Generated development plans',
        files: plans,
      },
      {
        id: 'codegen',
        label: 'Code Reports',
        icon: 'code',
        phase: 'Implement',
        description: 'Code generation reports',
        files: codegen,
      },
      ...(testing.length > 0
        ? [
            {
              id: 'testing',
              label: 'Test Reports',
              icon: 'science',
              phase: 'Verify',
              description: 'Test generation output',
              files: testing,
            },
          ]
        : []),
      ...(deployment.length > 0
        ? [
            {
              id: 'deploy',
              label: 'Delivery',
              icon: 'rocket_launch',
              phase: 'Deliver',
              description: 'Review & delivery artifacts',
              files: deployment,
            },
          ]
        : []),
    ].filter((g) => g.files.length > 0);

    // Auto-expand first data group
    if (this.dataGroups.length > 0) {
      this.expandedDataGroups.add(this.dataGroups[0].id);
    }

    // Other: anything not classified
    const classified = new Set([
      ...arc42,
      ...c4,
      ...quality,
      ...synthOther,
      ...facts,
      ...analysis,
      ...plans,
      ...codegen,
      ...testing,
      ...deployment,
    ]);
    this.otherFiles = files.filter((f) => !classified.has(f));

    // Stats (exclude internal pipeline data)
    const visibleFiles = files.filter((f) => !this.internalFiles.includes(f));
    this.totalFiles = visibleFiles.length;
    this.totalSize = visibleFiles.reduce((sum, f) => sum + f.size_bytes, 0);
    const docTypes = new Set(['md', 'adoc', 'html', 'confluence']);
    this.docCount = [...arc42, ...c4, ...quality, ...synthOther].filter((f) => docTypes.has(f.type)).length;
    this.dataCount = [...plans, ...codegen, ...testing, ...deployment].length;
    this.diagramCount = visibleFiles.filter((f) => f.type === 'drawio').length;
  }

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

  // ─── Interactions ───────────────────────────────────────────────

  selectArchGroup(id: string): void {
    this.activeArchGroup = id;
    this.closeViewer();
  }

  toggleDataGroup(id: string): void {
    if (this.expandedDataGroups.has(id)) {
      this.expandedDataGroups.delete(id);
    } else {
      this.expandedDataGroups.add(id);
    }
  }

  viewFile(file: KnowledgeFile): void {
    this.selectedFile = file;
    this.fileLoading = true;
    this.selectedContent = null;
    this.renderedHtml = null;
    this.viewMode = this.canRender(file) ? 'rendered' : 'source';
    this.cdr.markForCheck();

    this.api.getKnowledgeFile(file.path).subscribe({
      next: (content) => {
        const text = typeof content === 'string' ? content : JSON.stringify(content, null, 2);
        this.selectedContent = text;
        if (this.canRender(file)) {
          this.renderContent(file, text);
        }
        this.fileLoading = false;
        this.cdr.markForCheck();

        // Scroll to viewer
        setTimeout(() => document.getElementById('viewer')?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
      },
      error: () => {
        this.selectedContent = 'Error loading file';
        this.fileLoading = false;
        this.cdr.markForCheck();
      },
    });
  }

  closeViewer(): void {
    this.selectedFile = null;
    this.selectedContent = null;
    this.renderedHtml = null;
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
      json: 'application/json',
      md: 'text/markdown',
      html: 'text/html',
      adoc: 'text/asciidoc',
      xml: 'application/xml',
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

  // ─── Rendering ──────────────────────────────────────────────────

  private renderContent(file: KnowledgeFile, text: string): void {
    if (file.type === 'md') {
      const html = marked.parse(text) as string;
      this.renderedHtml = this.sanitizer.bypassSecurityTrustHtml(html);
    } else if (file.type === 'html') {
      this.renderedHtml = this.sanitizer.bypassSecurityTrustHtml(text);
    } else if (file.type === 'json') {
      const highlighted = this.highlightJson(text);
      this.renderedHtml = this.sanitizer.bypassSecurityTrustHtml(`<pre class="json-viewer">${highlighted}</pre>`);
    } else if (file.type === 'adoc') {
      this.renderedHtml = this.sanitizer.bypassSecurityTrustHtml(this.renderAsciidoc(text));
    } else if (file.type === 'drawio') {
      this.renderedHtml = this.sanitizer.bypassSecurityTrustHtml(this.renderDrawioInfo(text, file.name));
    } else if (file.type === 'confluence') {
      this.renderedHtml = this.sanitizer.bypassSecurityTrustHtml(this.renderConfluence(text));
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
          if (inTable) {
            html += '</tbody></table>';
            inTable = false;
          }
          html += '<pre class="json-viewer"><code>';
          inCode = true;
        }
        continue;
      }
      if (inCode) {
        html += this.esc(line) + '\n';
        continue;
      }
      if (trimmed === '----') {
        if (inTable) {
          html += '</tbody></table>';
          inTable = false;
        }
        html += '<hr>';
        continue;
      }
      const hm = trimmed.match(/^h([1-6])\.\s+(.+)$/);
      if (hm) {
        if (inTable) {
          html += '</tbody></table>';
          inTable = false;
        }
        html += `<h${hm[1]}>${this.cfInline(this.esc(hm[2]))}</h${hm[1]}>`;
        continue;
      }
      if (/^\|\|.+\|\|$/.test(trimmed)) {
        if (!inTable) {
          html += '<table><tbody>';
          inTable = true;
        }
        const cells = trimmed
          .slice(2, -2)
          .split('||')
          .map((c) => `<th>${this.cfInline(this.esc(c.trim()))}</th>`)
          .join('');
        html += `<tr>${cells}</tr>`;
        continue;
      }
      if (/^\|[^|].+\|$/.test(trimmed)) {
        if (!inTable) {
          html += '<table><tbody>';
          inTable = true;
        }
        const cells = trimmed
          .slice(1, -1)
          .split('|')
          .map((c) => `<td>${this.cfInline(this.esc(c.trim()))}</td>`)
          .join('');
        html += `<tr>${cells}</tr>`;
        continue;
      }
      if (inTable) {
        html += '</tbody></table>';
        inTable = false;
      }
      if (/^\*\s+/.test(trimmed)) {
        html += `<li>${this.cfInline(this.esc(trimmed.replace(/^\*\s+/, '')))}</li>`;
        continue;
      }
      if (/^#\s+/.test(trimmed)) {
        html += `<li>${this.cfInline(this.esc(trimmed.replace(/^#\s+/, '')))}</li>`;
        continue;
      }
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

  // ─── Helpers ────────────────────────────────────────────────────

  cleanDocName(name: string): string {
    // "01-introduction.md" → "01 — Introduction"
    const m = name.match(/^(\d+)[-_](.+?)\.(\w+)$/);
    if (m) {
      const title = m[2].replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
      return `${m[1]} — ${title}`;
    }
    // "c4-component.md" → "C4 Component"
    return name
      .replace(/\.\w+$/, '')
      .replace(/[-_]/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }

  fileIcon(type: string): string {
    switch (type) {
      case 'json':
        return 'data_object';
      case 'md':
        return 'article';
      case 'drawio':
        return 'architecture';
      case 'html':
        return 'web';
      case 'adoc':
        return 'description';
      case 'confluence':
        return 'edit_document';
      default:
        return 'insert_drive_file';
    }
  }

  formatBytes(bytes: number): string {
    return formatBytesUtil(bytes);
  }
}
