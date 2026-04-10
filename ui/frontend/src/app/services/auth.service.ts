/**
 * OIDC Authentication Service for Authentik integration.
 *
 * Handles login redirect, token storage, token refresh, and logout.
 * When OIDC is not configured, all methods are no-ops and isAuthenticated() returns true.
 */
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

interface OIDCConfig {
  authority: string;
  clientId: string;
  redirectUri: string;
  scopes: string;
  authorizationEndpoint?: string;
  tokenEndpoint?: string;
  endSessionEndpoint?: string;
}

interface UserInfo {
  sub: string;
  email: string;
  name: string;
  groups: string[];
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private config: OIDCConfig | null = null;
  private _isAuthenticated = new BehaviorSubject<boolean>(true);
  private _user = new BehaviorSubject<UserInfo | null>(null);

  readonly isAuthenticated$: Observable<boolean> = this._isAuthenticated.asObservable();
  readonly user$: Observable<UserInfo | null> = this._user.asObservable();

  /**
   * Initialize OIDC from environment/config.
   * Call this from app initialization (e.g., APP_INITIALIZER).
   */
  async init(config?: OIDCConfig): Promise<void> {
    if (!config || !config.authority) {
      // No OIDC configured — allow unauthenticated access
      this._isAuthenticated.next(true);
      return;
    }

    // Endpoints are provided by /api/auth/config (server-side discovery)
    this.config = config;

    // Check for existing token
    const token = this.getAccessToken();
    if (token && !this.isTokenExpired(token)) {
      this._isAuthenticated.next(true);
      await this.loadUserInfo();
      return;
    }

    // Check for authorization code in URL (redirect callback)
    const code = new URLSearchParams(window.location.search).get('code');
    if (code) {
      await this.handleCallback(code);
      // Clean up URL
      window.history.replaceState({}, '', window.location.pathname);
      return;
    }

    this._isAuthenticated.next(false);
  }

  isAuthenticated(): boolean {
    return this._isAuthenticated.value;
  }

  getAccessToken(): string | null {
    return sessionStorage.getItem('oidc_access_token');
  }

  login(): void {
    if (!this.config) return;

    const state = this.generateState();
    sessionStorage.setItem('oidc_state', state);

    const params = new URLSearchParams({
      response_type: 'code',
      client_id: this.config.clientId,
      redirect_uri: this.config.redirectUri,
      scope: this.config.scopes,
      state: state,
    });

    const authUrl = this.config.authorizationEndpoint || `${this.config.authority}/authorize`;
    window.location.href = `${authUrl}?${params.toString()}`;
  }

  logout(): void {
    sessionStorage.removeItem('oidc_access_token');
    sessionStorage.removeItem('oidc_refresh_token');
    sessionStorage.removeItem('oidc_state');
    this._isAuthenticated.next(false);
    this._user.next(null);

    if (this.config) {
      const endSessionUrl = this.config.endSessionEndpoint || `${this.config.authority}/end-session`;
      window.location.href = `${endSessionUrl}?post_logout_redirect_uri=${encodeURIComponent(this.config.redirectUri)}`;
    }
  }

  private async handleCallback(code: string): Promise<void> {
    if (!this.config) return;

    try {
      // Exchange code via backend proxy (avoids CORS issues)
      const response = await fetch('/api/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          grant_type: 'authorization_code',
          code: code,
          redirect_uri: this.config.redirectUri,
        }),
      });

      if (!response.ok) throw new Error(`Token exchange failed: ${response.status}`);

      const data = await response.json();
      sessionStorage.setItem('oidc_access_token', data.access_token);
      if (data.refresh_token) {
        sessionStorage.setItem('oidc_refresh_token', data.refresh_token);
      }

      this._isAuthenticated.next(true);
      await this.loadUserInfo();
    } catch (error) {
      console.error('[Auth] Token exchange failed:', error);
      this._isAuthenticated.next(false);
    }
  }

  async refreshToken(): Promise<boolean> {
    if (!this.config) return false;

    const refreshToken = sessionStorage.getItem('oidc_refresh_token');
    if (!refreshToken) return false;

    try {
      const response = await fetch('/api/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          grant_type: 'refresh_token',
          refresh_token: refreshToken,
        }),
      });

      if (!response.ok) return false;

      const data = await response.json();
      sessionStorage.setItem('oidc_access_token', data.access_token);
      if (data.refresh_token) {
        sessionStorage.setItem('oidc_refresh_token', data.refresh_token);
      }

      this._isAuthenticated.next(true);
      return true;
    } catch {
      return false;
    }
  }

  private async loadUserInfo(): Promise<void> {
    const token = this.getAccessToken();
    if (!token) return;

    try {
      const response = await fetch('/api/auth/userinfo', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        this._user.next(await response.json());
      }
    } catch {
      // Non-critical — user info display is optional
    }
  }

  private isTokenExpired(token: string): boolean {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.exp * 1000 < Date.now();
    } catch {
      return true;
    }
  }

  private generateState(): string {
    const array = new Uint8Array(16);
    crypto.getRandomValues(array);
    return Array.from(array, (b) => b.toString(16).padStart(2, '0')).join('');
  }
}
