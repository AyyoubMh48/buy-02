import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth';
import { MediaService } from '../../../core/services/media';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './register.html',
  styleUrl: './register.css',
})
export class Register {
  registerForm: FormGroup;
  loading = signal<boolean>(false);
  uploadingAvatar = signal<boolean>(false);
  errorMessage = signal<string>('');
  showPassword = signal<boolean>(false);
  avatarPreview = signal<string>('');

  constructor(
    private fb: FormBuilder,
    private auth: AuthService,
    private mediaService: MediaService,
    private router: Router
  ) {
    this.registerForm = this.fb.group({
      fullName: [
        '',
        [
          Validators.required,
          Validators.minLength(2),
          Validators.maxLength(50),
          Validators.pattern(/^[\p{L}0-9_.'\- @]+$/u)
        ]
      ],
      email: ['', [Validators.required, Validators.email, Validators.maxLength(254)]],
      password: ['', [Validators.required, Validators.minLength(6), Validators.maxLength(72)]],
      role: ['CLIENT', Validators.required],
      avatarUrl: ['']
    });
  }

  togglePassword(): void {
    this.showPassword.update(v => !v);
  }

  setRole(role: 'CLIENT' | 'SELLER'): void {
    this.registerForm.patchValue({ role });
  }

  // onAvatarSelect(event: Event): void {
  //   const file = (event.target as HTMLInputElement).files?.[0];
  //   if (!file) return;
  // 
  //   if (file.size > this.mediaService.MAX_FILE_SIZE) {
  //     this.errorMessage.set('Avatar image exceeds 2 MB limit.');
  //     return;
  //   }
  // 
  //   const localUrl = URL.createObjectURL(file);
  //   this.avatarPreview.set(localUrl);
  // 
  //   this.uploadingAvatar.set(true);
  //   this.errorMessage.set('');
  // 
  //   this.mediaService.uploadImage(file).subscribe({
  //     next: (res) => {
  //       this.registerForm.patchValue({ avatarUrl: res.url });
  //       this.avatarPreview.set(res.url);
  //       this.uploadingAvatar.set(false);
  //     },
  //     error: (err) => {
  //       this.errorMessage.set(err.message || 'Avatar upload failed.');
  //       this.uploadingAvatar.set(false);
  //     }
  //   });
  // }

  onSubmit(): void {
    if (this.registerForm.invalid) {
      this.registerForm.markAllAsTouched();
      return;
    }

    this.loading.set(true);
    this.errorMessage.set('');

    const payload = {
      ...this.registerForm.value,
      username: this.registerForm.value.fullName
    };

    this.auth.register(payload).subscribe({
      next: (res) => {
        const role = res.user?.role || this.registerForm.value.role;
        const dest = role === 'SELLER' ? '/seller/dashboard' : '/products';
        this.router.navigate([dest]);
      },
      error: (err) => {
        let msg = '';
        if (err.error?.fields && typeof err.error.fields === 'object') {
          const fieldMap = err.error.fields as Record<string, string>;
          const fieldErrors: string[] = [];
          if (fieldMap['fullName']) {
            fieldErrors.push(fieldMap['fullName']);
          }
          for (const [key, val] of Object.entries(fieldMap)) {
            if (key !== 'fullName' && key !== 'username' && val) {
              fieldErrors.push(val);
            }
          }
          if (fieldErrors.length === 0 && fieldMap['username']) {
            fieldErrors.push(fieldMap['username']);
          }
          msg = Array.from(new Set(fieldErrors)).join('. ');
        }

        if (!msg && err.error?.message) {
          msg = err.error.message;
        }

        if (!msg && typeof err.error === 'string') {
          msg = err.error;
        }

        if (!msg) {
          if (err.status === 409) {
            msg = 'Registration failed. Please try a different email.';
          } else if (err.status === 400) {
            msg = 'Registration failed. Please check your information and try again.';
          } else {
            msg = 'Registration failed. Please try again later.';
          }
        }

        this.errorMessage.set(msg);
        this.loading.set(false);
      }
    });
  }
}
