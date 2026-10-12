import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { Navbar } from './navbar';
import { AuthService } from '../../core/services/auth';

describe('Navbar behaviour', () => {
  let component: Navbar;
  let auth: AuthService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    auth = TestBed.inject(AuthService);
    component = new Navbar(auth);
  });

  it('toggles and closes the mobile menu', () => {
    expect(component.mobileMenuOpen()).toBe(false);
    component.toggleMenu();
    expect(component.mobileMenuOpen()).toBe(true);
    component.closeMenu();
    expect(component.mobileMenuOpen()).toBe(false);
  });

  it('builds initials from a full name', () => {
    expect(component.getUserInitials('Ada Lovelace')).toBe('AL');
  });

  it('builds initials from a username', () => {
    expect(component.getUserInitials(undefined, 'neo')).toBe('NE');
  });

  it('defaults to a generic user', () => {
    expect(component.getUserInitials()).toBe('US');
  });
});