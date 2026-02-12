import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { ApiService, KnowledgeSummary, KnowledgeFile } from '../../services/api.service';

@Component({
  selector: 'app-outputs',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule,
  ],
  template: `
    <div class="page-container">
      <div class="page-header">
        <mat-icon class="page-icon">code</mat-icon>
        <div>
          <h1 class="page-title">Outputs</h1>
          <p class="page-subtitle">Browse generated plans, code, and pipeline output files</p>
        </div>
      </div>

      <!-- Filters -->
      <div class="filter-bar">
        <mat-form-field appearance="outline" class="filter-field">
          <mat-label>Filter by phase</mat-label>
          <mat-select [(ngModel)]="filterPhase" (selectionChange)="applyFilters()">
            <mat-option value="">All phases</mat-option>
            @for (phase of availablePhases; track phase) {
              <mat-option [value]="phase">{{ phase }}</mat-option>
            }
          </mat-select>
        </mat-form-field>
        <mat-form-field appearance="outline" class="filter-field">
          <mat-label>Search files</mat-label>
          <input matInput [(ngModel)]="searchQuery" (input)="applyFilters()" placeholder="Filter by name..." />
          <mat-icon matSuffix>search</mat-icon>
        </mat-form-field>
        <span class="filter-count">{{ filteredFiles.length }} files</span>
      </div>

      @if (loading) {
        <div class="loading-center">
          <mat-spinner diameter="36"></mat-spinner>
        </div>
      } @else {
        <div class="split-layout">
          <!-- File List (left) -->
          <div class="file-list">
            @if (filteredFiles.length === 0) {
              <div class="empty-list">
                <mat-icon>folder_open</mat-icon>
                <p>No output files found</p>
              </div>
            }
            @for (file of filteredFiles; track file.path) {
              <div class="file-item" [class.file-selected]="selectedFile?.path === file.path"
                   (click)="selectFile(file)">
                <mat-icon class="file-type-icon">{{ getFileIcon(file) }}</mat-icon>
                <div class="file-info">
                  <div class="file-name">{{ file.name }}</div>
                  <div class="file-meta">
                    <span class="file-phase">{{ getPhaseLabel(file) }}</span>
                    <span class="file-size">{{ formatSize(file.size_bytes) }}</span>
                  </div>
                </div>
              </div>
            }
          </div>

          <!-- Content Viewer (right) -->
          <div class="content-viewer">
            @if (!selectedFile) {
              <div class="viewer-empty">
                <mat-icon>preview</mat-icon>
                <p>Select a file to view its contents</p>
              </div>
            } @else if (loadingContent) {
              <div class="loading-center">
                <mat-spinner diameter="28"></mat-spinner>
              </div>
            } @else {
              <div class="viewer-header">
                <div class="viewer-title">{{ selectedFile.name }}</div>
                <div class="viewer-actions">
                  <button mat-icon-button matTooltip="Copy to clipboard" (click)="copyContent()">
                    <mat-icon>content_copy</mat-icon>
                  </button>
                  <button mat-icon-button matTooltip="Download file" (click)="downloadContent()">
                    <mat-icon>download</mat-icon>
                  </button>
                </div>
              </div>
              <div class="viewer-body">
                @if (isJson) {
                  <pre class="json-viewer">{{ contentFormatted }}</pre>
                } @else {
                  <pre class="code-viewer"><code>{{ contentRaw }}</code></pre>
                }
              </div>
            }
          </div>
        </div>
      }
    </div>
  `,
  styles: [
    `
      .page-header {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 20px;
      }
      .page-icon {
        font-size: 28px;
        width: 28px;
        height: 28px;
        color: var(--cg-blue);
      }
      .page-title {
        font-size: 22px;
        font-weight: 500;
        margin: 0;
        color: var(--cg-gray-900);
      }
      .page-subtitle {
        font-size: 13px;
        color: var(--cg-gray-500);
        margin: 2px 0 0;
      }
      .loading-center {
        display: flex;
        justify-content: center;
        padding: 48px 0;
      }

      /* Filters */
      .filter-bar {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
      }
      .filter-field {
        width: 220px;
      }
      .filter-field ::ng-deep .mat-mdc-form-field-subscript-wrapper { display: none; }
      .filter-count {
        font-size: 12px;
        color: var(--cg-gray-400);
        margin-left: auto;
      }

      /* Split layout */
      .split-layout {
        display: flex;
        gap: 16px;
        min-height: calc(100vh - 280px);
      }

      /* File list */
      .file-list {
        width: 30%;
        min-width: 260px;
        max-height: calc(100vh - 280px);
        overflow-y: auto;
        background: #fff;
        border-radius: 10px;
        padding: 4px;
      }
      .file-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 12px;
        border-radius: 8px;
        cursor: pointer;
        transition: background 0.12s;
        border-left: 3px solid transparent;
      }
      .file-item:hover { background: var(--cg-gray-50, #f8f9fa); }
      .file-selected {
        background: rgba(18, 171, 219, 0.08) !important;
        border-left-color: var(--cg-vibrant);
      }
      .file-type-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
        color: var(--cg-gray-400);
        flex-shrink: 0;
      }
      .file-name {
        font-size: 13px;
        font-weight: 500;
        color: var(--cg-gray-900);
        word-break: break-all;
      }
      .file-meta {
        display: flex;
        gap: 8px;
        margin-top: 2px;
      }
      .file-phase {
        font-size: 11px;
        color: var(--cg-blue);
        font-weight: 500;
      }
      .file-size {
        font-size: 11px;
        color: var(--cg-gray-400);
      }
      .empty-list {
        text-align: center;
        padding: 40px 20px;
        color: var(--cg-gray-400);
      }
      .empty-list mat-icon {
        font-size: 36px;
        width: 36px;
        height: 36px;
        margin-bottom: 8px;
      }
      .empty-list p { font-size: 13px; }

      /* Content viewer */
      .content-viewer {
        flex: 1;
        background: #fff;
        border-radius: 10px;
        display: flex;
        flex-direction: column;
        max-height: calc(100vh - 280px);
      }
      .viewer-empty {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: var(--cg-gray-300);
      }
      .viewer-empty mat-icon {
        font-size: 40px;
        width: 40px;
        height: 40px;
        margin-bottom: 8px;
      }
      .viewer-empty p { font-size: 13px; }
      .viewer-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 16px;
        border-bottom: 1px solid var(--cg-gray-100, #f0f0f0);
      }
      .viewer-title {
        font-size: 14px;
        font-weight: 500;
        color: var(--cg-gray-900);
        font-family: monospace;
      }
      .viewer-actions {
        display: flex;
        gap: 4px;
      }
      .viewer-body {
        flex: 1;
        overflow: auto;
        padding: 16px;
      }
      .json-viewer, .code-viewer {
        margin: 0;
        font-size: 12px;
        line-height: 1.6;
        font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
        white-space: pre-wrap;
        word-break: break-word;
        color: var(--cg-gray-800, #333);
      }
      .json-viewer {
        color: var(--cg-navy, #0070ad);
      }
      .code-viewer code {
        counter-reset: line;
      }
    `,
  ],
})
export class OutputsComponent implements OnInit {
  loading = true;
  loadingContent = false;
  allFiles: KnowledgeFile[] = [];
  filteredFiles: KnowledgeFile[] = [];
  selectedFile: KnowledgeFile | null = null;
  contentRaw = '';
  contentFormatted = '';
  isJson = false;

