# 프론트엔드 아키텍처 지침

## 기본 원칙

패키지는 기능 또는 도메인 단위로 구성한다.

각 도메인 패키지는 다음 구조를 기본으로 한다.

```text
{domain}
├── api
├── model
├── hook
├── ui
└── util
```

페이지 단위 라우팅 컴포넌트는 `pages`에서 관리하고, 여러 도메인에서 사용하는 공통 요소는 `shared`에서 관리한다.

## 작업 트리

```text
src
├── app
│   ├── router
│   ├── provider
│   └── config
│
├── pages
│   └── {Domain}Page
│
├── features
│   └── {domain}
│       ├── api
│       │   ├── {domain}Api
│       │   ├── {domain}Query
│       │   └── {domain}Mutation
│       │
│       ├── model
│       │   ├── {Domain}
│       │   ├── {Domain}Request
│       │   └── {Domain}Response
│       │
│       ├── hook
│       │   └── use{Domain}
│       │
│       ├── ui
│       │   ├── {Domain}List
│       │   ├── {Domain}Item
│       │   └── {Domain}Form
│       │
│       └── util
│
└── shared
    ├── api
    ├── component
    ├── hook
    ├── type
    ├── util
    └── constant
```

## 디렉터리별 책임

### app

- 애플리케이션 전역 설정을 관리한다.
- 라우터, Provider, 환경 설정을 배치한다.
- 도메인 비즈니스 로직을 작성하지 않는다.

### pages

- 라우팅 단위의 페이지 컴포넌트를 관리한다.
- 여러 도메인 컴포넌트를 조합한다.
- 복잡한 API 호출이나 비즈니스 로직을 직접 작성하지 않는다.

### features

- 기능 또는 도메인 단위 코드를 관리한다.
- 특정 도메인에서만 사용하는 API, 타입, 훅, UI를 함께 배치한다.

### api

- 서버 API 호출을 관리한다.
- 조회 로직은 `Query`, 변경 로직은 `Mutation` 이름을 사용한다.
- HTTP 요청과 응답 타입은 `model`에 정의한다.

```text
userApi
userQuery
userMutation
```

### model

- 도메인 타입과 API 요청·응답 타입을 관리한다.
- 서버 데이터 구조와 화면에서 사용하는 상태 모델을 정의한다.

```text
User
CreateUserRequest
UserResponse
```

### hook

- API 호출, 상태 관리, 이벤트 처리 등 화면 로직을 관리한다.
- 커스텀 훅 이름은 `use`로 시작한다.
- 재사용 가능한 화면 동작을 UI 컴포넌트에서 분리한다.

```text
useUser
useUserForm
useUserList
```

### ui

- 도메인과 관련된 화면 컴포넌트를 관리한다.
- API를 직접 호출하지 않고 hook 또는 props를 통해 데이터를 전달받는다.
- 컴포넌트는 가능한 한 하나의 역할만 담당한다.

### util

- 해당 도메인에서만 사용하는 단순 변환 및 보조 기능을 관리한다.
- 상태 관리나 API 호출 로직은 작성하지 않는다.
- 여러 도메인에서 사용하는 기능은 `shared.util`에 작성한다.

### shared

- 둘 이상의 도메인에서 재사용하는 코드를 관리한다.
- 공통 버튼, 입력창, 모달, API 클라이언트, 타입, 훅 등을 배치한다.
- 특정 도메인에 종속된 코드는 배치하지 않는다.

## 의존성 방향

```text
app → pages → features → shared
```

- `shared`는 `features`, `pages`, `app`을 의존하지 않는다.
- `features`는 다른 feature를 직접 의존하지 않는 것을 원칙으로 한다.
- `pages`는 여러 feature를 조합할 수 있다.
- 도메인 간 조합 로직은 `pages` 또는 상위 계층에서 처리한다.

## 컴포넌트 작성 원칙

- 페이지 컴포넌트는 도메인 UI를 조합한다.
- UI 컴포넌트는 렌더링과 사용자 입력 처리를 담당한다.
- API 호출과 복잡한 상태 로직은 hook으로 분리한다.
- 서버 상태와 클라이언트 상태를 구분한다.
- 서버 상태는 Query 라이브러리를 통해 관리한다.
- props 전달이 과도할 때만 Context 또는 상태 관리 도구를 사용한다.

## 디자인 가이드 준수

프론트엔드 UI를 구현하거나 수정할 때는 루트 `DESIGN.md`를 함께 확인한다.

- 화면 레이아웃은 `DESIGN.md`의 Page Shell, Header, Section, Responsive Grid 패턴을 우선한다.
- Tailwind CSS 유틸리티 조합은 `DESIGN.md`에 정의된 Panel, Button, Segmented Control, Search Input, Badge, Table, Chart 패턴을 따른다.
- 색상은 `slate`, `blue`, `emerald`, `rose` 계열의 역할 규칙을 우선한다.
- 가격, 거래량, 등락률, 날짜 등 숫자 데이터에는 `tabular-nums` 적용을 기본으로 한다.
- 페이지 전체를 하나의 카드로 감싸거나, 카드 안에 다시 카드형 패널을 중첩하지 않는다.
- 큰 그림자, 그라데이션 배경, 장식용 blob, 실시간 거래 화면처럼 긴장감 있는 시각 효과는 사용하지 않는다.
- 둘 이상의 화면에서 반복되는 UI 패턴은 `shared/component`에 작성한다.
- 특정 도메인에서만 사용하는 UI는 각 `features/{domain}/ui`에 작성한다.

## 네이밍 규칙

| 역할        | 규칙                      |
| ----------- | ------------------------- |
| 페이지      | `{Domain}Page`            |
| UI 컴포넌트 | `{Domain}{Role}`          |
| 커스텀 훅   | `use{Domain}`             |
| API 모듈    | `{domain}Api`             |
| 조회 정의   | `{domain}Query`           |
| 변경 정의   | `{domain}Mutation`        |
| 요청 타입   | `{Action}{Domain}Request` |
| 응답 타입   | `{Domain}Response`        |
| 도메인 타입 | `{Domain}`                |
| 도메인 유틸 | `{domain}Util`            |
