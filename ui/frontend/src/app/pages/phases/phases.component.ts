import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';

import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatTableModule } from '@angular/material/table';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';

import { ApiService, PhaseInfo, PresetInfo, PipelineStatus } from '../../services/api.service';
import { PipelineService, ResetPreview } from '../../services/pipeline.service';
import { ConfirmDialogComponent, ConfirmDialogData } from '../../shared/confirm-dialog.component';
import { humanizePhaseId } from '../../shared/phase-utils';
import { isTerminal } from '../../shared/status';

@Component({
  selector: 'app-phases',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatChipsModule,
    MatTableModule,
    MatExpansionModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatDialogModule,
  ],
  template: `
    <div class="page-container">
      <div class="page-header">
        <mat-icon class="page-icon">account_tree</mat-icon>
        <div>
          <h1 class="page-title">Phases</h1>
          <p class="page-subtitle">View and manage pipeline phase configuration and presets</p>
        </div>
      </div>

      @if (loading) {
        <div class="loading-center">
          <mat-spinner diameter="36"></mat-spinner>
        </div>
      } @else {
        <mat-card>
          <mat-card-header>
            <mat-card-title class="section-card-title">
              <mat-icon>settings_suggest</mat-icon>
              Phase Configuration
            </mat-card-title>
            <span class="spacer"></span>
            <button
              mat-stroked-button
              color="warn"
              [disabled]="!hasResettablePhases()"
              (click)="resetAll()"
              matTooltip="Reset all completed/failed phases"
            >
              <mat-icon>restart_alt</mat-icon>
              Reset All
            </button>
          </mat-card-header>
          <mat-card-content>
            <table mat-table [dataSource]="phases" class="phase-table">
              <ng-container matColumnDef="order">
                <th mat-header-cell *matHeaderCellDef>#</th>
                <td mat-cell *matCellDef="let p">
                  <span class="phase-num">{{ p.order }}</span>
                </td>
              </ng-container>
              <ng-container matColumnDef="id">
                <th mat-header-cell *matHeaderCellDef>Type</th>
                <td mat-cell *matCellDef="let p">
                  <span class="phase-type">{{ p.type || 'pipeline' }}</span>
                </td>
              </ng-container>
              <ng-container matColumnDef="name">
                <th mat-header-cell *matHeaderCellDef>Name</th>
                <td mat-cell *matCellDef="let p">{{ p.name }}</td>
              </ng-container>
              <ng-container matColumnDef="status">
                <th mat-header-cell *matHeaderCellDef>Status</th>
                <td mat-cell *matCellDef="let p">
                  <span class="status-chip" [class]="'status-' + getPhaseStatus(p.id)">
                    @if (getPhaseStatus(p.id) === 'running') {
                      <mat-spinner diameter="14" class="inline-spinner"></mat-spinner>
                    }
                    @if (getPhaseStatus(p.id) === 'failed') {
                      <mat-icon class="status-icon-error" [matTooltip]="getPhaseError(p.id)">error_outline</mat-icon>
                    }
                    {{ getPhaseStatus(p.id) }}
                  </span>
                </td>
              </ng-container>
              <ng-container matColumnDef="dependencies">
                <th mat-header-cell *matHeaderCellDef>Dependencies</th>
                <td mat-cell *matCellDef="let p">
                  @for (dep of p.dependencies; track dep) {
                    <mat-chip class="dep-chip">{{ humanize(dep) }}</mat-chip>
                  }
                </td>
              </ng-container>
              <ng-container matColumnDef="actions">
                <th mat-header-cell *matHeaderCellDef></th>
                <td mat-cell *matCellDef="let p">
                  <button
                    mat-icon-button
                    color="warn"
                    [disabled]="!isPhaseTerminal(getPhaseStatus(p.id))"
                    (click)="resetPhase(p.id)"
                    matTooltip="Reset this phase"
                    aria-label="Reset this phase"
                  >
                    <mat-icon>restart_alt</mat-icon>
                  </button>
                </td>
              </ng-container>
              <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
              <tr mat-row *matRowDef="let row; columns: displayedColumns"></tr>
            </table>
          </mat-card-content>
        </mat-card>

        <h2 class="section-title">Presets</h2>
        <mat-accordion>
          @for (preset of presets; track preset.name) {
            <mat-expansion-panel>
              <mat-expansion-panel-header>
                <mat-panel-title>
                  <mat-icon class="preset-icon">{{ preset.icon || 'playlist_play' }}</mat-icon>
                  {{ preset.display_name || preset.name }}
                </mat-panel-title>
                <mat-panel-description>{{ preset.phases.length }} phases</mat-panel-description>
              </mat-expansion-panel-header>
              @if (preset.description) {
                <p class="preset-desc">{{ preset.description }}</p>
              }
              <mat-chip-set>
                @for (phase of preset.phases; track phase) {
                  <mat-chip>{{ humanize(phase) }}</mat-chip>
                }
              </mat-chip-set>
            </mat-expansion-panel>
          }
        </mat-accordion>
      }
    </div>
  `,
  styles: [
    `
      .phase-table {
        width: 100%;
      }
      .phase-table tr.mat-mdc-row:hover {
        background: rgba(0, 112, 173, 0.03);
      }
      .phase-num {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 26px;
        height: 26px;
        border-radius: 6px;
        background: var(--cg-gray-100);
        font-size: 12px;
        font-weight: 600;
        color: var(--cg-gray-500);
      }
      .phase-type {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 11px;
        font-weight: 500;
        text-transform: capitalize;
        background: var(--cg-gray-100);
        color: var(--cg-gray-600);
      }
      .dep-chip {
        font-size: 11px;
      }
      .section-title {
        margin-top: 32px;
        margin-bottom: 16px;
        font-weight: 400;
        font-size: 20px;
      }
      .preset-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
        margin-right: 8px;
        color: var(--cg-blue);
      }
      .preset-desc {
        font-size: 13px;
        color: var(--cg-gray-500);
        margin: 0 0 12px;
      }
      .spacer {
        flex: 1;
      }
      mat-card-header {
        display: flex;
        align-items: center;
      }
      .inline-spinner {
        display: inline-block;
        vertical-align: middle;
        margin-right: 4px;
      }
      .status-icon-error {
        font-size: 16px;
        width: 16px;
        height: 16px;
        vertical-align: middle;
        margin-right: 2px;
        color: var(--cg-red, #d32f2f);
      }
      .status-running {
        color: var(--cg-blue, #0070ad);
        font-weight: 500;
      }
      .status-failed {
        color: var(--cg-red, #d32f2f);
        font-weight: 500;
      }
    `,
  ],
})
export class PhasesComponent implements OnInit, OnDestroy {
  phases: PhaseInfo[] = [];
  presets: PresetInfo[] = [];
  pipeline: PipelineStatus | null = null;
  displayedColumns = ['order', 'id', 'name', 'status', 'dependencies', 'actions'];
  loading = true;
  private refreshTimer: ReturnType<typeof setInterval> | null = null;

