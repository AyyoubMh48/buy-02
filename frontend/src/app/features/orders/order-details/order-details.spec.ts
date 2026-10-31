import { of, throwError } from 'rxjs';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { Order } from '../../../core/models/order';
import { AuthService } from '../../../core/services/auth';
import { OrderService } from '../../../core/services/order';
import { OrderDetails } from './order-details';

const sampleOrder = (overrides: Partial<Order> = {}): Order => ({
  id: 'order-000123',
  customerId: 'customer-1',
  status: 'PENDING',
  items: [
    { productId: 'p1', sellerId: 's1', productName: 'Lamp', imageUrl: null, unitPrice: 10, quantity: 2, lineTotal: 20 },
  ],
  shippingAddress: { fullName: 'Sara', phone: '06', street: '1 Main St', city: 'Rabat', postalCode: '10000', country: 'Morocco' },
  paymentMethod: 'CASH_ON_DELIVERY',
  totalItems: 2,
  totalAmount: 20,
  statusHistory: [
    { status: 'PENDING', changedAt: '2026-10-01T10:00:00Z', changedBy: 'customer-1', note: 'Order placed' },
    { status: 'CONFIRMED', changedAt: '2026-10-02T10:00:00Z', changedBy: 's1', note: null },
  ],
  createdAt: '2026-10-01T10:00:00Z',
  updatedAt: '2026-10-02T10:00:00Z',
  ...overrides,
});

describe('OrderDetails', () => {
  let api: { get: ReturnType<typeof vi.fn> };

  const create = (role: 'CLIENT' | 'SELLER' = 'CLIENT', id: string | null = 'order-000123') =>
    new OrderDetails(
      api as unknown as OrderService,
      { hasRole: (r: string) => r === role } as unknown as AuthService,
      { snapshot: { paramMap: convertToParamMap(id ? { id } : {}) } } as unknown as ActivatedRoute,
    );

  beforeEach(() => {
    api = { get: vi.fn(() => of(sampleOrder())) };
  });

  it('loads the order from the route id', () => {
    const page = create();
    page.ngOnInit();
    expect(api.get).toHaveBeenCalledWith('order-000123');
    expect(page.order()?.id).toBe('order-000123');
    expect(page.busy()).toBe(false);
    expect(page.seller).toBe(false);
    expect(page.backLink).toBe('/orders');
  });

  it('links sellers back to their order list', () => {
    const page = create('SELLER');
    expect(page.seller).toBe(true);
    expect(page.backLink).toBe('/seller/orders');
  });

  it('shows the newest status change first without changing the order', () => {
    const order = sampleOrder();
    const page = create();
    expect(page.timeline(order).map(c => c.status)).toEqual(['CONFIRMED', 'PENDING']);
    expect(order.statusHistory[0].status).toBe('PENDING');
  });

  it.each([
    [{ status: 404 }, 'This order does not exist or is not yours.'],
    [{ status: 403 }, 'This order does not exist or is not yours.'],
    [{ status: 502, error: { message: 'Product Service is unavailable' } }, 'Product Service is unavailable'],
    [{ status: 0 }, 'Unable to load this order. Please retry.'],
  ])('explains load failures', (failure, message) => {
    api.get.mockReturnValue(throwError(() => failure));
    const page = create('CLIENT', null);
    page.ngOnInit();
    expect(api.get).toHaveBeenCalledWith('');
    expect(page.error()).toBe(message);
    expect(page.busy()).toBe(false);
  });
});
