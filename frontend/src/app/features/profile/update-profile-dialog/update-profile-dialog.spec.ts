import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { UpdateProfileDialog } from './update-profile-dialog';
import { MediaService } from '../../../core/services/media';
import { User } from '../../../core/models/user';

describe('UpdateProfileDialog', () => {
  let component: UpdateProfileDialog;
  let fixture: ComponentFixture<UpdateProfileDialog>;
  let mediaService: MediaService;

  const clientUser: User = {
    id: 'user1',
    email: 'client@example.com',
    fullName: 'Client User',
    username: 'client_user',
    role: 'CLIENT',
    avatarUrl: 'https://example.com/avatar.jpg',
  };

  const sellerUser: User = {
    id: 'user2',
    email: 'seller@example.com',
    fullName: 'Seller User',
    username: 'seller_user',
    role: 'SELLER',
    avatarUrl: 'https://example.com/seller-avatar.jpg',
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UpdateProfileDialog],
      providers: [provideHttpClient(), provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(UpdateProfileDialog);
    component = fixture.componentInstance;
    mediaService = TestBed.inject(MediaService);
  });

  it('should create', () => {
    component.user = clientUser;
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it('should hide avatar upload row when user is CLIENT', () => {
    component.user = clientUser;
    fixture.detectChanges();

    const avatarRow = fixture.nativeElement.querySelector('.profile-dialog-avatar-row');
    expect(avatarRow).toBeNull();
  });

  it('should show avatar upload row when user is SELLER', () => {
    component.user = sellerUser;
    fixture.detectChanges();

    const avatarRow = fixture.nativeElement.querySelector('.profile-dialog-avatar-row');
    expect(avatarRow).not.toBeNull();
  });

  it('should not upload avatar if user is CLIENT even if onAvatarSelect is triggered', () => {
    component.user = clientUser;
    fixture.detectChanges();

    const uploadSpy = vi.spyOn(mediaService, 'uploadImage');
    const fakeEvent = {
      target: {
        files: [new File(['dummy'], 'test.png', { type: 'image/png' })],
      },
    } as unknown as Event;

    component.onAvatarSelect(fakeEvent);

    expect(uploadSpy).not.toHaveBeenCalled();
  });
});

