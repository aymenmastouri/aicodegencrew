import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatTableModule } from '@angular/material/table';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { ApiService, PhaseInfo, PresetInfo, PipelineStatus } from '../../services/api.service';

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
  ],
  template: `
    <div class="page-container">
      <h1 class="page-title">
        <mat-icon>account_tree</mat-icon>
        Phases
      </h1>

      @if (loading) {
        <div class="loading-center">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else {
        <mat-card>
          <mat-card-header>
            <mat-card-title class="section-card-title">
              <mat-icon>settings_suggest</mat-icon>
              Phase Configuration
            </mat-card-title>
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
                <th mat-header-cell *matHeaderCellDef>Phase ID</th>
                <td mat-cell *matCellDef="let p" class="mono">{{ p.id }}</td>
              </ng-container>
              <ng-container matColumnDef="name">
                <th mat-header-cell *matHeaderCellDef>Name</th>
                <td mat-cell *matCellDef="let p">{{ p.name }}</td>
              </ng-container>
              <ng-container matColumnDef="status">
                <th mat-header-cell *matHeaderCellDef>Status</th>
                <td mat-cell *matCellDef="let p">
                  <span class="status-chip" [class]="'status-' + getPhaseStatus(p.id)">
                    {{ getPhaseStatus(p.id) }}
                  </span>
                </td>
              </ng-container>
              <ng-container matColumnDef="dependencies">
                <th mat-header-cell *matHeaderCellDef>Dependencies</th>
                <td mat-cell *matCellDef="let p">
                  @for (dep of p.dependencies; track dep) {
                    <mat-chip class="dep-chip">{{ dep | slice:0:20 }}</mat-chip>
                  }
                </td>
              </ng-container>
              <ng-container matColumnDef="actions">
                <th mat-header-cell *matHeaderCellDef></th>
                <td mat-cell *matCellDef="let p">
                  <button mat-icon-button color="primary" (click)="runPhase(p.id)" matTooltip="Run this phase">
                    <mat-icon>play_arrow</mat-icon>
                  </button>
                </td>
              </ng-container>
              <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
              <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
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
                  <mat-chip>{{ phase }}</mat-chip>
                }
              </mat-chip-set>
              <div class="preset-action">
                <button mat-flat-button color="primary" (click)="runPreset(preset.name)">
                  <mat-icon>play_arrow</mat-icon>
                  Run {{ preset.display_name || preset.name }}
                </button>
              </div>
            </mat-expansion-panel>
          }
        </mat-accordion>
      }
    </div>
  `,
  styles: [`
    .section-card-title {
      display: flex !important;
      align-items: center;
      gap: 8px;
    }
    .phase-table { width: 100%; }
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
    .dep-chip { font-size: 11px; }
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
    .preset-action { margin-top: 16px; }
  `],
})
export class PhasesComponent implements OnInit {
  phases: PhaseInfo[] = [];
  presets: PresetInfo[] = [];
  pipeline: PipelineStatus | null = null;
  displayedColumns = ['order', 'id', 'name', 'status', 'dependencies', 'actions'];
  loading = true;

  constructor(private api: ApiService, private router: Router, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.api.getPhases().subscribe({
      next: p => { this.phases = p; this.loading = false; this.cdr.markForCheck(); },
      error: () => { this.loading = false; this.cdr.markForCheck(); },
    });
    this.api.getPresets().subscribe(p => { this.presets = p; this.cdr.markForCheck(); });
    this.api.getPipelineStatus().subscribe(p => { this.pipeline = p; this.cdr.markForCheck(); });
  }

  getPhaseStatus(phaseId: string): string {
    if (!this.pipeline) return 'idle';
    const phase = this.pipeline.phases.find(p => p.id === phaseId);
    return phase?.status || 'idle';
  }

  runPreset(presetName: string): void {
    this.router.navigate(['/run'], { queryParams: { preset: presetName } });
  }

  runPhase(phaseId: string): void {
    this.router.navigate(['/run'], { queryParams: { phase: phaseId } });
  }
}
