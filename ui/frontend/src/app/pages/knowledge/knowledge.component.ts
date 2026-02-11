import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule } from '@angular/material/dialog';

import { ApiService, KnowledgeFile, KnowledgeSummary } from '../../services/api.service';

@Component({
  selector: 'app-knowledge',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatTableModule,
    MatButtonModule,
    MatDialogModule,
  ],
  template: `
    <div class="page-container">
      <h1 class="page-title">Knowledge Explorer</h1>

      @if (summary) {
        <div class="stats">
          <mat-card>
            <mat-card-content>
              <strong>{{ summary.total_files }}</strong> files |
              <strong>{{ formatBytes(summary.total_size_bytes) }}</strong> total
            </mat-card-content>
          </mat-card>
        </div>

        <mat-card>
          <mat-card-content>
            <table mat-table [dataSource]="summary.files" class="files-table">
              <ng-container matColumnDef="type">
                <th mat-header-cell *matHeaderCellDef>Type</th>
                <td mat-cell *matCellDef="let f">
                  <mat-icon>{{ fileIcon(f.type) }}</mat-icon>
                </td>
              </ng-container>
              <ng-container matColumnDef="path">
                <th mat-header-cell *matHeaderCellDef>Path</th>
                <td mat-cell *matCellDef="let f" class="mono">{{ f.path }}</td>
              </ng-container>
              <ng-container matColumnDef="size">
                <th mat-header-cell *matHeaderCellDef>Size</th>
                <td mat-cell *matCellDef="let f">{{ formatBytes(f.size_bytes) }}</td>
              </ng-container>
              <ng-container matColumnDef="modified">
                <th mat-header-cell *matHeaderCellDef>Modified</th>
                <td mat-cell *matCellDef="let f">{{ f.modified | slice:0:19 }}</td>
              </ng-container>
              <ng-container matColumnDef="actions">
                <th mat-header-cell *matHeaderCellDef></th>
                <td mat-cell *matCellDef="let f">
                  <button mat-icon-button (click)="viewFile(f)">
                    <mat-icon>visibility</mat-icon>
                  </button>
                </td>
              </ng-container>
              <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
              <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
            </table>
          </mat-card-content>
        </mat-card>
      }

      @if (selectedContent) {
        <mat-card class="preview-card">
          <mat-card-header>
            <mat-card-title>{{ selectedFile?.name }}</mat-card-title>
            <span class="spacer"></span>
            <button mat-icon-button (click)="selectedContent = null">
              <mat-icon>close</mat-icon>
            </button>
          </mat-card-header>
          <mat-card-content>
            <pre class="mono file-content">{{ selectedContent }}</pre>
          </mat-card-content>
        </mat-card>
      }
    </div>
  `,
  styles: [`
    .stats { margin-bottom: 16px; }
    .files-table { width: 100%; }
    .spacer { flex: 1; }
    .preview-card { margin-top: 16px; }
    .file-content {
      max-height: 500px;
      overflow: auto;
      background: #263238;
      color: #eeffff;
      padding: 16px;
      border-radius: 4px;
      white-space: pre-wrap;
      word-break: break-all;
    }
  `],
})
export class KnowledgeComponent implements OnInit {
  summary: KnowledgeSummary | null = null;
  selectedFile: KnowledgeFile | null = null;
  selectedContent: string | null = null;
  displayedColumns = ['type', 'path', 'size', 'modified', 'actions'];

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getKnowledgeFiles().subscribe(s => this.summary = s);
  }

  fileIcon(type: string): string {
    switch (type) {
      case 'json': return 'data_object';
      case 'md': return 'article';
      case 'drawio': return 'architecture';
      default: return 'insert_drive_file';
    }
  }

  formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  viewFile(file: KnowledgeFile): void {
    this.selectedFile = file;
    this.api.getKnowledgeFile(file.path).subscribe({
      next: (content) => {
        this.selectedContent = typeof content === 'string'
          ? content
          : JSON.stringify(content, null, 2);
      },
      error: () => {
        this.selectedContent = 'Error loading file';
      },
    });
  }
}
