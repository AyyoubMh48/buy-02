import { FormBuilder } from '@angular/forms';
import { of, throwError } from 'rxjs';

import { UpdateProfileDialog } from './update-profile-dialog';
import { User } from '../../../core/models/user';

const seller: User = { id: 'u2', email: 's@x.com', username: 'seller', role: 'SELLER', avatarUrl: 'https://old' };

function build(profile: any, media: any) {
  return new UpdateProfileDialog(new FormBuilder(), profile, media);
}

describe('UpdateProfileDialog behaviour', () => {
  beforeEach(() => vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:avatar'));
  afterEach(() => vi.restoreAllMocks());

  it('initialises the form and preview', () => {
    const c = build({}, { MAX_FILE_SIZE: 100 });
    c.user = seller;
    c.ngOnInit();
    expect(c.profileForm.value.username).toBe('seller');
    expect(c.avatarPreview()).toBe('https://old');
  });

  it('falls back to fullName when username is missing', () => {
    const c = build({}, { MAX_FILE_SIZE: 100 });
    c.user = { ...seller, username: undefined, fullName: 'Full Name' };
    c.ngOnInit();
    expect(c.profileForm.value.username).toBe('Full Name');
  });

  it('ignores avatar upload for non-sellers', () => {
    const media = { MAX_FILE_SIZE: 100, uploadImage: vi.fn() };
    const c = build({}, media);
    c.user = { ...seller, role: 'CLIENT' };
    c.onAvatarSelect({ target: { files: [new File(['x'], 'p.png', { type: 'image/png' })] } } as unknown as Event);
    expect(media.uploadImage).not.toHaveBeenCalled();
  });

  it('ignores an empty avatar selection', () => {
    const media = { MAX_FILE_SIZE: 100, uploadImage: vi.fn() };
    const c = build({}, media);
    c.user = seller;
    c.onAvatarSelect({ target: { files: [] } } as unknown as Event);
    expect(media.uploadImage).not.toHaveBeenCalled();
  });

  it('rejects non-image avatars', () => {
    const c = build({}, { MAX_FILE_SIZE: 100, uploadImage: vi.fn() });
    c.user = seller;
    c.onAvatarSelect({ target: { files: [new File(['x'], 'a.txt', { type: 'text/plain' })] } } as unknown as Event);
    expect(c.errorMessage()).toContain('image file');
  });

  it('rejects oversized avatars', () => {
    const c = build({}, { MAX_FILE_SIZE: 1, uploadImage: vi.fn() });
    c.user = seller;
    c.onAvatarSelect({ target: { files: [new File(['xx'], 'p.png', { type: 'image/png' })] } } as unknown as Event);
    expect(c.errorMessage()).toContain('2 MB');
  });

  it('uploads a seller avatar', () => {
    const media = { MAX_FILE_SIZE: 100, uploadImage: vi.fn(() => of({ id: 'm1', url: 'https://new' })) };
    const c = build({}, media);
    c.user = seller;
    c.onAvatarSelect({ target: { files: [new File(['x'], 'p.png', { type: 'image/png' })] } } as unknown as Event);
    expect(c.avatarMediaId()).toBe('m1');
    expect(c.avatarPreview()).toBe('https://new');
  });

  it('reports avatar upload errors', () => {
    const media = { MAX_FILE_SIZE: 100, uploadImage: vi.fn(() => throwError(() => ({ error: { message: 'no' } }))) };
    const c = build({}, media);
    c.user = seller;
    c.onAvatarSelect({ target: { files: [new File(['x'], 'p.png', { type: 'image/png' })] } } as unknown as Event);
    expect(c.errorMessage()).toBe('no');
  });

  it('does not submit an invalid form', () => {
    const profile = { updateProfile: vi.fn() };
    const c = build(profile, { MAX_FILE_SIZE: 100 });
    c.user = seller;
    c.ngOnInit();
    c.profileForm.patchValue({ username: '' });
    c.onSubmit();
    expect(profile.updateProfile).not.toHaveBeenCalled();
  });

  it('submits for a seller including the avatar media id', () => {
    const profile = { updateProfile: vi.fn(() => of({ ...seller, username: 'updated' })) };
    const c = build(profile, { MAX_FILE_SIZE: 100 });
    c.user = seller;
    c.ngOnInit();
    c.avatarMediaId.set('m1');
    const saved = vi.spyOn(c.saved, 'emit');
    c.onSubmit();
    expect(profile.updateProfile).toHaveBeenCalledWith({ username: 'seller', avatarUrl: 'm1' });
    expect(saved).toHaveBeenCalled();
  });

  it('submits for a client without an avatar id', () => {
    const profile = { updateProfile: vi.fn(() => of({ ...seller, role: 'CLIENT' })) };
    const c = build(profile, { MAX_FILE_SIZE: 100 });
    c.user = { ...seller, role: 'CLIENT' };
    c.ngOnInit();
    c.onSubmit();
    expect(profile.updateProfile).toHaveBeenCalledWith({ username: 'seller' });
  });

  it('maps validation field errors on submit failure', () => {
    const profile = { updateProfile: vi.fn(() => throwError(() => ({ error: { fields: { username: 'too short' } } }))) };
    const c = build(profile, { MAX_FILE_SIZE: 100 });
    c.user = seller;
    c.ngOnInit();
    c.onSubmit();
    expect(c.errorMessage()).toContain('too short');
  });

  it('falls back when no field or message error exists', () => {
    const profile = { updateProfile: vi.fn(() => throwError(() => ({ error: {} }))) };
    const c = build(profile, { MAX_FILE_SIZE: 100 });
    c.user = seller;
    c.ngOnInit();
    c.onSubmit();
    expect(c.errorMessage()).toContain('Profile update failed');
  });

  it('emits closed when idle', () => {
    const c = build({}, { MAX_FILE_SIZE: 100 });
    const closed = vi.spyOn(c.closed, 'emit');
    c.close();
    expect(closed).toHaveBeenCalled();
  });

  it('does not close while saving', () => {
    const c = build({}, { MAX_FILE_SIZE: 100 });
    c.saving.set(true);
    const closed = vi.spyOn(c.closed, 'emit');
    c.close();
    expect(closed).not.toHaveBeenCalled();
  });
});