  filterPhase = '';
  searchQuery = '';
  availablePhases: string[] = [];

  constructor(
    private api: ApiService,
    private snackBar: MatSnackBar,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.api.getKnowledgeFiles().subscribe({
      next: (summary: KnowledgeSummary) => {
        this.allFiles = summary.files;
        this.availablePhases = [...new Set(summary.files.map((f) => this.getPhaseLabel(f)))].sort();
        this.applyFilters();
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.cdr.markForCheck();
      },
    });
  }

  applyFilters(): void {
    let files = this.allFiles;
    if (this.filterPhase) {
      files = files.filter((f) => this.getPhaseLabel(f) === this.filterPhase);
    }
    if (this.searchQuery) {
      const q = this.searchQuery.toLowerCase();
      files = files.filter((f) => f.name.toLowerCase().includes(q) || f.path.toLowerCase().includes(q));
    }
    this.filteredFiles = files;
  }

  selectFile(file: KnowledgeFile): void {
    this.selectedFile = file;
    this.loadingContent = true;
    this.api.getKnowledgeFile(file.path).subscribe({
      next: (content: unknown) => {
        if (typeof content === 'object') {
          this.isJson = true;
          this.contentFormatted = JSON.stringify(content, null, 2);
          this.contentRaw = this.contentFormatted;
        } else {
          this.isJson = false;
          this.contentRaw = String(content);
          this.contentFormatted = this.contentRaw;
        }
        this.loadingContent = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.contentRaw = 'Failed to load file content';
        this.contentFormatted = this.contentRaw;
        this.isJson = false;
        this.loadingContent = false;
        this.cdr.markForCheck();
      },
    });
  }

  /** Extract the first subdirectory from the file path, humanize as label */
  getPhaseLabel(file: KnowledgeFile): string {
    const path = file.path.replace(/\\/g, '/');
    const withoutPrefix = path.replace(/^knowledge\/?/i, '');
    const firstSegment = withoutPrefix.split('/')[0] || '';
    if (!firstSegment) return 'Root';
    // Humanize: replace _ and - with spaces, title case
    return firstSegment
      .replace(/[_-]/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }

  getFileIcon(file: KnowledgeFile): string {
    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    switch (ext) {
      case 'json': return 'data_object';
      case 'md': return 'description';
      case 'drawio': return 'schema';
      default: return 'insert_drive_file';
    }
  }

  formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  copyContent(): void {
    navigator.clipboard.writeText(this.contentRaw).then(() => {
      this.snackBar.open('Copied to clipboard', 'OK', { duration: 2000 });
    });
  }

  downloadContent(): void {
    if (!this.selectedFile) return;
    const blob = new Blob([this.contentRaw], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = this.selectedFile.name;
    a.click();
    URL.revokeObjectURL(url);
  }
}
