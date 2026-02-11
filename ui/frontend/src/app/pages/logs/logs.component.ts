import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
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
    FormsModule,
  ],
  template: `
    <div class="page-container">
      <h1 class="page-title">Logs</h1>

      <mat-card class="toolbar-card">
        <mat-card-content class="toolbar">
          <mat-form-field>
            <mat-label>Log file</mat-label>
            <mat-select [(ngModel)]="selectedFile" (selectionChange)="loadLog()">
              @for (f of logFiles; track f) {
                <mat-option [value]="f">{{ f }}</mat-option>
              }
            </mat-select>
          </mat-form-field>
          <button mat-stroked-button (click)="loadLog()">
            <mat-icon>refresh</mat-icon> Refresh
          </button>
          @if (logResponse) {
            <span class="line-count">{{ logResponse.total_lines }} lines total</span>
          }
        </mat-card-content>
      </mat-card>

      @if (logResponse) {
        <mat-card>
          <mat-card-content>
            <div class="log-viewer">
              @for (line of logResponse.lines; track $index) {
                <div class="log-line" [class]="lineClass(line)">{{ line }}</div>
              }
            </div>
          </mat-card-content>
        </mat-card>
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
      border-radius: 4px;
      font-family: "Cascadia Code", "Fira Code", "Consolas", monospace;
      font-size: 12px;
      line-height: 1.6;
    }
    .log-line {
      color: #d4d4d4;
      white-space: pre-wrap;
      word-break: break-all;
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

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getLogFiles().subscribe(files => {
      this.logFiles = files;
      if (files.length) {
        this.selectedFile = files[0];
        this.loadLog();
      }
    });
  }

  loadLog(): void {
    this.api.getLogs(this.selectedFile, 500).subscribe(r => this.logResponse = r);
  }

  lineClass(line: string): string {
    if (line.includes('ERROR') || line.includes('error')) return 'error';
    if (line.includes('WARNING') || line.includes('warning')) return 'warning';
    return 'info';
  }
}
