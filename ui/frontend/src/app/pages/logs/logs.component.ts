import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { FormsModule } from '@angular/forms';

import { ApiService, LogResponse } from '../../services/api.service';

@Component({
  selector: 'app-logs',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatSelectModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    FormsModule,
  ],
  template: `
    <div class="page-container">
      <h1 class="page-title">
        <mat-icon>receipt_long</mat-icon>
        Logs
      </h1>

      <mat-card class="toolbar-card">
        <mat-card-content class="toolbar">
          <mat-form-field appearance="outline">
            <mat-label>Log file</mat-label>
            <mat-select [(ngModel)]="selectedFile" (selectionChange)="loadLog()">
              @for (f of logFiles; track f) {
                <mat-option [value]="f">{{ f }}</mat-option>
              }
            </mat-select>
          </mat-form-field>
          <button mat-stroked-button (click)="loadLog()" matTooltip="Refresh log">
            <mat-icon>refresh</mat-icon> Refresh
          </button>
          @if (logResponse) {
            <span class="line-count">{{ logResponse.total_lines }} lines total</span>
          }
        </mat-card-content>
      </mat-card>

      @if (loading) {
        <div class="loading-center">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (logResponse) {
        <mat-card>
          <mat-card-content>
            <div class="log-viewer">
              @for (line of logResponse.lines; track $index) {
                <div class="log-line" [class]="lineClass(line)">
                  <span class="log-num">{{ $index + 1 }}</span>{{ line }}
                </div>
              }
            </div>
          </mat-card-content>
        </mat-card>
      } @else if (logFiles.length === 0) {
        <div class="empty-state">
          <mat-icon>receipt_long</mat-icon>
          <p>No log files found. Logs are generated when the pipeline runs.</p>
        </div>
      }
    </div>
  `,
  styles: [`
    .toolbar {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .toolbar-card { margin-bottom: 16px; }
    .line-count {
      color: var(--cg-gray-500);
      font-size: 13px;
    }
    .log-viewer {
      max-height: 600px;
      overflow: auto;
      background: var(--cg-dark);
      padding: 12px;
      border-radius: 8px;
      font-family: "Cascadia Code", "Fira Code", "Consolas", monospace;
      font-size: 12px;
      line-height: 1.6;
    }
    .log-line {
      color: #d4d4d4;
      white-space: pre-wrap;
      word-break: break-all;
    }
    .log-num {
      display: inline-block;
      width: 36px;
      text-align: right;
      margin-right: 12px;
      color: rgba(255,255,255,0.2);
      user-select: none;
    }
    .log-line.error { color: #f48771; }
    .log-line.warning { color: #cca700; }
    .log-line.info { color: #d4d4d4; }
  `],
})
export class LogsComponent implements OnInit {
  logFiles: string[] = [];
  selectedFile = 'aicodegencrew.log';
  logResponse: LogResponse | null = null;
  loading = true;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.api.getLogFiles().subscribe({
      next: files => {
        this.logFiles = files;
        if (files.length) {
          this.selectedFile = files[0];
          this.loadLog();
        } else {
          this.loading = false;
        }
        this.cdr.markForCheck();
      },
      error: () => { this.loading = false; this.cdr.markForCheck(); },
    });
  }

  loadLog(): void {
    this.loading = true;
    this.cdr.markForCheck();
    this.api.getLogs(this.selectedFile, 500).subscribe({
      next: r => { this.logResponse = r; this.loading = false; this.cdr.markForCheck(); },
      error: () => { this.loading = false; this.cdr.markForCheck(); },
    });
  }

  lineClass(line: string): string {
    if (line.includes('ERROR') || line.includes('error')) return 'error';
    if (line.includes('WARNING') || line.includes('warning')) return 'warning';
    return 'info';
  }
}
