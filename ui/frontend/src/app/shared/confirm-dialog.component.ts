import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';

export interface ConfirmDialogData {
  title: string;
  message: string;
  details?: string[];
  type?: 'warn' | 'info';
  icon?: string;
  confirmLabel?: string;
}

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule, MatChipsModule],
  template: `
    <div class="dialog-header" [class]="'header-' + (data.type || 'warn')">
      <mat-icon class="dialog-icon">{{ data.icon || (data.type === 'info' ? 'info' : 'warning') }}</mat-icon>
      <h2 class="dialog-title">{{ data.title }}</h2>
    </div>
    <mat-dialog-content>
      <p class="dialog-message">{{ data.message }}</p>
      @if (data.details?.length) {
        <div class="detail-chips">
          @for (detail of data.details; track detail) {
            <span class="detail-chip">{{ detail }}</span>
          }
        </div>
      }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button (click)="dialogRef.close(false)">Cancel</button>
      <button mat-flat-button [color]="data.type === 'info' ? 'primary' : 'warn'" (click)="dialogRef.close(true)">
        {{ data.confirmLabel || 'Confirm' }}
      </button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      .dialog-header {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 20px 24px 12px;
      }
      .header-warn .dialog-icon {
        color: var(--cg-error, #dc3545);
      }
      .header-info .dialog-icon {
        color: var(--cg-blue, #0070ad);
      }
      .dialog-icon {
        font-size: 28px;
        width: 28px;
        height: 28px;
      }
      .dialog-title {
        font-size: 18px;
        font-weight: 500;
        margin: 0;
      }
      .dialog-message {
        font-size: 14px;
        color: var(--cg-gray-600, #555);
        line-height: 1.5;
        margin: 0 0 12px;
        white-space: pre-line;
      }
      .detail-chips {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
      }
      .detail-chip {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
        background: var(--cg-gray-100, #f0f0f0);
        color: var(--cg-gray-700, #555);
      }
    `,
  ],
})
export class ConfirmDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<ConfirmDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ConfirmDialogData,
  ) {}
}
