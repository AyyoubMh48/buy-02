# Buy01 - Microservices E-Commerce Platform

A scalable, containerized e-commerce backend platform built with **Java 17**, **Spring Boot 3**, **Spring Cloud (Eureka & Gateway)**, and **MongoDB**.

---

## 🏗️ System Architecture

```
                               ┌──────────────────────────────────┐
                               │       Client / Web Application    │
                               └────────────────┬─────────────────┘
                                                │
                                       https://localhost:4200
                                                │
                                                ▼
                               ┌──────────────────────────────────┐
                               │   API Gateway Service (8080)     │
                               │  - JWT Verification              │
                               │  - User Header Forwarding        │
                               └────────────────┬─────────────────┘
                                                │
                 ┌──────────────────────────────┼──────────────────────────────┐
                 │                              │                              │
                 ▼                              ▼                              ▼
  ┌─────────────────────────────┐ ┌─────────────────────────────┐ ┌─────────────────────────────┐
  │   User Service (8081)       │ │  Product Service (8082)     │ │   Media Service (8083)      │
  │  - Auth & JWT Generation    │ │  - Product Catalog (CRUD)   │ │  - File Uploads (≤ 2MB)     │
  │  - User Profile Management  │ │  - Seller Ownership Checks  │ │  - Image Serving            │
  └──────────────┬──────────────┘ └──────────────┬──────────────┘ └──────────────┬──────────────┘
                 │                               │                               │
                 └───────────────────────────────┼───────────────────────────────┘
                                                 │
                                                 ▼
                               ┌──────────────────────────────────┐
                               │     Discovery Service (8761)     │
                               │     - Eureka Service Registry    │
                               └──────────────────────────────────┘

                               ┌──────────────────────────────────┐
                               │       Apache Kafka (9092)        │
                               │ IMAGE_UPLOADED / PRODUCT_CREATED│
                               └──────────────────────────────────┘
```

---

## 📋 Services Overview

| Service Name | Port | Description |
| :--- | :--- | :--- |
| **Discovery Service** | `8761` | Eureka Server for microservice registration & dynamic lookup. |
| **API Gateway** | `8080` | Entry point for all clients. Handles JWT verification & request routing. |
| **User Service** | `8081` | Authentication (`/auth/register`, `/auth/login`), profile management (`/me`). |
| **Product Service** | `8082` | Product catalog CRUD (`/products`), seller ownership rules, and image linking. |
| **Media Service** | `8083` | Image uploads validation (MIME `image/*`, size $\le 2\text{MB}$) and image serving (Cloudinary / Storage). |
| **Frontend App** | `4200` | Angular Single Page Application with Auth pages, Seller dashboard, and Product listing. |
| **MongoDB (users)** | `27017` | User database; host access on localhost only. |
| **MongoDB (products)** | `27019` | Product database; host access on localhost only. |
| **MongoDB (media)** | `27020` | Media database; host access on localhost only. |
| **Apache Kafka** | `9092` | Event streaming for media uploads and product creation. |

---

## 🚀 How to Run the Platform

### MongoDB connection links

After changing port mappings, apply them from the project root:

```bash
docker compose up -d product-mongodb media-mongodb user-mongodb
```

Use these URI templates in MongoDB Compass or mongosh, replacing `${...}` with
the corresponding values from the root `.env` file. Percent-encode any special
characters in usernames and passwords when inserting them into a URI.

```text
mongodb://${USER_MONGO_USERNAME}:${USER_MONGO_PASSWORD}@localhost:27017/${USER_MONGO_DATABASE}?authSource=${USER_MONGO_DATABASE}
mongodb://${PRODUCT_MONGO_USERNAME}:${PRODUCT_MONGO_PASSWORD}@localhost:27019/${PRODUCT_MONGO_DATABASE}?authSource=${PRODUCT_MONGO_DATABASE}
mongodb://${MEDIA_MONGO_USERNAME}:${MEDIA_MONGO_PASSWORD}@localhost:27020/${MEDIA_MONGO_DATABASE}?authSource=${MEDIA_MONGO_DATABASE}
```

Application containers continue to use their respective MongoDB service names
on port `27017`. The separate `media-service/docker-compose.yml` defines an
independent media database on port `27018`, with connection URI
`mongodb://root:example@localhost:27018/media_db?authSource=admin`.

### Option 1: Run with Docker Compose (Recommended)

To build and run all microservices and the database together in isolated containers:

```bash
# 1. Build and start all services
docker compose up --build

# 2. To stop all running services
docker compose down
```

