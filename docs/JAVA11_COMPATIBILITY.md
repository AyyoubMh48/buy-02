# Java compatibility finding — migration deferred

Status: **Java 11 compatibility is unresolved. No migration is being attempted.**
The latest project instruction is to preserve the existing Java and Spring Boot
versions and focus on Nexus. No application source, service POM, compiler setting,
toolchain, wrapper or installed JDK was changed during this follow-up.

All six services still declare Java 17; existing CI selects Java 21. Fresh
`clean verify` runs on the existing Java 21 installation passed all **446 tests**
and produced the six executable JARs. Application classes have major version 61
(Java 17). None of these results demonstrates Java 11 compliance.

## Findings in the actual services

All six services inherit Spring Boot 4.1.x and Spring Cloud 2025.1.2. The
[Spring Boot system requirements](https://docs.spring.io/spring-boot/4.1/system-requirements.html)
require at least Java 17. Local inspection also found major version 61 in the
actual Spring Boot 4.1.0/4.1.1 and Eureka server 5.0.2 classes in the build cache.
Java 11 accepts class version 55, so changing only the compiler target cannot
make these dependencies usable.

| Service | Additional concrete incompatibilities |
| --- | --- |
| discovery | Its application source is simple, but the Boot parent, Eureka server and Cloud dependency bytecode already require Java 17. No newer-language syntax was found by the targeted source scan. |
| gateway | `src/main/java/com/buy01/gateway/security/SecurityConfig.java:65` calls `Stream.toList()`; `exception/GlobalExceptionHandler.java:15` uses pattern matching for instanceof and Spring ErrorResponse. `security/ApiErrorWriter.java:7` imports Jackson 3's `tools.jackson.databind.ObjectMapper`. Routing properties use `spring.cloud.gateway.server.webmvc.routes`; this is tied to the existing Cloud MVC gateway, not a compiler switch. Servlet filters use Jakarta packages. |
| user-service | `src/main/java/com/buy01/user_service/dto/UpdateProfileRequest.java:7` and `dto/external/MediaMetadataResponse.java:3` declare records. `client/MediaServiceClient.java:5` uses Spring RestClient. `security/ApiErrorWriter.java:7` imports Jackson 3. Servlet/validation code uses Jakarta packages, and the exception handler uses newer Spring ErrorResponse. |
| product-service | Records include `src/main/java/com/buy01/product_service/security/AuthenticatedUser.java:6`. `service/ProductService.java` uses Stream.toList(); `repository/ProductSearchRepository.java:71` uses switch arrow cases. `client/MediaServiceClient.java:6` uses RestClient; the exception handler uses newer Spring ErrorResponse. Servlet/validation code uses Jakarta packages. |
| media-service | Records in `src/main/java/com/buy_01/media/events/ImageUploadedEvent.java:5` and `events/ProductImagesChangedEvent.java:6`; pattern instanceof/Spring ErrorResponse in `exception/GlobalExceptionHandler.java:69`. Its actual Tika 4.0.0 `org/apache/tika/Tika.class` also has major version 61. |
| order-service | Records throughout DTOs/models, switch arrow cases in `src/main/java/com/buy01/order_service/models/OrderStatus.java:17`, Stream.toList() and pattern instanceof. Clients use RestClient; `exception/GlobalExceptionHandler.java` uses HttpStatusCode, ParameterErrors and HandlerMethodValidationException. Tests use text blocks, String.formatted, Boot ServiceConnection, MockitoBean and Boot modular test APIs. |

Records, Stream.toList and instanceof patterns are post-Java-11 features.
Switch expressions/arrow cases, text blocks and String.formatted also arrived
after Java 11. Jakarta imports are a framework migration concern, not proof that
every Jakarta library intrinsically requires Java 17.

Jackson 3's ObjectMapper and Tika 4's Tika class were inspected in the actual
local dependency JARs and have class version 61. Conversely, the inspected
Testcontainers 2.0.5 GenericContainer class had class version 52; the report does
**not** claim that every Testcontainers class is intrinsically Java-17-only.
The existing Spring Boot test integrations still prevent this application's
unchanged test configuration from running on Java 11.

## Earlier diagnostic evidence

Before migration work was explicitly deferred, diagnostics ran on temporary
copies under `/tmp/buy02-nexus-followup/java11/`, using the previously downloaded
Temurin 11 JDK. They did not modify working service POMs or install/change Java.
All six normal Java 11 build attempts failed. All six diagnostic compiler-target
overrides also failed. The failures include unsupported release 17, post-Java-11
syntax, and dependency class version 61 versus Java 11's expected 55.

The per-service logs are `/tmp/buy02-nexus-followup/java11-SERVICE.log` and
`java11-SERVICE-override.log`. These are failed diagnostic attempts, not successful
Java 11 tests. No further Java 11 work is part of the current Nexus task.

A Java 11 migration cannot be a safe Nexus-only change while retaining the current
frameworks. It would require a separately agreed application/framework effort.
No downgrade, source rewrite, dependency replacement or migration plan is applied.
