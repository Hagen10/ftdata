# Build stage
FROM eclipse-temurin:21-jdk-jammy AS builder

WORKDIR /build

# Copy gradle files
COPY gradle /build/gradle
COPY gradlew /build/gradlew
COPY settings.gradle.kts /build/settings.gradle.kts
COPY gradle.properties /build/gradle.properties

# Copy app build files
COPY app/build.gradle.kts /build/app/build.gradle.kts

# Copy source code
COPY app/src /build/app/src

# Build the application
RUN chmod +x /build/gradlew && \
    /build/gradlew bootJar -p app --no-daemon

# Runtime stage
FROM eclipse-temurin:21-jre-jammy

WORKDIR /app

# Copy the built jar from builder stage
COPY --from=builder /build/app/build/libs/*.jar app.jar

# Create a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port 8080
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD java -cp app.jar org.springframework.boot.loader.launch.JarLauncher --actuator.health || exit 1

# Run the application
ENTRYPOINT ["java", "-jar", "app.jar"]
