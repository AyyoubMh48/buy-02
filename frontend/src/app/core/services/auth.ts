import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { AuthResponse, RegisterRequest, User } from '../models/user';
import { API_BASE_URL } from '../api-config';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly API_URL = `${API_BASE_URL}/auth`;
  
  currentUser = signal<User | null>(this.getUserFromStorage());
  token = signal<string | null>(localStorage.getItem('buy01_token'));

  constructor(private http: HttpClient, private router: Router) {}

  login(credentials: { email: string; password: string }): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.API_URL}/login`, credentials).pipe(
      tap(res => this.handleAuthSuccess(res))
    );
  }

  register(data: RegisterRequest): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.API_URL}/register`, data).pipe(
      tap(res => this.handleAuthSuccess(res))
    );
  }

  logout(): void {
    localStorage.removeItem('buy01_token');
    localStorage.removeItem('buy01_user');
    this.currentUser.set(null);
    this.token.set(null);
    this.router.navigate(['/login']);
  }

  isLoggedIn(): boolean {
    return !!this.token();
  }

  hasRole(role: string): boolean {
    return this.currentUser()?.role === role;
  }

  updateCurrentUser(user: User): void {
    const currentUser = this.currentUser();
    const updatedUser = { ...currentUser, ...user };
    localStorage.setItem('buy01_user', JSON.stringify(updatedUser));
    this.currentUser.set(updatedUser);
  }

  private handleAuthSuccess(res: AuthResponse): void {
    localStorage.setItem('buy01_token', res.token);
    localStorage.setItem('buy01_user', JSON.stringify(res.user));
    this.token.set(res.token);
    this.currentUser.set(res.user);
  }

  private getUserFromStorage(): User | null {
    const raw = localStorage.getItem('buy01_user');
    return raw ? JSON.parse(raw) : null;
  }
}
