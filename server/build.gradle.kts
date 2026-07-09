import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    id("org.springframework.boot") version "4.0.6"
    id("io.spring.dependency-management") version "1.1.7"
    kotlin("jvm") version "2.3.21"
    kotlin("plugin.spring") version "2.3.21"
    kotlin("plugin.jpa") version "2.3.21"
}

group = "com.stockreport"
version = "0.0.1-SNAPSHOT"
description = "stock-report server"

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}

repositories {
    mavenCentral()
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter")
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.springframework.boot:spring-boot-starter-flyway")
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.jetbrains.kotlin:kotlin-reflect")

    runtimeOnly("org.postgresql:postgresql")
    runtimeOnly("org.flywaydb:flyway-database-postgresql")

    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.springframework.boot:spring-boot-testcontainers")
    testImplementation("org.springframework.restdocs:spring-restdocs-mockmvc")
    testImplementation("org.jetbrains.kotlin:kotlin-test-junit5")
    testImplementation("org.testcontainers:testcontainers-junit-jupiter")
    testImplementation("org.testcontainers:testcontainers-postgresql")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_21)
        freeCompilerArgs.add("-Xjsr305=strict")
    }
}

tasks.withType<Test> {
    useJUnitPlatform()
}
