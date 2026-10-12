import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './login.html',
  styleUrl: './login.css',
})
export class Login {
  loginForm: FormGroup;
  readonly loading = signal<boolean>(false);
  readonly errorMessage = signal<string>('');
  readonly showPassword = signal<boolean>(false);

  constructor(
    private readonly fb: FormBuilder,
    private readonly auth: AuthService,
    private readonly router: Router
  ) {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required]]
    });
  }

  togglePassword(): void {
    this.showPassword.update(v => !v);
  }

  onSubmit(): void {
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.loading.set(true);
    this.errorMessage.set('');

    this.auth.login(this.loginForm.value).subscribe({
      next: (res) => {
        const dest = res.user.role === 'SELLER' ? '/seller/dashboard' : '/products';
        this.router.navigate([dest]);
      },
      error: (err) => {
        this.errorMessage.set(err.error?.message || 'Invalid email or password. Please verify your credentials.');
        this.loading.set(false);
      }
    });
  }
}