import { Component, OnInit, signal, computed, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProductService } from '../../../core/services/product';
import { Product } from '../../../core/models/product';

@Component({
  selector: 'app-product-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './product-list.html',
  styleUrl: './product-list.css',
})
export class ProductList implements OnInit {
  readonly products = signal<Product[]>([]);
  readonly loading = signal<boolean>(true);
  readonly loadError = signal<string>('');

  // Search, Filter & View Controls
  readonly searchQuery = signal<string>('');
  readonly sortBy = signal<string>('featured');
  readonly filterStock = signal<string>('all');
  readonly viewMode = signal<'grid' | 'list'>('grid');

  // Interactive Quick View Modal (R-26, C-2)
  readonly selectedProduct = signal<Product | null>(null);
  readonly activeModalImage = signal<string>('');

  // Toast Feedback
  readonly toastMessage = signal<string>('');
  private toastTimeout: ReturnType<typeof setTimeout> | undefined;

  constructor(private readonly productService: ProductService) {}

  ngOnInit(): void {
    this.loadProducts();
  }

  loadProducts(): void {
    this.loading.set(true);
    this.loadError.set('');
    this.productService.getProducts().subscribe({
      next: (data: Product[]) => {
        this.products.set(data || []);
        this.loading.set(false);
      },
      error: () => {
        this.loadError.set('Unable to retrieve products. Please verify your connection.');
        this.loading.set(false);
      }
    });
  }

  // Computed filtered & sorted product list
  readonly filteredProducts = computed(() => {
    let list = [...this.products()];
    const query = this.searchQuery().trim().toLowerCase();

    if (query) {
      list = list.filter(p =>
        p.name.toLowerCase().includes(query) ||
        p.description?.toLowerCase().includes(query)
      );
    }

    if (this.filterStock() === 'in-stock') {
      list = list.filter(p => (p.quantity ?? 0) > 0);
    }

    switch (this.sortBy()) {
      case 'price-asc':
        list.sort((a, b) => a.price - b.price);
        break;
      case 'price-desc':
        list.sort((a, b) => b.price - a.price);
        break;
      case 'name-asc':
        list.sort((a, b) => a.name.localeCompare(b.name));
        break;
      default:
        // 'featured' keeps server order
        break;
    }

    return list;
  });

  clearSearch(): void {
    this.searchQuery.set('');
    this.filterStock.set('all');
    this.sortBy.set('featured');
  }

  openQuickView(product: Product): void {
    this.selectedProduct.set(product);
    const firstImg = product.images && product.images.length > 0 ? product.images[0] : '';
    this.activeModalImage.set(firstImg);
  }

  closeQuickView(): void {
    this.selectedProduct.set(null);
    this.activeModalImage.set('');
  }

  setActiveModalImage(url: string): void {
    this.activeModalImage.set(url);
  }

  addToOrder(product: Product): void {
    this.showToast(`Item "${product.name}" added to order request.`);
  }

  showToast(msg: string): void {
    this.toastMessage.set(msg);
    if (this.toastTimeout) clearTimeout(this.toastTimeout);
    this.toastTimeout = setTimeout(() => {
      this.toastMessage.set('');
    }, 3500);
  }

  @HostListener('window:keydown.escape')
  onEscapePress(): void {
    if (this.selectedProduct()) {
      this.closeQuickView();
    }
  }

  getPrimaryImage(p: Product): string {
    if (p.images && p.images.length > 0 && p.images[0]) {
      return p.images[0];
    }
    return '';
  }

  onImageError(event: Event): void {
    const imgElement = event.target as HTMLImageElement;
    imgElement.style.display = 'none';
    const fallback = imgElement.nextElementSibling as HTMLElement;
    if (fallback) {
      fallback.style.display = 'flex';
    }
  }
}
