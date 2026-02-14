import { Component, OnInit, ChangeDetectorRef, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { InputsService, CategoryDetail, InputFile } from '../../services/inputs.service';
import { formatBytes as formatBytesUtil } from '../../shared/phase-utils';

interface CategoryView {
  id: string;
  label: string;
  description: string;
  icon: string;
  accepted_extensions: string[];
  files: InputFile[];
  file_count: number;
  total_size: number;
  uploading: boolean;
  dragOver: boolean;
  error: string;
}

@Component({
  selector: 'app-input-files',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatChipsModule,
    MatProgressBarModule,
    MatSnackBarModule,
    MatTooltipModule,
  ],
  template: `
    <div class="page-container">
      <div class="page-header">
        <mat-icon class="page-icon">upload_file</mat-icon>
        <div>
          <h1 class="page-title">Input Files</h1>
          <p class="page-subtitle">Upload and manage task files, requirements, and reference documents</p>
        </div>
      </div>

      <!-- Stats Bar -->
      <div class="stats-bar">
        <div class="stat-item">
          <mat-icon>folder</mat-icon>
          <span class="stat-value">{{ totalFiles }}</span>
          <span class="stat-label">Total Files</span>
        </div>
        <div class="stat-item">
          <mat-icon>storage</mat-icon>
          <span class="stat-value">{{ formatSize(totalSize) }}</span>
          <span class="stat-label">Total Size</span>
        </div>
        @for (cat of categories; track cat.id) {
          <div class="stat-item">
            <mat-icon>{{ cat.icon }}</mat-icon>
            <span class="stat-value">{{ cat.file_count }}</span>
            <span class="stat-label">{{ cat.label }}</span>
          </div>
        }
      </div>

      <!-- Category Cards -->
      <div class="categories-grid">
        @for (cat of categories; track cat.id) {
          <mat-card class="category-card">
            <mat-card-header>
              <mat-icon mat-card-avatar class="cat-icon">{{ cat.icon }}</mat-icon>
              <mat-card-title>
                {{ cat.label }}
                @if (cat.file_count > 0) {
                  <span class="file-count-badge">{{ cat.file_count }}</span>
                }
              </mat-card-title>
              <mat-card-subtitle>{{ cat.description }}</mat-card-subtitle>
            </mat-card-header>

            <mat-card-content>
              <!-- Accepted formats -->
              <div class="ext-chips">
                @for (ext of cat.accepted_extensions; track ext) {
                  <span class="ext-chip">{{ ext }}</span>
                }
              </div>

              <!-- Drop zone -->
              <div
                class="drop-zone"
                [class.drag-over]="cat.dragOver"
                [class.has-error]="cat.error"
                (dragover)="onDragOver($event, cat)"
                (dragleave)="onDragLeave(cat)"
                (drop)="onDrop($event, cat)"
                (click)="fileInput.click()"
              >
                <input
                  #fileInput
                  type="file"
                  hidden
                  multiple
                  [accept]="cat.accepted_extensions.join(',')"
                  (change)="onFileSelected($event, cat)"
                />
                @if (cat.uploading) {
                  <mat-progress-bar mode="indeterminate"></mat-progress-bar>
                } @else {
                  <mat-icon class="drop-icon">cloud_upload</mat-icon>
                  <span class="drop-text">
                    @if (cat.dragOver) {
                      Drop files here
                    } @else {
                      Drag & drop or click to browse
                    }
                  </span>
                  <span class="drop-hint">{{ getHint(cat.id) }}</span>
                }
              </div>

              @if (cat.error) {
                <div class="error-msg">
                  <mat-icon>error_outline</mat-icon>
                  {{ cat.error }}
                </div>
              }

              <!-- File list -->
              @if (cat.files.length > 0) {
                <div class="file-list">
                  @for (file of cat.files; track file.filename) {
                    <div class="file-row">
                      <mat-icon class="file-type-icon">{{ getFileIcon(file.extension) }}</mat-icon>
                      <div class="file-info">
                        <span class="file-name">{{ file.filename }}</span>
                        <span class="file-meta"
                          >{{ formatSize(file.size_bytes) }} &middot; {{ formatDate(file.modified) }}</span
                        >
                      </div>
                      <button mat-icon-button color="warn" matTooltip="Delete file" (click)="deleteFile(cat, file)">
                        <mat-icon>delete_outline</mat-icon>
                      </button>
                    </div>
                  }
                </div>
              } @else {
                <div class="empty-state">
                  <mat-icon>inbox</mat-icon>
                  <span>No files yet</span>
                </div>
              }
            </mat-card-content>
          </mat-card>
        }
      </div>
    </div>
  `,
  styles: [
    `
      .categories-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(480px, 1fr));
        gap: 20px;
      }
      .category-card {
        border-radius: 12px;
      }
      .cat-icon {
        background: rgba(0, 112, 173, 0.08);
        color: var(--cg-blue) !important;
        border-radius: 10px !important;
        display: flex !important;
        align-items: center;
        justify-content: center;
      }
      .file-count-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 22px;
        height: 22px;
        padding: 0 6px;
        border-radius: 11px;
        background: var(--cg-vibrant);
        color: #fff;
        font-size: 12px;
        font-weight: 600;
        margin-left: 8px;
        vertical-align: middle;
      }
      .ext-chips {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        margin-bottom: 12px;
      }
      .ext-chip {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        background: var(--cg-gray-100);
        font-size: 11px;
        font-family: monospace;
        color: var(--cg-gray-500);
      }
      .drop-zone {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 6px;
        padding: 24px 16px;
        border: 2px dashed var(--cg-gray-200);
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.15s ease;
        margin-bottom: 12px;
        min-height: 80px;
      }
      .drop-zone:hover {
        border-color: var(--cg-blue);
        background: rgba(0, 112, 173, 0.03);
      }
      .drop-zone.drag-over {
        border-color: var(--cg-vibrant);
        background: rgba(18, 171, 219, 0.06);
        border-style: solid;
      }
      .drop-zone.has-error {
        border-color: var(--cg-error);
        background: rgba(220, 53, 69, 0.03);
      }
      .drop-icon {
        font-size: 32px;
        width: 32px;
        height: 32px;
        color: var(--cg-gray-200);
      }
      .drop-zone:hover .drop-icon,
      .drop-zone.drag-over .drop-icon {
        color: var(--cg-blue);
      }
      .drop-text {
        font-size: 13px;
        color: var(--cg-gray-500);
        font-weight: 500;
      }
      .drop-hint {
        font-size: 11px;
        color: var(--cg-gray-200);
      }
      .error-msg {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        color: var(--cg-error);
        margin-bottom: 12px;
      }
      .error-msg .mat-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
      }
      .file-list {
        display: flex;
        flex-direction: column;
        gap: 2px;
      }
      .file-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 10px;
        border-radius: 8px;
        transition: background 0.1s;
      }
      .file-row:hover {
        background: var(--cg-gray-50);
      }
      .file-type-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
        color: var(--cg-blue);
      }
      .file-info {
        flex: 1;
        display: flex;
        flex-direction: column;
        min-width: 0;
      }
      .file-name {
        font-size: 13px;
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .file-meta {
        font-size: 11px;
        color: var(--cg-gray-500);
      }
      .empty-state {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding: 20px;
        color: var(--cg-gray-200);
        font-size: 13px;
      }
      .empty-state .mat-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
      }
    `,
  ],
})
export class InputFilesComponent implements OnInit {
  categories: CategoryView[] = [];
  totalFiles = 0;
  totalSize = 0;