  constructor(
    private api: ApiService,
    private pipelineService: PipelineService,
    private cdr: ChangeDetectorRef,
    private snackBar: MatSnackBar,
    private dialog: MatDialog,
  ) {}

  ngOnInit(): void {
    this.api.getPhases().subscribe({
      next: (p) => {
        this.phases = p;
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.cdr.markForCheck();
      },
    });
    this.api.getPresets().subscribe((p) => {
      this.presets = p;
      this.cdr.markForCheck();
    });
    this.api.getPipelineStatus().subscribe((p) => {
      this.pipeline = p;
      this.startAutoRefreshIfNeeded();
      this.cdr.markForCheck();
    });
  }

  ngOnDestroy(): void {
    this.stopAutoRefresh();
  }

  humanize(phaseId: string): string {
    return humanizePhaseId(phaseId);
  }

  isPhaseTerminal(status: string): boolean {
    return isTerminal(status);
  }

  getPhaseStatus(phaseId: string): string {
    if (!this.pipeline) return 'idle';
    const phase = this.pipeline.phases.find((p) => p.id === phaseId);
    return phase?.status || 'idle';
  }

  hasCompletedPhases(): boolean {
    if (!this.pipeline) return false;
    return this.pipeline.phases.some((p) => p.status === 'completed');
  }

  hasResettablePhases(): boolean {
    if (!this.pipeline) return false;
    return this.pipeline.phases.some((p) => isTerminal(p.status) && p.id !== 'discover');
  }

  getPhaseError(phaseId: string): string {
    if (!this.pipeline) return '';
    const phase = this.pipeline.phases.find((p) => p.id === phaseId);
    return phase?.last_run ? `Failed at ${phase.last_run}` : 'Phase failed';
  }

