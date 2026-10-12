import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { csrfInterceptor } from './csrf-interceptor';

describe('CSRF protection', () => {
  let client: HttpClient;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [
      provideHttpClient(withInterceptors([csrfInterceptor])), provideHttpClientTesting(),
    ] });
    client = TestBed.inject(HttpClient);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it.each(['POST', 'PUT', 'PATCH', 'DELETE'])('gets a token before an API %s', method => {
    client.request(method, '/api/products', { body: {} }).subscribe();
    http.expectNone('/api/products');
    const token = http.expectOne('/api/csrf');
    expect(token.request.method).toBe('GET');
    token.flush({ token: 'csrf-token' });
    const write = http.expectOne('/api/products');
    expect(write.request.headers.get('X-XSRF-TOKEN')).toBe('csrf-token');
    write.flush({});
  });

  it.each(['GET', 'HEAD', 'OPTIONS', 'TRACE'])('does not fetch a token for %s', method => {
    client.request(method, '/api/products').subscribe();
    http.expectNone('/api/csrf');
    http.expectOne('/api/products').flush({});
  });

  it('does not send a token to an external service', () => {
    client.post('https://external.example/products', {}).subscribe();
    http.expectNone('/api/csrf');
    const request = http.expectOne('https://external.example/products');
    expect(request.request.headers.has('X-XSRF-TOKEN')).toBe(false);
    request.flush({});
  });

  it('does not perform a write if token acquisition fails', () => {
    const error = vi.fn();
    client.post('/api/products', {}).subscribe({ error });
    http.expectOne('/api/csrf').flush({}, { status: 503, statusText: 'Unavailable' });
    http.expectNone('/api/products');
    expect(error).toHaveBeenCalledTimes(1);
  });
});
