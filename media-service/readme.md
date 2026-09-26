# Buy01 - Media Service

The **Media Service** is a microservice responsible for handling secure file uploads, image validation, metadata management, and Cloudinary CDN integration for the **Buy01** e-commerce platform.

---

## Technical Stack

* **Framework:** Spring Boot 3.x (Java 17)
* **Database:** MongoDB (Metadata Persistence)
* **Cloud Storage:** Cloudinary SDK
* **File Validation:** Apache Tika (MIME type sniffing)
* **Event Streaming:** Apache Kafka (`IMAGE_UPLOADED` topic)
* **Containerization:** Docker & Docker Compose

---

## Features

* **Cloud Storage Integration:** Direct image uploads to Cloudinary CDN with automatic HTTPS URL generation.
* **Security & MIME Sniffing:** Genuine file type validation using Apache Tika to block extension spoofing before network operations.
* **File Size Guards:** Strict payload size limits (2 MB maximum).
* **Metadata Persistence:** Stores upload logs, public IDs, CDN paths, and owner details in MongoDB.
* **Event-Driven Architecture:** Emits Kafka events upon successful image uploads for downstream microservices.

---

## Getting Started

### Prerequisites

* Java 17+
* Maven 3.8+
* MongoDB running locally or via Docker (`localhost:27017`)
* Apache Kafka running locally or via Docker (`localhost:9092`)
* Cloudinary Account Credentials

---

## Configuration

Set your Cloudinary API credentials in `src/main/resources/application.yml` or export them as environment variables:

```yaml
server:
  port: 8082

spring:
  application:
    name: media-service
  data:
    mongodb:
      uri: ${SPRING_DATA_MONGODB_URI:mongodb://localhost:27017/media_db}
  kafka:
    bootstrap-servers: ${SPRING_KAFKA_BOOTSTRAP_SERVERS:localhost:9092}

cloudinary:
  cloud-name: ${CLOUDINARY_CLOUD_NAME:your_cloud_name}
  api-key: ${CLOUDINARY_API_KEY:your_api_key}
  api-secret: ${CLOUDINARY_API_SECRET:your_api_secret}

eureka:
  client:
    enabled: false
```

## API Documentation
  1. Upload Image
    Uploads an image to Cloudinary after running size and Apache Tika validation.

  * URL: /api/v1/media/images

  * Method: POST

  * Consumes: multipart/form-data

  * Headers:

    * X-User-Id (Optional): Owner user ID (Default: anonymous)

  * Body:

    * file (File, Required): Image payload (PNG, JPEG, WebP, GIF <= 2MB)

  #### Example Request (cURL)
  ```
  curl -X POST http://localhost:8082/api/v1/media/images \
  -H "X-User-Id: user_123" \
  -F "file=@/path/to/image.png"
  ```

  #### Response (200 OK)

  ```
  {
    "id": "66d52f8a123456789",
    "url": "[https://res.cloudinary.com/your_cloud/image/upload/v1725286400/buy01_products/abc123xyz.jpg](https://res.cloudinary.com/your_cloud/image/upload/v1725286400/buy01_products/abc123xyz.jpg)",
    "filename": "image.png",
    "contentType": "image/png",
    "size": 154200
  }
  ```

  2. Get Image Metadata
  Retrieves stored metadata for an image record by ID.

   * URL: /api/v1/media/images/{id}

   * Method: GET

  #### Response (200 OK)

  ```
  {
    "id": "66d52f8a123456789",
    "url": "[https://res.cloudinary.com/your_cloud/image/upload/v1725286400/buy01_products/abc123xyz.jpg](https://res.cloudinary.com/your_cloud/image/upload/v1725286400/buy01_products/abc123xyz.jpg)",
    "filename": "image.png",
    "contentType": "image/png",
    "size": 154200
  }
  ```
  3. Delete Image
  Deletes an asset from Cloudinary CDN and removes its metadata from MongoDB.

    * URL: /api/v1/media/images/{id}

    * Method: DELETE

    * Headers:

      * X-User-Id (Required): Must match the image uploader ID

  #### Response (204 No Content)
  #### Running with Docker Compose
  To spin up MongoDB, Kafka, and the Media Service simultaneously:

  ```
  docker compose up --build -d
  docker compose up -d
  ```

  ```
  docker compose logs -f media-service
  ```

  ```
  docker run -d --name mongodb-media -p 27017:27017 mongo:latest
  ```

##### Remove old conflicting container
```
docker rm -f mongo-media
```

##### Confirm Mongo is up on mongo:7
```
docker ps
```

##### Build the app image (note the trailing dot!)
```
docker build -t media-service .
```

##### Run the app container on the same network
```
docker run -d \
  --name media-service \
  --network buy01-network \
  -p 8082:8082 \
  -e SPRING_DATA_MONGODB_URI="mongodb://root:example@mongo-media:27017/media_db?authSource=admin" \
  media-service
```

##### Watch logs
```
docker logs -f media-service
```