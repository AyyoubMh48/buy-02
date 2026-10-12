import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { Register } from './register';
import { AuthService } from '../../../core/services/auth';
import { Router } from '@angular/router';

describe('Register behaviour', () => {
  let fixture: ComponentFixture<Register>;
  let component: Register;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [Register], providers: [provideRouter([])] }).compileComponents();
    fixture = TestBed.createComponent(Register);
    component = fixture.componentInstance;
  });

  function fill(role: 'CLIENT' | 'SELLER' = 'CLIENT') {
    component.registerForm.patchValue({
      fullName: 'Valid Name',
      email: 'v@example.com',
      password: 'password123',
      role,
    });
  }

  it('toggles password and sets role', () => {
    component.togglePassword();
    expect(component.showPassword()).toBe(true);
    component.setRole('SELLER');
    expect(component.registerForm.value.role).toBe('SELLER');
  });

  it('does not submit an invalid form', () => {
    const auth = TestBed.inject(AuthService);
    const register = vi.spyOn(auth, 'register');
    component.registerForm.patchValue({ fullName: '', email: 'bad', password: '1' });
    component.onSubmit();
    expect(register).not.toHaveBeenCalled();
  });

  it('navigates seller after registration', () => {
    const auth = TestBed.inject(AuthService);
    const router = TestBed.inject(Router);
    vi.spyOn(auth, 'register').mockReturnValue(of({ token: 't', user: { id: '1', email: 'v@example.com', role: 'SELLER' } }));
    const navigate = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    fill('SELLER');
    component.onSubmit();
    expect(navigate).toHaveBeenCalledWith(['/seller/dashboard']);
  });

  it('maps field errors from the backend', () => {
    const auth = TestBed.inject(AuthService);
    vi.spyOn(auth, 'register').mockReturnValue(throwError(() => ({
      error: { fields: { fullName: 'Bad name', email: 'Bad email' } },
    })));
    fill();
    component.onSubmit();
    expect(component.errorMessage()).toContain('Bad name');
    expect(component.errorMessage()).toContain('Bad email');
  });

  it('uses a string error body', () => {
    const auth = TestBed.inject(AuthService);
    vi.spyOn(auth, 'register').mockReturnValue(throwError(() => ({ error: 'plain failure' })));
    fill();
    component.onSubmit();
    expect(component.errorMessage()).toBe('plain failure');
  });

  it.each([
    [409, 'different email'],
    [400, 'check your information'],
    [500, 'try again later'],
  ])('maps status %i to a friendly message', (status, message) => {
    const auth = TestBed.inject(AuthService);
    vi.spyOn(auth, 'register').mockReturnValue(throwError(() => ({ status, error: {} })));
    fill();
    component.onSubmit();
    expect(component.errorMessage()).toContain(message);
  });
});