  private startAutoRefreshIfNeeded(): void {
    if (this.pipeline?.is_running && !this.refreshTimer) {
      this.refreshTimer = setInterval(() => this.refreshStatus(), 3000);
    } else if (!this.pipeline?.is_running && this.refreshTimer) {
      this.stopAutoRefresh();
    }
  }

  private stopAutoRefresh(): void {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
  }

  private phaseDisplayName(phaseId: string): string {
    const phase = this.phases.find((p) => p.id === phaseId);
    return phase?.name || humanizePhaseId(phaseId);
  }

  resetPhase(phaseId: string): void {
    const phaseName = this.phaseDisplayName(phaseId);

    // Discover: clear status only (preserve ChromaDB index)
    if (phaseId === 'discover') {
      const ref = this.dialog.open(ConfirmDialogComponent, {
        width: '480px',
        data: {
          title: `Clear ${phaseName} Status`,
          message: `This will clear the status for ${phaseName}.\nThe ChromaDB index will not be deleted.`,
          details: [phaseName],
          type: 'info',
          icon: 'refresh',
          confirmLabel: 'Clear Status',
        } as ConfirmDialogData,
      });
      ref.afterClosed().subscribe((confirmed) => {
        if (!confirmed) return;
        this.pipelineService.clearPhaseState([phaseId]).subscribe({
          next: () => {
            this.snackBar.open(`${phaseName} status cleared`, 'OK', { duration: 4000 });
            this.refreshStatus();
          },
          error: (err) => {
            this.snackBar.open(err?.error?.detail || 'Clear status failed', 'OK', { duration: 4000 });
          },
        });
      });
      return;
    }

    const cascade = true;
    this.pipelineService.previewReset([phaseId], cascade).subscribe({
      next: (preview: ResetPreview) => {
        const names = preview.phases_to_reset.map((id) => this.phaseDisplayName(id));
        const ref = this.dialog.open(ConfirmDialogComponent, {
          width: '480px',
          data: {
            title: `Reset ${phaseName}`,
            message: `The following phase(s) will be reset.\n${preview.files_to_delete.length} file(s) will be deleted.`,
            details: names,
            type: 'warn',
            icon: 'restart_alt',
            confirmLabel: 'Reset',
          } as ConfirmDialogData,
        });
        ref.afterClosed().subscribe((confirmed) => {
          if (!confirmed) return;
          this.pipelineService.executeReset([phaseId], cascade).subscribe({
            next: (result) => {
              this.snackBar.open(
                `Reset ${result.reset_phases.length} phase(s), deleted ${result.deleted_count} file(s)`,
                'OK',
                { duration: 4000 },
              );
              this.refreshStatus();
            },
            error: (err) => {
              this.snackBar.open(err?.error?.detail || 'Reset failed', 'OK', { duration: 4000 });
            },
          });
        });
      },
    });
  }

  resetAll(): void {
    const phaseIds =
      this.pipeline?.phases
        .filter((p) => (p.status === 'completed' || p.status === 'failed') && p.id !== 'discover')
        .map((p) => p.id) || [];

    this.pipelineService.previewReset(phaseIds).subscribe({
      next: (preview: ResetPreview) => {
        const names = preview.phases_to_reset.map((id) => this.phaseDisplayName(id));
        const ref = this.dialog.open(ConfirmDialogComponent, {
          width: '480px',
          data: {
            title: 'Reset All Phases (excluding Discover)',
            message: `The following ${names.length} phase(s) will be reset.\n${preview.files_to_delete.length} file(s) will be deleted.`,
            details: names,
            type: 'warn',
            icon: 'restart_alt',
            confirmLabel: 'Reset All',
          } as ConfirmDialogData,
        });
        ref.afterClosed().subscribe((confirmed) => {
          if (!confirmed) return;
          this.pipelineService.executeReset(preview.phases_to_reset).subscribe({
            next: (result) => {
              this.snackBar.open(
                `Reset ${result.reset_phases.length} phase(s), deleted ${result.deleted_count} file(s)`,
                'OK',
                { duration: 4000 },
              );
              this.refreshStatus();
            },
            error: (err) => {
              this.snackBar.open(err?.error?.detail || 'Reset failed', 'OK', { duration: 4000 });
            },
          });
        });
      },
    });
  }

  private refreshStatus(): void {
    this.api.getPipelineStatus().subscribe((p) => {
      this.pipeline = p;
      this.startAutoRefreshIfNeeded();
      this.cdr.markForCheck();
    });
  }
}