  private hints: Record<string, string> = {
    tasks: 'Drop JIRA XML exports, tickets, or task descriptions here',
    requirements: 'Drop requirement docs, specs, or matrices here',
    logs: 'Drop application log files for analysis here',
    reference: 'Drop mockups, diagrams, or design documents here',
  };

  constructor(
    private inputsService: InputsService,
    private snackBar: MatSnackBar,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.loadAll();
  }

  loadAll(): void {
    this.inputsService.listAll().subscribe({
      next: (data) => {
        this.categories = Object.entries(data).map(([id, cat]) => ({
          id,
          label: cat.label,
          description: cat.description,
          icon: cat.icon,
          accepted_extensions: cat.accepted_extensions,
          files: cat.files,
          file_count: cat.file_count,
          total_size: cat.total_size,
          uploading: false,
          dragOver: false,
          error: '',
        }));
        this.totalFiles = this.categories.reduce((s, c) => s + c.file_count, 0);
        this.totalSize = this.categories.reduce((s, c) => s + c.total_size, 0);
        this.cdr.markForCheck();
      },
      error: () => {
        this.snackBar.open('Failed to load input files', 'Dismiss', { duration: 4000 });
        this.cdr.markForCheck();
      },
    });
  }

  getHint(categoryId: string): string {
    return this.hints[categoryId] || '';
  }

