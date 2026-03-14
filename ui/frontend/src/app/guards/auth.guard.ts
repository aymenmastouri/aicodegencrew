/**
 * Route guard that redirects to OIDC login when authentication is required.
 *
 * When OIDC is not configured, the guard always allows access.
 */
import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {
  constructor(
    private auth: AuthService,
    private router: Router,
  ) {}

  canActivate(): boolean {
    if (this.auth.isAuthenticated()) {
      return true;
    }

    // Trigger OIDC login redirect
    this.auth.login();
    return false;
  }
}