> **Troubleshooting: Container Name Conflict**  
> If you get `Error response from daemon: Conflict. The container name "/buy01-mongodb" is already in use`, an old standalone container is running. Remove it with:
> ```bash
> docker rm -f buy01-mongodb buy01-discovery buy01-user-service buy01-gateway buy01-product-service
> ```
> Then run `docker compose up --build` again.

Once running, verify service health:
* **Eureka Dashboard**: [http://localhost:8761](http://localhost:8761)
* **API Gateway Health**: [https://localhost:8443/actuator/health](https://localhost:8443/actuator/health) (local certificate)
* **Frontend**: [https://localhost:4200](https://localhost:4200) (local certificate)
* **Kafka**: `localhost:9092`

### Kafka Events

Kafka runs as a single-node KRaft broker in Docker Compose. The application services connect to it internally using `kafka:9092`.

| Topic | Producer | Published when |
| :--- | :--- | :--- |
| `IMAGE_UPLOADED` | Media Service | An image is uploaded to Cloudinary and its metadata is saved to MongoDB. |
| `PRODUCT_CREATED` | Product Service | A seller creates a product and it is saved to MongoDB. |

List the available topics:

```bash
docker compose exec kafka kafka-topics \
   --bootstrap-server localhost:9092 \
   --list
```

Watch image upload events:

```bash
docker compose exec kafka kafka-console-consumer \
   --bootstrap-server localhost:9092 \
   --topic IMAGE_UPLOADED \
   --from-beginning
```

Watch product creation events:

```bash
docker compose exec kafka kafka-console-consumer \
   --bootstrap-server localhost:9092 \
   --topic PRODUCT_CREATED \
   --from-beginning
```

Keep a consumer running, then upload an image or create a product through the frontend/API. A JSON event should appear in the consumer terminal.

---

### Option 2: Run Microservices Locally for Development

#### Prerequisites
* **Java 17** or higher installed (`java -version`)
* **Docker** running (for MongoDB)

#### Step 1: Start MongoDB
```bash
docker run -d --name buy01-mongodb -p 27017:27017 mongo:7.0
```

#### Step 2: Start Services in Order

Open separate terminal windows for each service:

1. **Start Discovery Service**:
   ```bash
   cd discovery
   ./mvnw spring-boot:run
   ```
   *Wait until Eureka starts at `http://localhost:8761`.*

2. **Start User Service**:
   ```bash
   cd user-service
   ./mvnw  -boot:run
   ```

3. **Start Product Service**:
   ```bash
   cd product-service
   ./mvnw spring-boot:run
   ```

4. **Start API Gateway**:
   ```bash
   cd gateway
   ./mvnw spring-boot:run
   ```

Kafka is started automatically when using Docker Compose. When running services locally, start a Kafka broker separately and set:

```bash
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

---

## ⚙️ Environment Configuration (`.env`)

Each service supports `.env` configuration files via `spring.config.import=optional:file:./.env[.properties]`.

Examples are available in each service directory:
* `user-service/.env.example`
* `gateway/.env.example`
* `discovery/.env.example`
* `product-service/.env.example`

### Common Environment Variables

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `PORT` | Service specific | Port number for the service. |
| `EUREKA_CLIENT_SERVICE_URL` | `http://localhost:8761/eureka/` | URL of the Eureka Discovery server. |
| `JWT_SECRET` | Secret Key | Secret key used to sign and verify JWT tokens. |
| `JWT_EXPIRATION` | `3600000` (1 hour) | Token validity period in milliseconds. |
| `MONGODB_URI` | `mongodb://localhost:27017/...` | MongoDB connection URI. |

---

## 🔌 API Routes via Gateway (`https://localhost:8443`)

### Authentication & Profile (`user-service`)
* `POST /auth/register` – Register a new user (`role`: `CLIENT` or `SELLER`).
* `POST /auth/login` – Login to retrieve JWT Bearer token.
* `GET /me` – Fetch current user profile (*requires `Authorization: Bearer <token>`*).
* `PUT /me` – Update user profile details.

### Product Management (`product-service`)
* `GET /products` – Fetch all products (Public).
* `GET /products/{id}` – Fetch product by ID (Public).
* `POST /products` – Create a product (*Seller only*).
* `PUT /products/{id}` – Update product details (*Seller & Owner only*).
* `DELETE /products/{id}` – Delete product (*Seller & Owner only*).
* `GET /products/myshiit` – Fetch seller's own products (*Seller only*).
* `PUT /products/{id}/images` – Link uploaded image URLs to a product.

### Media Uploads (`media-service`)
* `POST /media/images` – Upload image file ($\le 2\text{MB}$, MIME `image/*`) (*Seller only*).
* `GET /media/images/{id}` – View/download uploaded image.
