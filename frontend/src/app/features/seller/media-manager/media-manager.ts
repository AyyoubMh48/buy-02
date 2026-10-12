import { Component, OnInit, signal, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MediaService } from '../../../core/services/media';
import { ProductService } from '../../../core/services/product';
import { MediaResponse } from '../../../core/models/media';

interface DisplayMedia {
  id?: string;
  url: string;
  filename: string;
  size?: number;
  source?: string;
}

@Component({
  selector: 'app-media-manager',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './media-manager.html',
  styleUrl: './media-manager.css',
})
export class MediaManager implements OnInit {
  readonly selectedFile = signal<File | null>(null);
  readonly previewUrl = signal<string | null>(null);
  readonly uploading = signal<boolean>(false);
  readonly errorMessage = signal<string>('');
  readonly toastMessage = signal<string>('');
  
  // Gallery items
  readonly mediaList = signal<DisplayMedia[]>([]);

  // Preview Modal
  readonly previewModalItem = signal<DisplayMedia | null>(null);

  constructor(
    private readonly mediaService: MediaService,
    private readonly productService: ProductService
  ) {}

  ngOnInit(): void {
    this.loadExistingCatalogMedia();
  }

  loadExistingCatalogMedia(): void {
    this.productService.getProducts().subscribe({
      next: (products) => {
        const found: DisplayMedia[] = [];
        const seen = new Set<string>();

        for (const p of products) {
          if (p.images?.length) {
            for (const imgUrl of p.images) {
              if (imgUrl && !seen.has(imgUrl)) {
                seen.add(imgUrl);
                const namePart = imgUrl.split('/').pop() || 'Product Asset';
                found.push({
                  url: imgUrl,
                  filename: namePart,
                  source: p.name
                });
              }
            }
          }
        }
        this.mediaList.set(found);
      },
      error: () => {}
    });
  }

  onFileSelected(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    this.errorMessage.set('');

    if (!file) return;

    if (!file.type.startsWith('image/')) {
      this.errorMessage.set('Invalid format. Please select an image file (e.g. JPG, PNG, WebP).');
      this.selectedFile.set(null);
      this.previewUrl.set(null);
      return;
    }

    if (file.size > this.mediaService.MAX_FILE_SIZE) {
      this.errorMessage.set('Selected file exceeds the 2 MB maximum size limit.');
      this.selectedFile.set(null);
      this.previewUrl.set(null);
      return;
    }

    this.selectedFile.set(file);

    // Create local object URL for instant preview
    const objectUrl = URL.createObjectURL(file);
    this.previewUrl.set(objectUrl);
  }

  clearSelection(): void {
    this.selectedFile.set(null);
    this.previewUrl.set(null);
  }

  upload(): void {
    const file = this.selectedFile();
    if (!file) return;

    this.uploading.set(true);
    this.errorMessage.set('');

    this.mediaService.uploadImage(file).subscribe({
      next: (res: MediaResponse) => {
        const newItem: DisplayMedia = {
          id: res.id,
          url: res.url,
          filename: res.filename || file.name,
          size: res.size || file.size,
          source: 'Newly Uploaded'
        };
        this.mediaList.update(list => [newItem, ...list]);
        this.clearSelection();
        this.uploading.set(false);
        this.showToast('Asset uploaded successfully to Media Service.');
      },
      error: (err) => {
        this.errorMessage.set(err.message || 'Media upload rejected.');
        this.uploading.set(false);
      }
    });
  }

  copyUrl(url: string): void {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(url).then(() => {
        this.showToast('Asset URL copied to clipboard.');
      }).catch(() => {
        this.showToast(`URL: ${url}`);
      });
    } else {
      this.showToast(`URL: ${url}`);
    }
  }

  openPreview(item: DisplayMedia): void {
    this.previewModalItem.set(item);
  }

  closePreview(): void {
    this.previewModalItem.set(null);
  }

  showToast(msg: string): void {
    this.toastMessage.set(msg);
    setTimeout(() => {
      this.toastMessage.set('');
    }, 3500);
  }

  @HostListener('window:keydown.escape')
  onEscape(): void {
    if (this.previewModalItem()) {
      this.closePreview();
    }
  }
}