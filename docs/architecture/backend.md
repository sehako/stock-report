# 백엔드 패키지 아키텍처 지침

## 기본 원칙

패키지는 기능 또는 도메인 단위로 구성한다.

각 도메인 패키지는 다음 계층을 포함한다.

```text
{domain}
├── presentation
├── application
├── domain
├── infrastructure
└── util
```

## 작업 트리

```text
{domain}
├── presentation
│   ├── {Domain}Controller
│   └── request
│       ├── Create{Domain}Request
│       └── Update{Domain}Request
│
├── application
│   ├── {Domain}Service
│   ├── dto
│   │   ├── Create{Domain}Dto
│   │   └── Update{Domain}Dto
│   └── response
│       ├── {Domain}Response
│       └── {Domain}DetailResponse
│
├── domain
│   ├── {Domain}
│   ├── {Domain}Repository
│   └── {Domain}Status
│
├── infrastructure
│   ├── persistence
│   │   ├── {Domain}JpaRepository
│   │   └── {Domain}RepositoryImpl
│   └── client
│       └── {ExternalService}Client
│
└── util
```

## 계층별 책임

### presentation

- HTTP 요청과 응답을 처리한다.
- 요청 Body 객체는 `request` 패키지에 작성한다.
- 요청 객체 이름은 `Request`로 끝낸다.
- 비즈니스 로직을 작성하지 않는다.

```text
CreateUserRequest
UpdateUserRequest
```

### application

- 유스케이스와 비즈니스 흐름을 처리한다.
- 입력값은 `dto` 패키지에서 관리한다.
- 반환값은 `response` 패키지에서 관리한다.
- 반환 객체 이름은 `Response`로 끝낸다.
- 트랜잭션은 application 계층에서 관리한다.

```text
CreateUserDto
UpdateUserDto
UserResponse
UserDetailResponse
```

### domain

- 엔티티, 값 객체, 상태, 핵심 비즈니스 규칙을 관리한다.
- Repository 인터페이스를 정의한다.
- 엔티티 상태 변경은 도메인 메서드를 통해 처리한다.

### infrastructure

- JPA, 외부 API, Kafka 등 외부 기술 연동을 담당한다.
- domain에 정의된 Repository 인터페이스를 구현한다.

### util

- 해당 도메인에서만 사용하는 단순 보조 기능을 관리한다.
- 비즈니스 규칙은 `util`에 작성하지 않는다.
- 여러 도메인에서 사용하는 기능은 `global.util`에 작성한다.

## 의존성 방향

```text
presentation → application → domain
infrastructure → domain
```

- domain은 presentation과 infrastructure를 의존하지 않는다.
- application은 infrastructure 구현체가 아닌 domain 인터페이스에 의존한다.

## 네이밍 규칙

| 역할                  | 규칙                      |
| --------------------- | ------------------------- |
| Controller            | `{Domain}Controller`      |
| HTTP 요청             | `{Action}{Domain}Request` |
| Application 입력      | `{Action}{Domain}Dto`     |
| 응답                  | `{Domain}Response`        |
| Service               | `{Domain}Service`         |
| Repository 인터페이스 | `{Domain}Repository`      |
| JPA Repository        | `{Domain}JpaRepository`   |
| Repository 구현체     | `{Domain}RepositoryImpl`  |
| 외부 API Client       | `{Service}Client`         |
