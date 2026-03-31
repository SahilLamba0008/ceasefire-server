# Stage 1: Build
FROM eclipse-temurin:21-jdk AS build

WORKDIR /app

ARG GRADLE_VERSION=8.14
RUN apt-get update \
    && apt-get install -y wget unzip \
    && wget -q "https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip" -O /tmp/gradle.zip \
    && unzip -q /tmp/gradle.zip -d /opt \
    && ln -s "/opt/gradle-${GRADLE_VERSION}/bin/gradle" /usr/bin/gradle \
    && rm -rf /tmp/gradle.zip /var/lib/apt/lists/*

COPY build.gradle settings.gradle ./
COPY src ./src

RUN gradle clean bootJar -x test --no-daemon

# Stage 2: Run
FROM eclipse-temurin:21-jre-jammy

WORKDIR /app

COPY --from=build /app/build/libs/*.jar app.jar

RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
