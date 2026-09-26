import { Component, OnInit, signal, computed, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, FormsModule, Validators } from '@angular/forms';
import { ProductService } from '../../../core/services/product';
import { MediaService } from '../../../core/services/media';
import { Product } from '../../../core/models/product';

@Component({
  selector: 'app-seller-dashboard',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule],
  templateUrl: './seller-dashboard.html',
  styleUrl: './seller-dashboard.css'
})
export class SellerDashboard implements OnInit {
  products = signal<Product[]>([]);
  productForm: FormGroup;
  showForm = signal<boolean>(false);
  editingId = signal<string | null>(null);
  attachedMedia = signal<{ id?: string; url: string }[]>([]);
  uploading = signal<boolean>(false);
  saving = signal<boolean>(false);
  statusMessage = signal<string>('');
  statusType = signal<'success' | 'danger' | 'info'>('info');

  // Search in seller table
  filterQuery = signal<string>('');

  // Accessible in-app delete modal (R-26, R-32)
  pendingDeleteProduct = signal<Product | null>(null);

  constructor(
    private fb: FormBuilder,
    private productService: ProductService,
    private mediaService: MediaService
  ) {
    this.productForm = this.fb.group({
      name: ['', [Validators.required, Validators.minLength(2)]],
      price: [null, [Validators.required, Validators.min(0.01)]],
      quantity: [1, [Validators.required, Validators.min(0)]],
      description: ['', [Validators.required, Validators.minLength(5)]]
    });
  }

  ngOnInit(): void {
    this.loadProducts();
  }

  loadProducts(): void {
    this.productService.getMyProducts().subscribe({
      next: (data) => this.products.set(data || []),
      error: () => this.showNotification('Failed to retrieve catalog listings.', 'danger')
    });
  }

  // Real dashboard metrics (R-17 - genuine data only, no fabricated numbers)
  totalListings = computed(() => this.products().length);
  totalUnits = computed(() => this.products().reduce((acc, p) => acc + (p.quantity || 0), 0));
  inStockCount = computed(() => this.products().filter(p => (p.quantity || 0) > 0).length);
  outOfStockCount = computed(() => this.products().filter(p => (p.quantity || 0) === 0).length);

  // Filtered seller products
  filteredProducts = computed(() => {
    const q = this.filterQuery().trim().toLowerCase();
    if (!q) return this.products();
    return this.products().filter(p =>
      p.name.toLowerCase().includes(q) ||
      (p.description && p.description.toLowerCase().includes(q))
    );
  });

  openCreateForm(): void {
    this.editingId.set(null);
    this.attachedMedia.set([]);
    this.productForm.reset({ price: null, quantity: 1, name: '', description: '' });
    this.showForm.set(true);
  }

  editProduct(product: Product): void {
    this.editingId.set(product.id || null);
    const media = (product.images || []).map((url, index) => ({
      url,
      id: product.mediaIds?.[index]
    }));
    this.attachedMedia.set(media);
    this.productForm.patchValue({
      name: product.name,
      price: product.price,
      quantity: product.quantity,
      description: product.description
    });
    this.showForm.set(true);
  }

  closeForm(): void {
    this.showForm.set(false);
    this.editingId.set(null);
  }

  uploadImage(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;

    if (file.size > this.mediaService.MAX_FILE_SIZE) {
      this.showNotification('File exceeds the 2 MB maximum limit.', 'danger');
      return;
    }

    this.uploading.set(true);
    this.mediaService.uploadImage(file).subscribe({
      next: (res) => {
        this.attachedMedia.update(list => [...list, { id: res.id, url: res.url }]);
        this.uploading.set(false);
        this.showNotification('Image uploaded and attached.', 'success');
      },
      error: (err) => {
        this.showNotification(err.message || 'Image upload failed.', 'danger');
        this.uploading.set(false);
      }
    });
  }

  removeImage(index: number): void {
    this.attachedMedia.update(list => list.filter((_, i) => i !== index));
  }

  saveProduct(): void {
    if (this.productForm.invalid) {
      this.productForm.markAllAsTouched();
      return;
    }

    if (this.attachedMedia().length === 0) {
      this.showNotification('At least one product image is required.', 'danger');
      return;
    }

    this.saving.set(true);
    const mediaIds = this.attachedMedia()
      .filter(m => !!m.id)
      .map(m => m.id as string);

    if (mediaIds.length === 0) {
      this.showNotification('Each product image must finish uploading before you save.', 'danger');
      return;
    }

    const payload: Product = {
      ...this.productForm.value,
      mediaIds: mediaIds.length > 0 ? mediaIds : undefined
    };

    const currentId = this.editingId();
    if (currentId) {
      this.productService.updateProduct(currentId, payload).subscribe({
        next: () => {
          this.saving.set(false);
          this.showNotification('Product details updated successfully.', 'success');
          this.loadProducts();
          this.closeForm();
        },
        error: (err) => {
          this.saving.set(false);
          this.showNotification(err.error?.message || 'Failed to update product.', 'danger');
        }
      });
    } else {
      this.productService.createProduct(payload).subscribe({
        next: () => {
          this.saving.set(false);
          this.showNotification('New product created successfully.', 'success');
          this.loadProducts();
          this.closeForm();
        },
        error: (err) => {
          this.saving.set(false);
          this.showNotification(err.error?.message || 'Failed to create product.', 'danger');
        }
      });
    }
  }

  requestDeleteProduct(product: Product): void {
    this.pendingDeleteProduct.set(product);
  }

  cancelDelete(): void {
    this.pendingDeleteProduct.set(null);
  }

  confirmDelete(): void {
    const p = this.pendingDeleteProduct();
    if (!p || !p.id) return;

    this.productService.deleteProduct(p.id).subscribe({
      next: () => {
        this.showNotification(`Product "${p.name}" deleted.`, 'success');
        this.pendingDeleteProduct.set(null);
        this.loadProducts();
      },
      error: (err) => {
        this.showNotification(err.error?.message || 'Failed to delete product.', 'danger');
        this.pendingDeleteProduct.set(null);
      }
    });
  }

  showNotification(msg: string, type: 'success' | 'danger' | 'info' = 'info'): void {
    this.statusMessage.set(msg);
    this.statusType.set(type);
    setTimeout(() => {
      this.statusMessage.set('');
    }, 4000);
  }

  @HostListener('window:keydown.escape')
  onEscapePress(): void {
    if (this.pendingDeleteProduct()) {
      this.cancelDelete();
    }
    if (this.showForm()) {
      this.closeForm();
    }
  }

  onThumbError(event: Event): void {
    const el = event.target as HTMLImageElement;
    el.style.display = 'none';
  }
}
