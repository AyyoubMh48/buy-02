# Order Service — Service Layer

This document describes the **service layer** added to the Orders microservice on branch `order-service-layer`. It builds on the two earlier, already merged steps:

1. `Orders-1` — module setup (Spring Boot, MongoDB, Eureka, gateway route, Docker Compose, Jenkins).
2. `order-backend-build` — DTOs, `OrderController`, user context, error handling, and the `OrderService` **interface**.

This step adds the implementation behind that interface: persistence, product snapshots, pricing, status rules, authorization and duplicate-order protection. With it, the service starts and works end to end. Before it, `main` contained the controller without an implementation, so the service could not start in Docker.

It also adds stock reservation (with a new internal endpoint in Product Service), paginated order lists, and two gateway fixes that orders depend on: identity headers can no longer be spoofed, and CORS allows the `Idempotency-Key` header.

---

## Contents

- [What changed](#what-changed)
- [Architecture](#architecture)
- [Data model](#data-model)
- [Order lifecycle](#order-lifecycle)
- [Business rules per endpoint](#business-rules-per-endpoint)
- [API reference](#api-reference)
- [Creating an order step by step](#creating-an-order-step-by-step)
- [Search and filtering](#search-and-filtering)
- [Calling Product Service](#calling-product-service)
- [Stock reservation](#stock-reservation)
- [Pricing](#pricing)
- [Concurrency and duplicate protection](#concurrency-and-duplicate-protection)
- [Error responses](#error-responses)
- [Configuration](#configuration)
- [Testing](#testing)
- [Known limitations](#known-limitations)

---

## What changed

### New files

| File | Purpose |
|---|---|
| `models/Order.java` | MongoDB document for the `orders` collection, with indexes and optimistic locking |
| `models/OrderItem.java` | Product snapshot stored in each order line |
| `models/ShippingAddress.java` | Delivery address stored with the order |
| `models/StatusChange.java` | One entry of the status timeline |
| `repository/OrderRepository.java` | Spring Data repository (by id, by customer + idempotency key) |
| `repository/OrderSearchRepository.java` | Filtered customer/seller lists built with `MongoTemplate` |
| `client/ProductClient.java` | Reads product data from Product Service through Eureka |
| `dtos/external/ProductDetails.java` | The Product Service fields an order needs |
| `config/AppConfig.java` | `@LoadBalanced` `RestClient.Builder` with timeouts, and a `Clock` bean |
| `service/OrderServiceImpl.java` | Implementation of `OrderService` |
| `service/OrderMapper.java` | Model ↔ DTO conversion, including the seller view |
| `service/OrderPricing.java` | All money calculations |
| `dtos/external/StockRequest.java` | Body of Product Service's stock endpoints |
| `dtos/external/UpstreamError.java` | Reads the `message` of another service's error response |
| `dtos/req/PageParams.java` | `page` / `size` query parameters of the lists |
| `dtos/response/PageResponse.java` | Paginated list response |

### Modified files

| File | Change |
|---|---|
| `pom.xml` | Added `spring-boot-starter-restclient` and `spring-cloud-starter-loadbalancer` |
| `application.properties` | `spring.mongodb.uri` (Spring Boot 4 name) and `product-service.base-url` |
| `models/OrderStatus.java` | Added the transition rules (`allowedNext`, `canTransitionTo`) |
| `exception/GlobalExceptionHandler.java` | `OptimisticLockingFailureException` → 409 |
| `OrderServiceApplicationTests.java` | Removed the `OrderService` mock; disables index creation in tests |
| `controller/OrderControllerTest.java` | Added the concurrent-update 409 test and the paging tests |
| `controller/OrderController.java` | `GET /orders/my` and `/orders/seller` return a `PageResponse` |

### Other services

| File | Change |
|---|---|
| `product-service/.../controller/StockController.java` | **new**: `POST /internal/stock/reserve` and `/internal/stock/release` |
| `product-service/.../service/StockService.java` | **new**: atomic all-or-nothing stock decrement, and release |
| `product-service/.../dtos/req/StockRequest.java`, `exception/ConflictException.java` | **new**, with a 409 handler in `GlobalExceptionHandler` |
| `gateway/.../security/JwtAuthenticationFilter.java` | Always removes client-sent `X-User-Id` / `X-User-Role` / `X-User-Roles`, then sets them from the JWT |
| `gateway/.../filter/CustomHttpServletRequestWrapper.java` | Case-insensitive header names, and `removeHeader` |
| `gateway/.../security/SecurityConfig.java` | CORS allows `Idempotency-Key`; no longer allows `X-User-*` |

### New tests

`OrderServiceImplTest`, `OrderStatusTest`, `OrderPricingTest`, `OrderSearchRepositoryTest`, `ProductClientTest`.
Product Service: `StockServiceTest`, `StockControllerTest`. Gateway: `CorsConfigTest`, plus spoofing tests in `JwtAuthenticationFilterTest` and `CustomHttpServletRequestWrapperTest`.

---

## Architecture

```
Browser ──► nginx (/api/orders) ──► Gateway (/orders, JWT → X-User-Id / X-User-Roles)
                                         │  lb://order-service (Eureka)
                                         ▼
┌──────────────────────────── order-service ────────────────────────────┐
│  UserContextFilter → @CurrentUser AuthenticatedUser                    │
│        │                                                              │
│  OrderController ──► OrderService (interface)                         │
│                          │                                            │
│                    OrderServiceImpl ──► OrderPricing                  │
│                     │      │     │                                    │
│      OrderRepository │      │     └──► OrderMapper ──► DTOs            │
│ OrderSearchRepository┘      │                                         │
│            │           ProductClient ──(@LoadBalanced RestClient)─────┼──► product-service
│            ▼                                                          │    GET /products/{id}
│                                                                       │    POST /internal/stock/*
│      order-mongodb (orders collection)                                │
└───────────────────────────────────────────────────────────────────────┘
```

- The controller does no business logic. It validates input and delegates to `OrderService`.
- `OrderServiceImpl` owns every rule: roles, ownership, transitions, stock, idempotency.
- The gateway is the only source of identity. It removes any `X-User-*` header a client sends, and sets them only from a valid JWT.
- Money math lives only in `OrderPricing`, and the transition rules only in `OrderStatus`.

---

## Data model

One order is one MongoDB document in the `orders` collection.

```json
{
  "_id": ObjectId("6718f2a9c3b1e45d2a9f0c11"),
  "version": 1,
  "customerId": "customer-1",
  "idempotencyKey": "3f2b8c1e-9d4a-4c7e-b1f0-2a6d8e5c7b90",
  "status": "CONFIRMED",
  "items": [
    { "productId": "p1", "sellerId": "seller-a", "productName": "Headphones",
      "imageUrl": "https://.../h1.png", "unitPrice": NumberDecimal("20.00"),
      "quantity": 2, "lineTotal": NumberDecimal("40.00") },
    { "productId": "p2", "sellerId": "seller-b", "productName": "USB Cable",
      "imageUrl": null, "unitPrice": NumberDecimal("5.00"),
      "quantity": 1, "lineTotal": NumberDecimal("5.00") }
  ],
  "sellerIds": ["seller-a", "seller-b"],
  "shippingAddress": { "fullName": "Sara B.", "phone": "0600000000", "street": "1 Main St",
                       "city": "Casablanca", "postalCode": "20000", "country": "Morocco" },
  "paymentMethod": "CASH_ON_DELIVERY",
  "totalItems": 3,
  "totalAmount": NumberDecimal("45.00"),
  "statusHistory": [
    { "status": "PENDING",   "changedAt": ISODate("2026-10-24T10:15:00Z"), "changedBy": "customer-1", "note": "Order placed" },
    { "status": "CONFIRMED", "changedAt": ISODate("2026-10-24T11:02:00Z"), "changedBy": "seller-a",   "note": null }
  ],
  "createdAt": ISODate("2026-10-24T10:15:00Z"),
  "updatedAt": ISODate("2026-10-24T11:02:00Z")
}
```

### Key design choices

- **Product snapshot.** Each item copies the product's name, image, unit price and seller at order time. Later product edits or deletion never change past orders.
- **Exact money.** Prices and totals are `BigDecimal`, stored as `DECIMAL128`, so they stay exact and Mongo can still do arithmetic and sorting on them.
- **`sellerIds`.** The distinct sellers of the items, kept separately so a seller's orders can be found through an index.
- **`statusHistory`.** Entries are only ever added, never edited. It drives the timeline on the order details page.
- **`@Version`.** Optimistic locking: see [Concurrency](#concurrency-and-duplicate-protection).

### Indexes

| Name | Definition | Used by |
|---|---|---|
| `customer_idempotency_key` | `{customerId: 1, idempotencyKey: 1}`, **unique** | duplicate-order protection |
| `customer_created` | `{customerId: 1, createdAt: -1}` | `GET /orders/my`, newest first |
| `seller_created` | `{sellerIds: 1, createdAt: -1}` | `GET /orders/seller`, newest first |

The indexes are created at startup (`spring.data.mongodb.auto-index-creation=true`).

---

## Order lifecycle

```
             ┌─────────┐     ┌───────────┐     ┌─────────┐     ┌───────────┐
 placed ───► │ PENDING │ ──► │ CONFIRMED │ ──► │ SHIPPED │ ──► │ DELIVERED │  final
             └─────────┘     └───────────┘     └─────────┘     └───────────┘
                  │                │
                  ▼                ▼
             ┌────────────────────────────┐
             │         CANCELLED          │  final
             └────────────────────────────┘
```

| From | Allowed next |
|---|---|
| `PENDING` | `CONFIRMED`, `CANCELLED` |
| `CONFIRMED` | `SHIPPED`, `CANCELLED` |
| `SHIPPED` | `DELIVERED` |
| `DELIVERED`, `CANCELLED` | none |

Skipping steps, going backwards, staying in the same status, and changing a final status are all rejected with **409**. The rules live in `OrderStatus.allowedNext()`. Because it's an exhaustive `switch`, adding a new status without rules won't compile.

---

## Business rules per endpoint

All paths are as seen by the service. The frontend calls them under `/api/orders`.

| Endpoint | Who | Rules | Success |
|---|---|---|---|
| `POST /orders` | `CLIENT` | `Idempotency-Key` header required; products must exist and be in stock | 201, the full order |
| `GET /orders/my` | any authenticated user | only the caller's own orders; filters and paging apply | 200, page |
| `GET /orders/seller` | `SELLER` | only orders containing the caller's products; **only the seller's own items and totals** | 200, page |
| `GET /orders/{id}` | the customer who placed it, or a seller in it | the customer sees the full order; a seller sees only their items | 200 |
| `PATCH /orders/{id}/cancel` | the customer who placed it | only from `PENDING` or `CONFIRMED`; the units go back in stock | 200, cancelled order |
| `POST /orders/{id}/reorder` | the customer who placed it | any status, including cancelled; returns product ids and quantities, **not prices** | 200 |
| `PATCH /orders/{id}/status` | `SELLER` with products in the order | must be an allowed transition; optional `note` goes in the history; `CANCELLED` puts the units back in stock | 200, seller view |

Every rejected access returns **403** and every unknown id **404**. A request without identity headers is rejected with **401** before reaching the service.

### Seller view

A customer may buy from several sellers in one order. A seller only sees **their own items**, and `totalItems` / `totalAmount` are recalculated for those items. Other sellers' products and prices stay private. The shipping address and status history are visible, because the seller needs them to ship.

### Reorder

Reorder does not create an order. It returns the original items (`productId`, `quantity`) so the frontend can start a new checkout. Prices aren't copied: the new order gets current prices and a stock check when it's created.

---

## API reference

Base path from the browser: `/api/orders` (nginx → gateway `/orders`). Every endpoint needs `Authorization: Bearer <jwt>`. Responses are JSON; amounts are decimal numbers with 2 places; times are ISO-8601 UTC.

### `POST /orders` — place an order

Headers: `Idempotency-Key: <uuid>` (required, at most 100 characters; reuse it for every retry of the same checkout).

```json
{
  "items": [
    { "productId": "6718e0c2a1b2c3d4e5f60708", "quantity": 2 },
    { "productId": "6718e0c2a1b2c3d4e5f60709", "quantity": 1 }
  ],
  "shippingAddress": {
    "fullName": "Sara B.", "phone": "0600000000", "street": "1 Main St",
    "city": "Casablanca", "postalCode": "20000", "country": "Morocco"
  },
  "paymentMethod": "CASH_ON_DELIVERY"
}
```

| Field | Rules |
|---|---|
| `items` | 1 to 50 entries; the same product may appear twice (quantities are added) |
| `items[].quantity` | 1 to 100, and at most 100 per product after merging |
| `shippingAddress.*` | all required; `fullName`, `city`, `country` ≤ 100, `phone` ≤ 30, `street` ≤ 200, `postalCode` ≤ 20 characters |
| `paymentMethod` | optional, `CASH_ON_DELIVERY` (the only method) |

Only ids and quantities are accepted: name, price and seller always come from Product Service.

**201** — the order (`OrderResponse`):

```json
{
  "id": "6718f2a9c3b1e45d2a9f0c11",
  "customerId": "customer-1",
  "status": "PENDING",
  "items": [
    { "productId": "6718e0c2a1b2c3d4e5f60708", "sellerId": "seller-a", "productName": "Headphones",
      "imageUrl": "https://.../h1.png", "unitPrice": 20.00, "quantity": 2, "lineTotal": 40.00 }
  ],
  "shippingAddress": { "fullName": "Sara B.", "phone": "0600000000", "street": "1 Main St",
                       "city": "Casablanca", "postalCode": "20000", "country": "Morocco" },
  "paymentMethod": "CASH_ON_DELIVERY",
  "totalItems": 2,
  "totalAmount": 40.00,
  "statusHistory": [
    { "status": "PENDING", "changedAt": "2026-10-24T10:15:00Z", "changedBy": "customer-1", "note": "Order placed" }
  ],
  "createdAt": "2026-10-24T10:15:00Z",
  "updatedAt": "2026-10-24T10:15:00Z"
}
```

### `GET /orders/my` and `GET /orders/seller` — lists

Query parameters, all optional: `status`, `from`, `to`, `q` (see [Search and filtering](#search-and-filtering)), `page` (0-based, default `0`, at most `10000`) and `size` (default `20`, 1 to `100`).

**200** — newest first:

```json
{
  "content": [ { "id": "6718f2a9c3b1e45d2a9f0c11", "status": "SHIPPED", "...": "OrderResponse fields" } ],
  "page": 0,
  "size": 20,
  "totalElements": 42,
  "totalPages": 3
}
```

On `/orders/seller`, each order contains only the seller's own items, and `totalItems` / `totalAmount` cover only those items.

### `GET /orders/{id}` — details

**200** — an `OrderResponse` (the seller view for a seller). `statusHistory` is the timeline for the details page.

### `PATCH /orders/{id}/cancel` — cancel

No body. **200** — the order with status `CANCELLED` and a new history entry `Cancelled by customer`.

### `POST /orders/{id}/reorder` — start a repeat purchase

No body. **200**:

```json
{
  "sourceOrderId": "6718f2a9c3b1e45d2a9f0c11",
  "items": [ { "productId": "6718e0c2a1b2c3d4e5f60708", "quantity": 2 } ]
}
```

`items` has the same shape as `POST /orders` items, so the frontend can put them in the cart or send them to checkout. Nothing is created and no stock is reserved.

### `PATCH /orders/{id}/status` — seller status update

```json
{ "status": "SHIPPED", "note": "Sent with Amana, tracking 123" }
```

`status` is required; `note` is optional, at most 255 characters. **200** — the seller view of the order.

### Errors

All errors use one shape: see [Error responses](#error-responses).

---

## Creating an order step by step

`OrderServiceImpl.createOrder(request, idempotencyKey, user)`:

1. **Role check.** Only `CLIENT` may order; anyone else gets 403.
2. **Idempotency lookup.** If an order exists for this customer + key, it's returned as-is. No new order is created and Product Service isn't called.
3. **Merge duplicates.** The same product listed twice becomes one line with the summed quantity. A merged quantity above 100 returns 400.
4. **Snapshot each product** through `ProductClient`:
   - not found → 400
   - Product Service down, slow or returning invalid data → 502
   - requested quantity above stock → 400 `Not enough stock for <name>: <n> available`
   - price converted to `BigDecimal` with 2 decimals
5. **Build the order:** status `PENDING`, `sellerIds`, totals, payment method (default `CASH_ON_DELIVERY`), first history entry `Order placed`, timestamps from the injected `Clock`.
6. **Reserve stock** in Product Service, all items or none (see [Stock reservation](#stock-reservation)). If another customer took the units since step 4 → 400 with Product Service's message.
7. **Insert.** If two identical requests race past step 2, the unique index rejects one (`DuplicateKeyException`). That request puts its own reservation back and returns the order the other one created, so both callers get the same order and the stock is only taken once. If the insert fails for any other reason, the reservation is put back and the error is returned.

```
CLIENT? ──no──► 403
   │yes
key already used? ──yes──► existing order (200 body, 201 status)
   │no
merge items (>100 ──► 400)
   │
for each product: fetch → validate → stock check → freeze price/name/seller
   │   (not found / out of stock ──► 400, upstream problem ──► 502)
build order (PENDING, totals, history)
   │
reserve stock ──not enough──► 400 (nothing saved, nothing taken)
   │
insert ──duplicate key──► release + order created by the concurrent request
   │   ──other failure──► release + error
   │
201 + order
```

---

## Search and filtering

`GET /orders/my` and `GET /orders/seller` accept these optional query parameters:

| Parameter | Example | Meaning |
|---|---|---|
| `status` | `SHIPPED` | exact status |
| `from` | `2026-01-01` | placed on or after this day (UTC) |
| `to` | `2026-01-31` | placed on or before this day (UTC, **whole day included**) |
| `q` | `head` | exact order id, **or** a product name containing the text (case-insensitive) |
| `page` | `0` | page number, starting at 0 (default 0) |
| `size` | `20` | orders per page, 1 to 100 (default 20) |

Validation: an unknown `status` returns 400, `from` after `to` returns 400, `q` is at most 100 characters, and `page` / `size` out of range return 400.

Example: `GET /orders/seller?status=SHIPPED&from=2026-01-01&to=2026-01-31&q=head` becomes

```js
db.orders.find({ $and: [
  { sellerIds: "seller-a" },
  { status: "SHIPPED" },
  { createdAt: { $gte: ISODate("2026-01-01T00:00:00Z"), $lt: ISODate("2026-02-01T00:00:00Z") } },
  { $or: [ { _id: "head" }, { "items.productName": /\Qhead\E/i } ] }
]}).sort({ createdAt: -1 }).skip(0).limit(20)
```

- The owner condition is always included, so filters can never reveal other users' orders.
- The search text is wrapped in `Pattern.quote`, so it is matched literally. Regex input like `.*` or `(a+)+$` can't match everything or slow the database down (ReDoS).
- Results are newest first. The total comes from a `count` with the same filters, which is skipped when the page alone gives it (a page that is not full).

---

## Calling Product Service

```
ProductClient.getProduct("p1")
  → RestClient GET http://product-service/products/p1   (Accept: application/json)
  → @LoadBalanced interceptor asks Eureka for "product-service" → e.g. 172.18.0.7:8082
  → product-service ProductController.getProductById (public endpoint, no JWT needed)
  → JSON → ProductDetails (unknown fields such as description and mediaIds are ignored)
```

| Product Service result | Order Service response |
|---|---|
| 200 with valid data | continue |
| 404 | **400** `Product not found: <id>` |
| 4xx / 5xx | **502** |
| no connection within 2 s, or no response within 5 s | **502** |
| empty body, missing name/owner, invalid price | **502** |

A 400 means the customer should change the request; a 502 means a service behind the order service failed.

- **Service discovery.** The `@LoadBalanced` builder resolves the logical name through Eureka and rotates between instances, so no host or port is hard-coded.
- **Timeouts.** Java's default HTTP client has no timeout. Without the 2 s / 5 s limits, a stuck Product Service would make order requests hang.

---

## Stock reservation

Checking stock when the order is built isn't enough: two customers can both see "1 available" and both order it. So the order service also **takes** the units from Product Service before saving the order, and gives them back on cancellation.

Product Service endpoints (`StockController`):

| Endpoint | Body | Result |
|---|---|---|
| `POST /internal/stock/reserve` | `{"items": [{"productId": "p1", "quantity": 2}]}` | **204**; **409** `Not enough stock for <name>: <n> available`; **404** unknown product |
| `POST /internal/stock/release` | same | **204**; deleted products are skipped |

- **Not reachable from outside.** The gateway has no route for `/internal/**` and only the gateway's port is published, so only services on the Docker network can call them.
- **Atomic per product.** Each product is decremented with one conditional update, `{_id: p1, quantity: {$gte: 2}}` → `$inc: {quantity: -2}`, so two orders can never both take the last unit.
- **All or nothing.** If one product is short, the products already decremented in that request are put back before the 409.

| When | Stock |
|---|---|
| order created | reserved just before the insert |
| reservation fails | nothing saved, 400 to the customer |
| insert fails, or loses an idempotency race | released |
| order cancelled, by the customer or by a seller (`PATCH /status`) | the whole order is released **after** the cancellation is saved; a failed save (e.g. 409 concurrent update) keeps the stock with the order |
| delivered | nothing to do: the units are already gone |

If a release fails (Product Service down), the request still succeeds, because the order's outcome is already decided. The failure is logged at `ERROR` with the product ids and quantities so the stock can be corrected by hand.

---

## Pricing

`OrderPricing` is the only place money is calculated:

| Method | Rule |
|---|---|
| `toPrice(double)` | `BigDecimal.valueOf(price)`, 2 decimals, half-up rounding; rejects negative, NaN and infinite |
| `lineTotal(unitPrice, qty)` | `unitPrice × qty`, 2 decimals |
| `totalAmount(items)` | sum of line totals, 2 decimals |
| `totalItems(items)` | sum of quantities |

Product Service stores prices as `double`. They're converted once, at the boundary. `BigDecimal.valueOf(19.99)` is exactly `19.99`, and every later calculation is exact (for example, `0.1 + 0.2` gives `0.30`, not `0.30000000000000004`).

---

## Concurrency and duplicate protection

### Duplicate orders: `Idempotency-Key`

The frontend generates one key per checkout (for example, `crypto.randomUUID()`) and sends it on every retry of that checkout. Double-clicks, timeouts and automatic retries then produce **one** order. Two layers enforce this:

1. a lookup before creating (the normal case)
2. a **unique index** for requests that arrive at the same moment

### Lost updates: `@Version`

Two requests that change the same order at the same time (for example, the customer cancels while the seller ships) can't overwrite each other. Each save increments `version` and only succeeds if the version is unchanged since the order was read. The losing request gets:

```
409 Conflict — "The order was modified at the same time, please retry"
```

---

## Error responses

Every error has the same shape:

```json
{
  "timestamp": "2026-10-24T10:15:02",
  "status": 409,
  "error": "Conflict",
  "message": "Cannot change order status from SHIPPED to CANCELLED",
  "path": "/orders/6718f2a9c3b1e45d2a9f0c11/cancel",
  "validationErrors": null
}
```

| Status | When |
|---|---|
| 400 | validation failure (with per-field `validationErrors`), malformed JSON, unknown enum value, missing `Idempotency-Key`, product not found, not enough stock (also when the stock reservation fails), quantity limit, invalid `page` / `size` |
| 401 | no `X-User-Id` (not authenticated through the gateway) |
| 403 | wrong role, or not the customer / a seller of this order |
| 404 | order not found |
| 405 | unsupported HTTP method |
| 409 | invalid status transition, or concurrent modification |
| 502 | Product Service unavailable or returned invalid data |
| 500 | unexpected error; the message is generic and details stay in the logs |

---

## Configuration

`src/main/resources/application.properties`:

| Property | Default | Notes |
|---|---|---|
| `server.port` | `8084` | `SERVER_PORT` |
| `spring.application.name` | `order-service` | Eureka name; the gateway route `lb://order-service` depends on it |
| `spring.mongodb.uri` | `mongodb://localhost:27021/order_service_db` | `MONGODB_URI`. Docker Compose also sets `SPRING_MONGODB_URI`. |
| `spring.data.mongodb.auto-index-creation` | `true` | **must stay `true`**: the unique idempotency index depends on it |
| `eureka.client.service-url.defaultZone` | `http://localhost:8761/eureka/` | `EUREKA_CLIENT_SERVICE_URL` |
| `product-service.base-url` | `http://product-service` | `PRODUCT_SERVICE_URL`; an **Eureka name, without `/products`** |

`AppConfig` beans:

| Bean | Purpose |
|---|---|
| `loadBalancedRestClientBuilder` | `@LoadBalanced` builder, connect timeout 2 s, read timeout 5 s |
| `clock` | `Clock.systemUTC()`; injected so tests can fix the time |

No Docker Compose changes are needed for this step: the stock endpoints live in the existing product-service container.

---

## Testing

```bash
cd order-service
./mvnw clean verify
```

**144 tests, all passing. Line coverage 98.9%, branch coverage 92.4%** (JaCoCo report: `target/site/jacoco/index.html`).

| Test class | Tests | Covers |
|---|---|---|
| `OrderServiceImplTest` | 48 | create (snapshot, totals, merging, idempotency, the race, stock check and reservation, release on failure, upstream errors), paginated lists, customer and seller access, cancel (with stock release), reorder, status updates (seller cancel releases stock) |
| `OrderControllerTest` | 29 | routing, validation, paging, auth, every error status (MockMvc) |
| `OrderStatusTest` | 20 | allowed and forbidden transitions |
| `OrderPricingTest` | 9 | rounding, floating-point safety, invalid prices, totals |
| `SecurityComponentsTest` | 8 | header parsing, `@CurrentUser` resolution |
| `OrderSearchRepositoryTest` | 8 | generated Mongo queries for each filter, literal regex, skip/limit, count |
| `ProductClientTest` | 14 | product lookup and stock reserve/release: success, 404, 409, 5xx, unreachable, empty body (`MockRestServiceServer`) |
| `DtoTest` | 7 | defensive copies, date-range validation, page defaults |
| `OrderServiceApplicationTests` | 1 | Spring context starts |

The tests don't need MongoDB, Eureka or Product Service. Repositories and the product client are mocked or use mock HTTP servers, and time is fixed with `Clock.fixed(...)`.

---

## Known limitations

| Limitation | Impact | Possible follow-up |
|---|---|---|
| Stock is reserved before the order is saved, **not in one transaction** | if order-service crashes between reserving and saving, or a release fails, units stay taken (logged at `ERROR`) | outbox / event-based reservation |
| A seller editing a product sets `quantity` directly | an edit at the same moment as an order can overwrite that order's decrement | change stock by delta in Product Service |
| **One status per order** | in a multi-seller order, any of its sellers changes the status for everyone | status per seller or per item |
| No **system** role for status changes | only sellers move orders forward | a trusted internal channel (e.g. Kafka events), not a header role |
| Date filters use **UTC days** | an order at 00:30 Morocco time can appear under the previous day | accept the client's time zone |
| No integration tests against a **real MongoDB** | indexes and queries are checked through generated queries, not a live database | Testcontainers, once supported in the Jenkins environment |
| No `product-service` instance in Eureka → **500** instead of 502 | wrong status code when product-service is down or not yet registered | also map `IllegalStateException` in `ProductClient` |
