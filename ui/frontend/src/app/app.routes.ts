import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./pages/dashboard/dashboard.component').then(m => m.DashboardComponent),
  },
  {
    path: 'run',
    loadComponent: () =>
      import('./pages/run-pipeline/run-pipeline.component').then(m => m.RunPipelineComponent),
  },
  {
    path: 'inputs',
    loadComponent: () =>
      import('./pages/input-files/input-files.component').then(m => m.InputFilesComponent),
  },
  {
    path: 'phases',
    loadComponent: () =>
      import('./pages/phases/phases.component').then(m => m.PhasesComponent),
  },
  {
    path: 'knowledge',
    loadComponent: () =>
      import('./pages/knowledge/knowledge.component').then(m => m.KnowledgeComponent),
  },
  {
    path: 'reports',
    loadComponent: () =>
      import('./pages/reports/reports.component').then(m => m.ReportsComponent),
  },
  {
    path: 'metrics',
    loadComponent: () =>
      import('./pages/metrics/metrics.component').then(m => m.MetricsComponent),
  },
  {
    path: 'logs',
    loadComponent: () =>
      import('./pages/logs/logs.component').then(m => m.LogsComponent),
  },
];
