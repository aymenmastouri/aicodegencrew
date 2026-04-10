import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { APP_INITIALIZER, provideZonelessChangeDetection } from '@angular/core';
import { HTTP_INTERCEPTORS, provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';

import { AppComponent } from './app/app.component';
import { routes } from './app/app.routes';
import { AuthService } from './app/services/auth.service';
import { AuthInterceptor } from './app/services/auth.interceptor';
import { HttpErrorInterceptor } from './app/services/http-error.interceptor';

function initAuth(auth: AuthService) {
  return async () => {
    try {
      const res = await fetch('/api/auth/config');
      const cfg = await res.json();
      if (cfg.enabled) {
        await auth.init({
          authority: cfg.authority,
          clientId: cfg.clientId,
          redirectUri: cfg.redirectUri || window.location.origin,
          scopes: cfg.scopes || 'openid profile email',
          authorizationEndpoint: cfg.authorizationEndpoint,
          endSessionEndpoint: cfg.endSessionEndpoint,
        });
      }
    } catch {
      // Auth config not available — allow unauthenticated access
    }
  };
}

bootstrapApplication(AppComponent, {
  providers: [
    provideZonelessChangeDetection(),
    provideRouter(routes),
    provideHttpClient(withInterceptorsFromDi()),
    provideAnimationsAsync(),
    { provide: APP_INITIALIZER, useFactory: initAuth, deps: [AuthService], multi: true },
    { provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true },
    { provide: HTTP_INTERCEPTORS, useClass: HttpErrorInterceptor, multi: true },
  ],
}).catch((err) => {
  document.body.style.cssText = 'padding:40px;font-family:monospace;color:red;white-space:pre-wrap';
  document.body.textContent = 'BOOTSTRAP ERROR:\n' + (err?.message || err) + '\n\n' + (err?.stack || '');
  console.error('Bootstrap failed:', err);
});
