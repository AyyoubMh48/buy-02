import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { Login } from './login';
import { AuthService } from '../../../core/services/auth';
import { Router } from '@angular/router';

describe('Login behaviour', () => {
  let fixture: ComponentFixture<Login>;
  let component: Login;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [Login], providers: [provideRouter([])] }).compileComponents();
    fixture = TestBed.createComponent(Login);
    component = fixture.componentInstance;
  });

  function fill(email = 'a@b.com', password = 'secret') {
    component.loginForm.setValue({ email, password });
  }

  it('toggles password visibility', () => {
    expect(component.showPassword()).toBe(false);
    component.togglePassword();
    expect(component.showPassword()).toBe(true);
  });

  it('does not submit an invalid form', () => {
    const auth = TestBed.inject(AuthService);
    const login = vi.spyOn(auth, 'login');
    fill('', '');
    component.onSubmit();
    expect(login).not.toHaveBeenCalled();
    expect(component.loginForm.touched).toBe(true);
  });

  it('navigates sellers to the dashboard', () => {
    const auth = TestBed.inject(AuthService);
    const router = TestBed.inject(Router);
    vi.spyOn(auth, 'login').mockReturnValue(of({ token: 't', user: { id: '1', email: 'a@b.com', role: 'SELLER' } }));
    const navigate = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    fill();
    component.onSubmit();
    expect(navigate).toHaveBeenCalledWith(['/seller/dashboard']);
  });

  it('navigates clients to products', () => {
    const auth = TestBed.inject(AuthService);
    const router = TestBed.inject(Router);
    vi.spyOn(auth, 'login').mockReturnValue(of({ token: 't', user: { id: '1', email: 'a@b.com', role: 'CLIENT' } }));
    const navigate = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    fill();
    component.onSubmit();
    expect(navigate).toHaveBeenCalledWith(['/products']);
  });

  it('shows backend error message on failure', () => {
    const auth = TestBed.inject(AuthService);
    vi.spyOn(auth, 'login').mockReturnValue(throwError(() => ({ error: { message: 'Bad creds' } })));
    fill();
    component.onSubmit();
    expect(component.errorMessage()).toBe('Bad creds');
    expect(component.loading()).toBe(false);
  });

  it('falls back to a generic error message', () => {
    const auth = TestBed.inject(AuthService);
    vi.spyOn(auth, 'login').mockReturnValue(throwError(() => ({})));
    fill();
    component.onSubmit();
    expect(component.errorMessage()).toContain('Invalid email or password');
  });
});