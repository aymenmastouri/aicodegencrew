import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideZonelessChangeDetection } from '@angular/core';

import { AppComponent } from './app/app.component';
import { routes } from './app/app.routes';

bootstrapApplication(AppComponent, {
  providers: [
    provideZonelessChangeDetection(),
    provideRouter(routes),
    provideHttpClient(),
    provideAnimationsAsync(),
  ],
}).catch(err => {
  document.body.style.cssText = 'padding:40px;font-family:monospace;color:red;white-space:pre-wrap';
  document.body.textContent = 'BOOTSTRAP ERROR:\n' + (err?.message || err) + '\n\n' + (err?.stack || '');
  console.error('Bootstrap failed:', err);
});
