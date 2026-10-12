import { HttpClient, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { switchMap } from 'rxjs';
import { API_BASE_URL } from '../api-config';

export const csrfInterceptor: HttpInterceptorFn = (request, next) => {
  const safeMethod = ['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(request.method);
  const apiRequest = request.url.startsWith(`${API_BASE_URL}/`);
  if (safeMethod || !apiRequest) return next(request);

  return inject(HttpClient).get<{ token: string }>(`${API_BASE_URL}/csrf`).pipe(
    switchMap(({ token }) => next(request.clone({ setHeaders: { 'X-XSRF-TOKEN': token } })))
  );
};
