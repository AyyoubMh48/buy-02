# ==========================================
# Stage 1: Build the Application
# ==========================================
FROM maven:3.9.6-eclipse-temurin-17 AS builder

WORKDIR /app

# Copy pom.xml first to leverage Docker layer caching for dependencies
COPY pom.xml .
RUN mvn dependency:go-offline -B

# Copy source code and build the executable JAR
COPY src ./src
RUN mvn package -DskipTests

# ==========================================
# Stage 2: Minimal Production Runtime
# ==========================================
FROM eclipse-temurin:17-jre-alpine

WORKDIR /app

# Create non-root user and media upload directory for security
RUN addgroup -S appgroup && adduser -S appuser -G appgroup && \
mkdir -p /app/uploads && \
chown -R appuser:appgroup /app

# Copy compiled JAR from builder stage
COPY --from=builder /app/target/*.jar app.jar
RUN chown appuser:appgroup app.jar

# Switch to non-root user
USER appuser

# Expose service port (matches server.port in application.yml)
EXPOSE 8083

# Declare volume mount point for file persistence
VOLUME ["/app/uploads"]

# Health check endpoint via Actuator
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
CMD wget --quiet --tries=1 --spider http://localhost:8083/actuator/health || exit 1

# Start Spring Boot service
ENTRYPOINT ["java", "-jar", "app.jar"]