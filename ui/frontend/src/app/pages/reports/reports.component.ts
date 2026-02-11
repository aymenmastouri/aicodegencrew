import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule } from '@angular/material/tabs';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatChipsModule } from '@angular/material/chips';

import { ApiService, ReportList } from '../../services/api.service';

@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatTabsModule,
    MatExpansionModule,
    MatChipsModule,
  ],
  template: `
    <div class="page-container">
      <h1 class="page-title">Reports</h1>

      <mat-tab-group>
        <mat-tab label="Development Plans ({{ reports?.plans?.length || 0 }})">
          @if (reports?.plans?.length) {
            <mat-accordion>
              @for (plan of reports!.plans; track plan['task_id']) {
                <mat-expansion-panel>
                  <mat-expansion-panel-header>
                    <mat-panel-title>{{ plan['task_id'] }}</mat-panel-title>
                    <mat-panel-description>
                      {{ $any(plan['understanding'])?.['summary'] || 'No summary' }}
                    </mat-panel-description>
                  </mat-expansion-panel-header>
                  <pre class="mono plan-content">{{ plan | json }}</pre>
                </mat-expansion-panel>
              }
            </mat-accordion>
          } @else {
            <p class="empty-state">No development plans found.</p>
          }
        </mat-tab>

        <mat-tab label="Codegen Reports ({{ reports?.codegen_reports?.length || 0 }})">
          @if (reports?.codegen_reports?.length) {
            <mat-accordion>
              @for (report of reports!.codegen_reports; track report['task_id']) {
                <mat-expansion-panel>
                  <mat-expansion-panel-header>
                    <mat-panel-title>{{ report['task_id'] }}</mat-panel-title>
                    <mat-panel-description>
                      <span class="status-chip" [class]="'status-' + report['status']">
                        {{ report['status'] }}
                      </span>
                    </mat-panel-description>
                  </mat-expansion-panel-header>
                  <pre class="mono plan-content">{{ report | json }}</pre>
                </mat-expansion-panel>
              }
            </mat-accordion>
          } @else {
            <p class="empty-state">No codegen reports found.</p>
          }
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
  styles: [`
    .plan-content {
      max-height: 400px;
      overflow: auto;
      background: var(--cg-dark);
      color: #eeffff;
      padding: 16px;
      border-radius: 4px;
      font-size: 12px;
    }
    .empty-state {
      padding: 32px;
      text-align: center;
      color: var(--cg-gray-500);
    }
  `],
})
export class ReportsComponent implements OnInit {
  reports: ReportList | null = null;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getReports().subscribe(r => this.reports = r);
  }
}