  onDragOver(event: DragEvent, cat: CategoryView): void {
    event.preventDefault();
    event.stopPropagation();
    cat.dragOver = true;
    this.cdr.markForCheck();
  }

  onDragLeave(cat: CategoryView): void {
    cat.dragOver = false;
    this.cdr.markForCheck();
  }

  onDrop(event: DragEvent, cat: CategoryView): void {
    event.preventDefault();
    event.stopPropagation();
    cat.dragOver = false;
    cat.error = '';

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.uploadFiles(cat, Array.from(files));
    }
    this.cdr.markForCheck();
  }

  onFileSelected(event: Event, cat: CategoryView): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      cat.error = '';
      this.uploadFiles(cat, Array.from(input.files));
      input.value = '';
    }
  }

  private uploadFiles(cat: CategoryView, files: File[]): void {
    cat.uploading = true;
    this.cdr.markForCheck();
    let completed = 0;
    let errors = 0;

    for (const file of files) {
      this.inputsService.uploadFile(cat.id, file).subscribe({
        next: () => {
          completed++;
          if (completed + errors === files.length) {
            cat.uploading = false;
            if (errors === 0) {
              this.snackBar.open(`Uploaded ${completed} file${completed > 1 ? 's' : ''} to ${cat.label}`, 'OK', {
                duration: 3000,
              });
            }
            this.loadAll();
          }
        },
        error: (err) => {
          errors++;
          const msg = err?.error?.detail || `Failed to upload ${file.name}`;
          cat.error = msg;
          if (completed + errors === files.length) {
            cat.uploading = false;
            this.snackBar.open(msg, 'Dismiss', { duration: 5000 });
            this.loadAll();
          }
          this.cdr.markForCheck();
        },
      });
    }
  }

  deleteFile(cat: CategoryView, file: InputFile): void {
    this.inputsService.deleteFile(cat.id, file.filename).subscribe({
      next: () => {
        this.snackBar.open(`Deleted ${file.filename}`, 'OK', { duration: 3000 });
        this.loadAll();
      },
      error: () => {
        this.snackBar.open(`Failed to delete ${file.filename}`, 'Dismiss', { duration: 4000 });
        this.cdr.markForCheck();
      },
    });
  }

  getFileIcon(ext: string): string {
    switch (ext) {
      case '.xml':
        return 'code';
      case '.json':
        return 'data_object';
      case '.pdf':
        return 'picture_as_pdf';
      case '.docx':
      case '.doc':
        return 'article';
      case '.xlsx':
      case '.xls':
      case '.csv':
        return 'table_chart';
      case '.png':
      case '.jpg':
      case '.jpeg':
      case '.svg':
        return 'image';
      case '.drawio':
        return 'schema';
      case '.pptx':
        return 'slideshow';
      case '.md':
        return 'description';
      case '.log':
      case '.txt':
        return 'text_snippet';
      default:
        return 'insert_drive_file';
    }
  }

  formatSize(bytes: number): string {
    return formatBytesUtil(bytes);
  }

  formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
}
