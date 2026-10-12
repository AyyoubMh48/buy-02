import { TestBed } from '@angular/core/testing';
import { HttpRequest, HttpHandlerFn, HttpErrorResponse } from '@angular/common/http';
import { Router, provideRouter } from '@angular/router';
import { of, throwError, firstValueFrom } from 'rxjs';

import { authGuard } from './guards/auth-guard';
import { roleGuard } from './guards/role-guard';
import { jwtInterceptor } from './interceptors/jwt-interceptor';
import { AuthService } from './services/auth';

describe('guards and interceptor', () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ providers: [provideRouter([])] });
  });

  afterEach(() => localStorage.clear());

  it('authGuard allows a logged-in user', () => {
    localStorage.setItem('buy01_token', 'tok');
    const auth = TestBed.inject(AuthService);
    vi.spyOn(auth, 'isLoggedIn').mockReturnValue(true);
    const result = TestBed.runInInjectionContext(() => authGuard({} as any, {} as any));
    expect(result).toBe(true);
  });

  it('authGuard redirects anonymous users to login', () => {
    const router = TestBed.inject(Router);
    const navigate = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    const result = TestBed.runInInjectionContext(() => authGuard({} as any, {} as any));
    expect(result).toBe(false);
    expect(navigate).toHaveBeenCalledWith(['/login']);
  });

  it('roleGuard allows matching role', () => {
    const auth = TestBed.inject(AuthService);
    vi.spyOn(auth, 'isLoggedIn').mockReturnValue(true);
    vi.spyOn(auth, 'hasRole').mockReturnValue(true);
    const result = TestBed.runInInjectionContext(() => roleGuard('SELLER')({} as any, {} as any));
    expect(result).toBe(true);
  });

  it('roleGuard redirects mismatched role', () => {
    const auth = TestBed.inject(AuthService);
    const router = TestBed.inject(Router);
    vi.spyOn(auth, 'isLoggedIn').mockReturnValue(true);
    vi.spyOn(auth, 'hasRole').mockReturnValue(false);
    const navigate = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    const result = TestBed.runInInjectionContext(() => roleGuard('SELLER')({} as any, {} as any));
    expect(result).toBe(false);
    expect(navigate).toHaveBeenCalledWith(['/products']);
  });

  it('jwtInterceptor attaches bearer token', async () => {
    const auth = TestBed.inject(AuthService);
    vi.spyOn(auth, 'token').mockReturnValue('tok');
    const next = vi.fn((req: HttpRequest<unknown>) => of({} as any));
    const request = new HttpRequest('POST', '/api/products', {});

    await TestBed.runInInjectionContext(() =>
      firstValueFrom(jwtInterceptor(request, next as unknown as HttpHandlerFn)));

    expect(next.mock.calls[0][0].headers.get('Authorization')).toBe('Bearer tok');
  });

  it('jwtInterceptor skips auth for public product reads', async () => {
    const auth = TestBed.inject(AuthService);
    vi.spyOn(auth, 'token').mockReturnValue('tok');
    const next = vi.fn((req: HttpRequest<unknown>) => of({} as any));
    const request = new HttpRequest('GET', 'https://localhost:8443/products');

    await TestBed.runInInjectionContext(() =>
      firstValueFrom(jwtInterceptor(request, next as unknown as HttpHandlerFn)));

    expect(next.mock.calls[0][0].headers.has('Authorization')).toBe(false);
  });

  it('jwtInterceptor logs out on 401', async () => {
    const auth = TestBed.inject(AuthService);
    const router = TestBed.inject(Router);
    const logout = vi.spyOn(auth, 'logout').mockImplementation(() => {});
    const navigate = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    const next = vi.fn(() => throwError(() => new HttpErrorResponse({ status: 401 })));
    const request = new HttpRequest('GET', '/api/products/1');

    await TestBed.runInInjectionContext(() =>
      firstValueFrom(jwtInterceptor(request, next as unknown as HttpHandlerFn)).catch(() => {}));

    expect(logout).toHaveBeenCalled();
    expect(navigate).toHaveBeenCalledWith(['/login']);
  });
});