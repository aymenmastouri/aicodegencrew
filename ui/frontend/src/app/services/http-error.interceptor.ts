import { Injectable } from '@angular/core';
import {
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest,
  HttpErrorResponse,
} from '@angular/common/http';
import { Observable, throwError, from } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';
import { NotificationService } from './notification.service';
import { AuthService } from './auth.service';

@Injectable()
export class HttpErrorInterceptor implements HttpInterceptor {
  constructor(
    private notif: NotificationService,
    private auth: AuthService,
  ) {}

  intercept(req: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    return next.handle(req).pipe(
      catchError((error: unknown) => {
        if (error instanceof HttpErrorResponse) {
          const status = error.status;
          const detail = (error.error && (error.error.detail || error.error.message)) || error.message;

          // 401: attempt token refresh, then retry once
          if (status === 401) {
            return from(this.auth.refreshToken()).pipe(
              switchMap((refreshed) => {
                if (refreshed) {
                  const token = this.auth.getAccessToken();
                  const retryReq = req.clone({
                    setHeaders: token ? { Authorization: `Bearer ${token}` } : {},
                  });
                  return next.handle(retryReq);
                }
                // Refresh failed — redirect to login
                this.auth.login();
                return throwError(() => error);
              }),
            );
          }

          // Let 0 (network), 4xx, 5xx bubble up as user-visible errors.
          if (status === 0) {
            this.notif.error('Cannot reach backend. Check server/network.');
          } else if (status >= 500) {
            this.notif.error(`Server error (${status}): ${detail}`);
          } else if (status >= 400) {
            this.notif.error(`Request failed (${status}): ${detail}`);
          }
        }
        return throwError(() => error);
      }),
    );
  }
}

