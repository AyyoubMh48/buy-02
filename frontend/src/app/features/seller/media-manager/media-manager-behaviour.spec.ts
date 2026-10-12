import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { MediaManager } from './media-manager';
import { MediaService } from '../../../core/services/media';
import { ProductService } from '../../../core/services/product';

describe('MediaManager behaviour', () => {
  let mediaMock: any;
  let productMock: any;
  let component: MediaManager;

  beforeEach(() => {
    mediaMock = {
      MAX_FILE_SIZE: 2097152,
      uploadImage: vi.fn(() => of({ id: 'm1', url: 'https://u', filename: 'p.png', size: 3 })),
    };
    productMock = {
      getProducts: vi.fn(() => of([
        { id: '1', name: 'Chair', description: '', price: 1, quantity: 1, images: ['https://a/x.png'] },
      ])),
    };
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:preview');
    TestBed.configureTestingModule({
      providers: [
        { provide: MediaService, useValue: mediaMock },
        { provide: ProductService, useValue: productMock },
      ],
    });
    component = TestBed.runInInjectionContext(
      () => new MediaManager(TestBed.inject(MediaService), TestBed.inject(ProductService)));
  });

  afterEach(() => vi.restoreAllMocks());

  it('loads existing catalog media', () => {
    component.ngOnInit();
    expect(component.mediaList().length).toBe(1);
    expect(component.mediaList()[0].filename).toBe('x.png');
  });

  it('handles load failure silently', () => {
    productMock.getProducts.mockReturnValue(throwError(() => new Error('x')));
    component.loadExistingCatalogMedia();
    expect(component.mediaList().length).toBe(0);
  });

  it('ignores empty file selection', () => {
    component.onFileSelected({ target: { files: [] } } as unknown as Event);
    expect(component.selectedFile()).toBeNull();
  });

  it('rejects non-image files', () => {
    component.onFileSelected({ target: { files: [new File(['x'], 'a.txt', { type: 'text/plain' })] } } as unknown as Event);
    expect(component.errorMessage()).toContain('Invalid format');
  });

  it('rejects oversized files', () => {
    const big = new File([new ArrayBuffer(mediaMock.MAX_FILE_SIZE + 1)], 'b.png', { type: 'image/png' });
    component.onFileSelected({ target: { files: [big] } } as unknown as Event);
    expect(component.errorMessage()).toContain('2 MB');
  });

  it('accepts a valid image and creates a preview', () => {
    component.onFileSelected({ target: { files: [new File(['x'], 'p.png', { type: 'image/png' })] } } as unknown as Event);
    expect(component.selectedFile()).not.toBeNull();
    expect(component.previewUrl()).toBe('blob:preview');
  });

  it('clears selection', () => {
    component.selectedFile.set(new File(['x'], 'p.png', { type: 'image/png' }));
    component.previewUrl.set('blob:x');
    component.clearSelection();
    expect(component.selectedFile()).toBeNull();
    expect(component.previewUrl()).toBeNull();
  });

  it('uploads the selected file', () => {
    vi.useFakeTimers();
    component.selectedFile.set(new File(['x'], 'p.png', { type: 'image/png' }));
    component.upload();
    expect(mediaMock.uploadImage).toHaveBeenCalled();
    expect(component.mediaList().length).toBe(1);
    expect(component.toastMessage()).toContain('uploaded');
    vi.useRealTimers();
  });

  it('upload without a file is a no-op', () => {
    component.upload();
    expect(mediaMock.uploadImage).not.toHaveBeenCalled();
  });

  it('reports upload errors', () => {
    mediaMock.uploadImage.mockReturnValue(throwError(() => new Error('rejected')));
    component.selectedFile.set(new File(['x'], 'p.png', { type: 'image/png' }));
    component.upload();
    expect(component.errorMessage()).toBe('rejected');
  });

  it('manages the preview modal', () => {
    component.openPreview({ id: '1', url: 'u', filename: 'f' });
    expect(component.previewModalItem()?.id).toBe('1');
    component.onEscape();
    expect(component.previewModalItem()).toBeNull();
  });

  it('escape without modal is a no-op', () => {
    component.onEscape();
    expect(component.previewModalItem()).toBeNull();
  });

  it('copies URL using the clipboard', async () => {
    const writeText = vi.fn(() => Promise.resolve());
    Object.assign(navigator, { clipboard: { writeText } });
    component.copyUrl('https://u');
    await Promise.resolve();
    expect(writeText).toHaveBeenCalledWith('https://u');
  });

  it('falls back to a toast when clipboard is unavailable', () => {
    Object.assign(navigator, { clipboard: undefined });
    component.copyUrl('https://u');
    expect(component.toastMessage()).toContain('https://u');
  });
});