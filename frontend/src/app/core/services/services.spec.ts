import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

import { AuthService } from './auth';
import { MediaService } from './media';
import { ProductService } from './product';
import { ProfileService } from './profile';

describe('core services', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
    localStorage.clear();
  });

  describe('AuthService', () => {
    it('login stores token and user', () => {
      const service = TestBed.inject(AuthService);
      const response = { token: 'tok', user: { id: '1', email: 'a@b.c', role: 'CLIENT' as const } };

      service.login({ email: 'a@b.c', password: 'x' }).subscribe();
      http.expectOne('/api/auth/login').flush(response);

      expect(service.isLoggedIn()).toBe(true);
      expect(service.token()).toBe('tok');
      expect(service.currentUser()?.id).toBe('1');
    });

    it('register stores session', () => {
      const service = TestBed.inject(AuthService);
      const response = { token: 'tok2', user: { id: '2', email: 'c@d.e', role: 'SELLER' as const } };

      service.register({ email: 'c@d.e', password: 'secret', fullName: 'A', role: 'SELLER' }).subscribe();
      http.expectOne('/api/auth/register').flush(response);

      expect(service.hasRole('SELLER')).toBe(true);
    });

    it('logout clears storage and session', () => {
      const service = TestBed.inject(AuthService);
      service.login({ email: 'a@b.c', password: 'x' }).subscribe();
      http.expectOne('/api/auth/login').flush({ token: 'tok', user: { id: '1', email: 'a@b.c', role: 'CLIENT' } });

      service.logout();

      expect(service.token()).toBeNull();
      expect(service.currentUser()).toBeNull();
      expect(localStorage.getItem('buy01_token')).toBeNull();
    });

    it('hasRole is false when no user', () => {
      const service = TestBed.inject(AuthService);
      expect(service.hasRole('CLIENT')).toBe(false);
    });

    it('updateCurrentUser merges and persists', () => {
      const service = TestBed.inject(AuthService);
      service.login({ email: 'a@b.c', password: 'x' }).subscribe();
      http.expectOne('/api/auth/login').flush({ token: 'tok', user: { id: '1', email: 'a@b.c', role: 'CLIENT' } });

      service.updateCurrentUser({ id: '1', email: 'a@b.c', role: 'CLIENT', username: 'neo' });

      expect(service.currentUser()?.username).toBe('neo');
      expect(JSON.parse(localStorage.getItem('buy01_user')!).username).toBe('neo');
    });

    it('reads an existing session from storage', () => {
      localStorage.setItem('buy01_token', 'stored');
      localStorage.setItem('buy01_user', JSON.stringify({ id: '9', email: 's@t.u', role: 'SELLER' }));
      const service = TestBed.inject(AuthService);

      expect(service.token()).toBe('stored');
      expect(service.currentUser()?.id).toBe('9');
    });
  });

  describe('MediaService', () => {
    it('uploadImage posts multipart for valid image', () => {
      const service = TestBed.inject(MediaService);
      const file = new File(['x'], 'p.png', { type: 'image/png' });

      service.uploadImage(file).subscribe();
      const req = http.expectOne('/api/media/images');
      expect(req.request.method).toBe('POST');
      req.flush({ id: 'm1', url: 'u', filename: 'p.png', contentType: 'image/png', size: 1 });
    });

    it('uploadImage rejects non-image', () => {
      const service = TestBed.inject(MediaService);
      let error: Error | undefined;
      service.uploadImage(new File(['x'], 'a.txt', { type: 'text/plain' })).subscribe({ error: e => (error = e) });
      expect(error?.message).toContain('image');
    });

    it('uploadImage rejects oversized file', () => {
      const service = TestBed.inject(MediaService);
      const big = new File([new ArrayBuffer(service.MAX_FILE_SIZE + 1)], 'big.png', { type: 'image/png' });
      let error: Error | undefined;
      service.uploadImage(big).subscribe({ error: e => (error = e) });
      expect(error?.message).toContain('2 MB');
    });

    it('deleteImage and getImageUrl', () => {
      const service = TestBed.inject(MediaService);
      service.deleteImage('m1').subscribe();
      http.expectOne('/api/media/images/m1').flush(null);
      expect(service.getImageUrl('m1')).toBe('/api/media/images/m1');
    });
  });

  describe('ProductService', () => {
    it('calls all product endpoints', () => {
      const service = TestBed.inject(ProductService);
      service.getProducts().subscribe();
      http.expectOne('/api/products').flush([]);
      service.getMyProducts().subscribe();
      http.expectOne('/api/products/myProducts').flush([]);
      service.getProductById('1').subscribe();
      http.expectOne('/api/products/1').flush({});
      const product = { name: 'n', description: 'd', price: 1, quantity: 1 } as any;
      service.createProduct(product).subscribe();
      http.expectOne('/api/products').flush(product);
      service.updateProduct('1', product).subscribe();
      http.expectOne('/api/products/1').flush(product);
      service.deleteProduct('1').subscribe();
      http.expectOne('/api/products/1').flush(null);
    });
  });

  describe('ProfileService', () => {
    it('getProfile and updateProfile', () => {
      const service = TestBed.inject(ProfileService);
      service.getProfile().subscribe();
      http.expectOne('/api/me').flush({});
      service.updateProfile({ username: 'neo' }).subscribe();
      const req = http.expectOne('/api/me');
      expect(req.request.method).toBe('PUT');
      req.flush({});
    });
  });
});