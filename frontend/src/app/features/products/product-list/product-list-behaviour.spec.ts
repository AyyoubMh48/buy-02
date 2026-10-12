import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { ProductList } from './product-list';
import { ProductService } from '../../../core/services/product';
import { Product } from '../../../core/models/product';

const products: Product[] = [
  { id: '1', name: 'Apple', description: 'red fruit', price: 10, quantity: 5, images: ['a.png'] },
  { id: '2', name: 'Banana', description: 'yellow', price: 5, quantity: 0, images: [] },
  { id: '3', name: 'Cherry', description: '', price: 20, quantity: 2, images: ['c.png'] },
];

describe('ProductList behaviour', () => {
  let component: ProductList;
  let serviceMock: { getProducts: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    serviceMock = { getProducts: vi.fn(() => of(products)) };
    TestBed.configureTestingModule({
      providers: [{ provide: ProductService, useValue: serviceMock }],
    });
    component = TestBed.runInInjectionContext(() => new ProductList(TestBed.inject(ProductService)));
  });

  it('loads products on init', () => {
    component.ngOnInit();
    expect(component.products().length).toBe(3);
    expect(component.loading()).toBe(false);
  });

  it('sets an error when loading fails', () => {
    serviceMock.getProducts.mockReturnValue(throwError(() => new Error('down')));
    component.loadProducts();
    expect(component.loadError()).toContain('Unable to retrieve');
    expect(component.loading()).toBe(false);
  });

  it('filters by search query', () => {
    component.products.set(products);
    component.searchQuery.set('ban');
    expect(component.filteredProducts().map(p => p.id)).toEqual(['2']);
  });

  it('filters in-stock products', () => {
    component.products.set(products);
    component.filterStock.set('in-stock');
    expect(component.filteredProducts().length).toBe(2);
  });

  it('sorts by price ascending and descending', () => {
    component.products.set(products);
    component.sortBy.set('price-asc');
    expect(component.filteredProducts()[0].price).toBe(5);
    component.sortBy.set('price-desc');
    expect(component.filteredProducts()[0].price).toBe(20);
  });

  it('sorts by name', () => {
    component.products.set(products);
    component.sortBy.set('name-asc');
    expect(component.filteredProducts()[0].name).toBe('Apple');
  });

  it('clearSearch resets controls', () => {
    component.searchQuery.set('x');
    component.filterStock.set('in-stock');
    component.sortBy.set('price-asc');
    component.clearSearch();
    expect(component.searchQuery()).toBe('');
    expect(component.filterStock()).toBe('all');
    expect(component.sortBy()).toBe('featured');
  });

  it('manages quick view modal', () => {
    component.openQuickView(products[0]);
    expect(component.selectedProduct()?.id).toBe('1');
    expect(component.activeModalImage()).toBe('a.png');
    component.setActiveModalImage('other.png');
    expect(component.activeModalImage()).toBe('other.png');
    component.closeQuickView();
    expect(component.selectedProduct()).toBeNull();
  });

  it('opens quick view with no images', () => {
    component.openQuickView(products[1]);
    expect(component.activeModalImage()).toBe('');
  });

  it('escape closes the modal only when open', () => {
    component.onEscapePress();
    expect(component.selectedProduct()).toBeNull();
    component.openQuickView(products[0]);
    component.onEscapePress();
    expect(component.selectedProduct()).toBeNull();
  });

  it('shows a toast when adding to order', () => {
    vi.useFakeTimers();
    component.addToOrder(products[0]);
    expect(component.toastMessage()).toContain('Apple');
    vi.advanceTimersByTime(3600);
    expect(component.toastMessage()).toBe('');
    vi.useRealTimers();
  });

  it('getPrimaryImage handles presence and absence', () => {
    expect(component.getPrimaryImage(products[0])).toBe('a.png');
    expect(component.getPrimaryImage(products[1])).toBe('');
  });

  it('onImageError hides the image and reveals the fallback', () => {
    const img = document.createElement('img');
    const fallback = document.createElement('div');
    img.appendChild(fallback);
    component.onImageError({ target: img } as unknown as Event);
    expect(img.style.display).toBe('none');
    expect(fallback.style.display).toBe('flex');
  });
});