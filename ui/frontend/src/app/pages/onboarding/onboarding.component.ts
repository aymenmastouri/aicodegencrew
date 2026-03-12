import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatListModule } from '@angular/material/list';

import { ApiService, SetupStatus } from '../../services/api.service';

@Component({
  selector: 'app-onboarding',
  standalone: true,
  imports: [CommonModule, RouterLink, MatCardModule, MatIconModule, MatButtonModule, MatListModule],
  template: `
    <div class="page-container">
      <div class="page-header">
        <mat-icon class="page-icon">playlist_add_check</mat-icon>
        <div>
          <h1 class="page-title">Onboarding Checklist</h1>
          <p class="page-subtitle">Prüfe, ob Repo, LLM und Inputs korrekt konfiguriert sind.</p>
        </div>
      </div>

      <mat-card>
        <mat-card-content>
          <mat-list>
            <mat-list-item>
              <mat-icon matListIcon [ngClass]="setup?.repo_configured ? 'ok' : 'missing'">
                {{ setup?.repo_configured ? 'check_circle' : 'error' }}
              </mat-icon>
              <div matLine>Repository konfiguriert</div>
              <div matLine class="hint">PROJECT_PATH zeigt auf ein existierendes Verzeichnis.</div>
            </mat-list-item>

            <mat-list-item>
              <mat-icon matListIcon [ngClass]="setup?.llm_configured ? 'ok' : 'missing'">
                {{ setup?.llm_configured ? 'check_circle' : 'error' }}
              </mat-icon>
              <div matLine>LLM-Konfiguration</div>
              <div matLine class="hint">LLM_PROVIDER, MODEL und API_BASE sind gesetzt.</div>
            </mat-list-item>

            <mat-list-item>
              <mat-icon matListIcon [ngClass]="setup?.has_input_files ? 'ok' : 'missing'">
                {{ setup?.has_input_files ? 'check_circle' : 'warning' }}
              </mat-icon>
              <div matLine>Input-Files vorhanden</div>
              <div matLine class="hint">TASK_INPUT_DIR enthält mindestens eine Datei.</div>
            </mat-list-item>

            <mat-list-item>
              <mat-icon matListIcon [ngClass]="setup?.has_run_history ? 'ok' : 'missing'">
                {{ setup?.has_run_history ? 'check_circle' : 'info' }}
              </mat-icon>
              <div matLine>Run-History</div>
              <div matLine class="hint">Es existiert mindestens ein abgeschlossener Run.</div>
            </mat-list-item>
          </mat-list>

          <div *ngIf="errors.length" class="error-box">
            <h3><mat-icon>error_outline</mat-icon> Offene Punkte</h3>
            <ul>
              <li *ngFor="let e of errors">{{ e }}</li>
            </ul>
          </div>
        </mat-card-content>
        <mat-card-actions>
          <button mat-stroked-button color="primary" routerLink="/env">
            <mat-icon>settings</mat-icon>
            Edit .env
          </button>
          <button mat-stroked-button routerLink="/inputs">
            <mat-icon>upload_file</mat-icon>
            Manage Input Files
          </button>
          <span class="flex-1"></span>
          <button mat-flat-button color="primary" routerLink="/run">
            <mat-icon>rocket_launch</mat-icon>
            Run Pipeline
          </button>
        </mat-card-actions>
      </mat-card>
    </div>
  `,
  styles: [
    `
      .hint {
        font-size: 12px;
        color: var(--cg-gray-500);
      }
      .ok {
        color: var(--cg-success);
      }
      .missing {
        color: var(--cg-error);
      }
      .error-box {
        margin-top: 16px;
        padding: 12px 16px;
        border-radius: 8px;
        background: rgba(220, 53, 69, 0.06);
        color: var(--cg-error);
        font-size: 13px;
      }
      .error-box h3 {
        display: flex;
        align-items: center;
        gap: 6px;
        margin: 0 0 6px;
        font-size: 14px;
      }
    `,
  ],
})
export class OnboardingComponent implements OnInit {
  setup: (SetupStatus & { errors?: string[] }) | null = null;
  errors: string[] = [];

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getSetupStatus().subscribe({
      next: (s: any) => {
        this.setup = s;
        this.errors = (s.errors as string[]) || [];
      },
    });
  }
}

