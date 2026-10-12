import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth';

export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const token = authService.token();
  const isPublicProductRead =
    req.method === 'GET' &&
    /^https:\/\/localhost:8443\/products(?:\/(?!myProducts(?:[/?]|$))[^/?]+)?(?:\?.*)?$/.test(req.url);

  const isCsrfRequest = req.method === 'GET' && req.url.endsWith('/csrf');
  if (token && !isPublicProductRead && !isCsrfRequest) {
    req = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
  }

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      // If unauthorized and not attempting to login/register, clear session and redirect to login
      if (error.status === 401 && !req.url.includes('/auth/login') && !req.url.includes('/auth/register')) {
        authService.logout();
        router.navigate(['/login']);
      }
      return throwError(() => error);
    })
  );
};
