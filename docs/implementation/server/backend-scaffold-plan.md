# 백엔드 스캐폴드 계획

상태: 초안

## 범위

`server/` 아래에 신규 백엔드 프로젝트를 생성한다.

이번 단계는 Spring Boot 백엔드의 실행 가능한 기본 골격을 만드는 데 한정한다. 조회 API, 도메인 모델, DB 스키마 정의는 포함하지 않는다.

## 결정 사항

- 언어: Kotlin
- 프레임워크: Spring Boot
- 빌드 도구: Gradle
- 패키지명: `com.stockreport`
- 프로젝트 위치: `server/`
- 인증: MVP 제외 범위 유지
- API 구현: 제외
- DB 스키마 정의: 제외
- Flyway: 의존성과 기본 설정만 포함
- JPA: 의존성과 기본 설정만 포함
- 데이터베이스: PostgreSQL 연결을 전제로 설정

## 초기 파일

- `settings.gradle.kts`
- `build.gradle.kts`
- Gradle Wrapper 파일
- Spring Boot 애플리케이션 진입점
- 기본 테스트 파일
- `application.yml`
- `application-local.yml`
- `application-test.yml`
- `.gitignore`

## 구현 절차

1. `server/` 디렉터리에 Kotlin Spring Boot 프로젝트 골격을 생성한다.
2. Gradle Kotlin DSL 기반 빌드 설정을 추가한다.
3. Spring Boot, Kotlin, JPA, Flyway, PostgreSQL 드라이버 의존성을 구성한다.
4. `com.stockreport` 패키지 아래 애플리케이션 진입점을 추가한다.
5. 환경별 설정 파일을 추가하되 실제 운영 비밀값은 포함하지 않는다.
6. Flyway는 활성화 가능한 상태로 두되 초기 마이그레이션 SQL은 작성하지 않는다.
7. 조회 API, Controller, Service, Repository, Entity는 생성하지 않는다.
8. 기본 컨텍스트 로딩 테스트를 추가한다.
9. 가능하면 Gradle 테스트로 프로젝트 생성 결과를 검증한다.

## 제외 범위

- DB 테이블, 인덱스, 제약조건, 마이그레이션 SQL 정의
- 조회 API Controller 구현
- DTO, Entity, Repository, Service 구현
- 시장 개요, 골든크로스, 종목 상세, 업종, 과거 리포트 API 구현
- Python 배치 연동
- 기술지표 또는 신호 계산 로직
- 인증 및 권한 처리
- Docker Compose 구성
- 운영 배포 설정
- 모니터링, 로깅 정책 세부화

## 검증 계획

- `./gradlew test` 실행
- 테스트 또는 빌드 실패 시 원인을 보고하고 임의로 범위를 확장하지 않는다.
- 네트워크 또는 로컬 Gradle 환경 문제로 검증이 불가능하면 실행하지 못한 이유를 보고한다.

## 위험 요소

- Spring Boot 프로젝트 생성 또는 의존성 해석에는 네트워크 접근이 필요할 수 있다.
- 로컬 JDK 버전이 Spring Boot 요구사항과 맞지 않을 수 있다.
- Flyway 의존성은 포함하지만 스키마 파일이 없으므로 실제 DB 연결 검증은 이번 단계에서 수행하지 않는다.
- JPA 의존성은 포함하지만 Entity가 없으므로 도메인 매핑 검증은 이후 단계에서 수행해야 한다.
