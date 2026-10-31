import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Order } from '../../../core/models/order';
import { AuthService } from '../../../core/services/auth';
import { OrderService } from '../../../core/services/order';
import { shortId, statusBadge, statusLabel } from '../order-status';

/** One order: items, totals, address and status timeline. Sellers only receive their own items. */
@Component({
  selector: 'app-order-details',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './order-details.html',
})
export class OrderDetails implements OnInit {
  readonly statusLabel = statusLabel;
  readonly statusBadge = statusBadge;
  readonly shortId = shortId;

  readonly order = signal<Order | null>(null);
  readonly busy = signal(false);
  readonly error = signal('');
  readonly seller: boolean;
  private readonly id: string;

  constructor(
    private readonly orders: OrderService,
    auth: AuthService,
    route: ActivatedRoute,
  ) {
    this.seller = auth.hasRole('SELLER');
    this.id = route.snapshot.paramMap.get('id') ?? '';
  }

  get backLink(): string {
    return this.seller ? '/seller/orders' : '/orders';
  }

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.busy.set(true);
    this.error.set('');
    this.orders.get(this.id).subscribe({
      next: order => {
        this.order.set(order);
        this.busy.set(false);
      },
      error: e => this.fail(e, 'Unable to load this order. Please retry.'),
    });
  }

  /** Newest change first. */
  timeline(order: Order) {
    return [...order.statusHistory].reverse();
  }

  protected fail(e: { status?: number; error?: { message?: string } }, fallback: string): void {
    const notFound = e.status === 404 || e.status === 403;
    this.error.set(notFound ? 'This order does not exist or is not yours.' : e.error?.message || fallback);
    this.busy.set(false);
  }
}
