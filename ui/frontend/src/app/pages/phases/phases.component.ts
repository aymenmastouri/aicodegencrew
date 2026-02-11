import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatTableModule } from '@angular/material/table';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatTooltipModule } from '@angular/material/tooltip';

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
  ],
  template: `
    <div class="page-container">
      <h1 class="page-title">Phases</h1>

      <mat-card>
        <mat-card-header>
          <mat-card-title>Phase Configuration</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <table mat-table [dataSource]="phases" class="phase-table">
            <ng-container matColumnDef="order">
              <th mat-header-cell *matHeaderCellDef>#</th>
              <td mat-cell *matCellDef="let p">{{ p.order }}</td>
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
                  <mat-chip>{{ dep | slice:0:20 }}</mat-chip>
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

      <h2>Presets</h2>
      <mat-accordion>
        @for (preset of presets; track preset.name) {
          <mat-expansion-panel>
            <mat-expansion-panel-header>
              <mat-panel-title>{{ preset.name }}</mat-panel-title>
              <mat-panel-description>{{ preset.phases.length }} phases</mat-panel-description>
            </mat-expansion-panel-header>
            <mat-chip-set>
              @for (phase of preset.phases; track phase) {
                <mat-chip>{{ phase }}</mat-chip>
              }
            </mat-chip-set>
            <div style="margin-top: 12px;">
              <button mat-raised-button color="primary" (click)="runPreset(preset.name)">
                <mat-icon>play_arrow</mat-icon>
                Run {{ preset.name }}
              </button>
            </div>
          </mat-expansion-panel>
        }
      </mat-accordion>
    </div>
  `,
  styles: [`
    .phase-table { width: 100%; }
    h2 { margin-top: 32px; margin-bottom: 16px; font-weight: 400; }
  `],
})
export class PhasesComponent implements OnInit {
  phases: PhaseInfo[] = [];
  presets: PresetInfo[] = [];
  pipeline: PipelineStatus | null = null;
  displayedColumns = ['order', 'id', 'name', 'status', 'dependencies', 'actions'];

  constructor(private api: ApiService, private router: Router) {}

  ngOnInit(): void {
    this.api.getPhases().subscribe(p => this.phases = p);
    this.api.getPresets().subscribe(p => this.presets = p);
    this.api.getPipelineStatus().subscribe(p => this.pipeline = p);
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
