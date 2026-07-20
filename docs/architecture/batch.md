# 배치 아키텍처 지침

## 기본 원칙

Python 배치는 작업 단위와 공통 기능을 분리한다.

작업 단위는 하나의 배치 목적을 나타낸다. 예를 들어 거래량 상위 종목 선정, 종목 일봉 수집, 지수 일봉 수집은 서로 다른 작업 단위로 관리한다.

각 배치 작업 패키지는 다음 계층을 포함한다.

```text
{job}
├── application
├── domain
├── infrastructure
└── util
```

여러 배치 작업에서 함께 사용하는 설정, 데이터베이스 연결, 로깅, 공통 클라이언트 보조 기능은 `shared`에서 관리한다.

## 작업 트리

```text
app/batch
├── src
│   ├── batch
│   │   └── main.py
│   │
│   ├── jobs
│   │   └── {job}
│   │       ├── application
│   │       │   ├── {job}_runner.py
│   │       │   └── dto.py
│   │       │
│   │       ├── domain
│   │       │   ├── model.py
│   │       │   ├── service.py
│   │       │   └── repository.py
│   │       │
│   │       ├── infrastructure
│   │       │   ├── persistence
│   │       │   │   └── {job}_repository.py
│   │       │   └── client
│   │       │       └── {external_service}_client.py
│   │       │
│   │       └── util
│   │
│   └── shared
│       ├── config
│       ├── database
│       ├── logging
│       └── util
│
├── tests
│   ├── jobs
│   │   └── {job}
│   └── shared
│
└── pyproject.toml
```

## 디렉터리별 책임

### jobs

- 배치 작업 단위 코드를 관리한다.
- 각 작업은 하나의 명확한 실행 목적을 가진다.
- 다른 작업 패키지의 내부 구현을 직접 의존하지 않는다.
- 작업 간 조합이 필요하면 상위 실행 진입점 또는 `shared`의 공통 인터페이스를 통해 처리한다.

### main.py

- 배치 실행 진입점이다.
- 명령행 인자와 환경 설정을 읽고 실행할 작업 runner를 선택한다.
- 도메인 규칙, SQL, 외부 API 호출 세부 구현을 작성하지 않는다.
- 지정 실행 옵션이 추가되더라도 실제 처리 흐름은 각 작업의 application 계층에 위임한다.
- 실행 파일은 `app/batch/src/batch/main.py`에 두고, 가상환경을 활성화한 뒤 `python -m batch.main`으로 실행한다.

### application

- 배치 유스케이스와 실행 흐름을 처리한다.
- 외부 데이터 조회, 도메인 규칙 실행, 저장소 호출 순서를 조합한다.
- 트랜잭션 경계를 관리한다.
- 실행 결과 요약과 작업 단위 로그를 남긴다.
- 데이터베이스 SQL이나 외부 API 호출 세부 구현을 직접 작성하지 않는다.

### domain

- 배치 작업의 핵심 규칙을 관리한다.
- 외부 라이브러리, 데이터베이스, 네트워크 호출에 의존하지 않는 순수 로직을 우선 배치한다.
- 도메인 모델, 값 검증, 정렬, 필터링, 중복 처리 규칙을 작성한다.
- 저장소 인터페이스를 정의한다.

### infrastructure

- 외부 기술 연동을 담당한다.
- `persistence`는 RDB 저장과 조회를 담당한다.
- `client`는 `FinanceDataReader` 같은 외부 데이터 소스 호출을 담당한다.
- `domain`에 정의된 저장소 인터페이스를 구현한다.
- 외부 데이터 구조를 도메인에서 사용하는 구조로 변환한다.

### util

- 해당 배치 작업에서만 사용하는 단순 보조 기능을 관리한다.
- 핵심 비즈니스 규칙은 `util`에 작성하지 않는다.
- 둘 이상의 작업에서 재사용하는 기능은 `shared.util` 또는 더 구체적인 `shared` 하위 패키지에 작성한다.

### shared

- 여러 배치 작업에서 재사용하는 공통 기능을 관리한다.
- 설정 로딩, 데이터베이스 연결 생성, 로깅 설정, 공통 날짜 변환 같은 기능을 배치한다.
- 특정 작업의 비즈니스 규칙을 작성하지 않는다.
- `shared`는 개별 `jobs` 패키지에 의존하지 않는다.

## 의존성 방향

```text
application → domain
application → infrastructure
infrastructure → domain
jobs → shared
```

- `domain`은 `application`, `infrastructure`, `shared.database`를 의존하지 않는다.
- `application`은 실행 흐름을 조합하기 위해 `domain`과 `infrastructure`를 의존할 수 있다.
- `infrastructure`는 `domain`의 모델과 인터페이스를 의존할 수 있다.
- `shared`는 `jobs`를 의존하지 않는다.
- 서로 다른 `jobs` 패키지는 직접 의존하지 않는다.

## 실행 진입점 원칙

- 배치 실행 진입점은 작업 단위 runner를 호출한다.
- 옵션 없는 기본 실행은 MVP 기본 배치 흐름을 수행한다.
- 지정 종목, 지정 지수, 지정 기간 재수집 옵션은 별도 이슈에서 추가한다.
- 실행 인자는 application 계층에서 사용할 명령 객체 또는 DTO로 변환한다.
- 진입점에는 도메인 규칙, SQL, 외부 API 호출 세부 구현을 작성하지 않는다.

## 설정 및 환경 변수

- 데이터베이스 접속 정보, 실행 환경, 로그 레벨은 환경 변수 또는 설정 파일로 주입한다.
- 비밀번호, API 키, 토큰 등 민감정보를 코드나 문서에 직접 작성하지 않는다.
- 로컬 개발용 실제 환경 변수 값은 Git에서 제외되는 `app/batch/.env`에만 기록하고, 문서에는 변수명과 값의 형식만 기록한다.
- 설정 값 검증은 배치 시작 시점에 수행한다.
- 누락된 필수 설정은 명확한 오류 메시지와 함께 배치를 중단한다.

## Python 의존성 및 가상환경

- 배치 프로젝트의 Python 의존성은 `app/batch/pyproject.toml`에 기록한다.
- 의존성은 저장소나 전역 Python 환경에 직접 설치하지 않고, `app/batch/.venv` 가상환경에 설치한다.
- `.venv`는 로컬 실행 산출물이므로 Git에 커밋하지 않는다.
- 새 개발 환경에서는 `app/batch`에서 `python -m venv .venv`로 가상환경을 만들고, `. .venv/bin/activate`로 활성화한 뒤 설치와 테스트 명령을 실행한다.

## 트랜잭션 및 멱등성

- 데이터베이스 변경은 application 계층에서 작업 단위 트랜잭션 경계를 정한다.
- 같은 배치를 같은 입력으로 여러 번 실행해도 최종 데이터 상태가 같아야 한다.
- 중복 방지는 데이터베이스 유니크 제약과 upsert를 우선 사용한다.
- 일부 데이터만 저장된 상태가 사용자 조회 결과에 노출되지 않도록 관련 변경을 하나의 트랜잭션으로 묶는다.
- 배치에서 제외된 데이터는 이슈 요구사항이 삭제를 명시하지 않는 한 삭제하지 않고 상태 값으로 구분한다.

## 오류 처리 및 로깅

- 배치 시작, 주요 단계 완료, 저장 결과, 실패 사유를 로그로 남긴다.
- 외부 데이터 조회 실패와 데이터베이스 저장 실패는 구분해 기록한다.
- 한 항목 실패를 계속 진행할지 전체 배치를 중단할지는 이슈별 요구사항에 따른다.
- 오류 로그에는 재실행에 필요한 식별자와 원인을 포함한다.
- 민감정보가 로그에 남지 않도록 한다.

## 테스트 작성 원칙

- `domain` 로직은 외부 네트워크와 데이터베이스 없이 단위 테스트한다.
- `application`은 외부 클라이언트와 저장소를 대체 객체로 바꿔 실행 흐름을 테스트한다.
- `infrastructure.persistence`는 가능한 경우 테스트 데이터베이스로 upsert, 트랜잭션, 중복 방지를 검증한다.
- `infrastructure.client`는 외부 서비스 호출을 직접 수행하는 테스트보다 응답 변환 로직 테스트를 우선한다.
- 실제 외부 네트워크 호출이 필요한 검증은 수동 검증이나 별도 통합 검증으로 분리한다.

## 네이밍 규칙

| 역할                  | 규칙                         |
| --------------------- | ---------------------------- |
| 작업 패키지           | `{job}`                      |
| 실행 조합             | `{job}_runner.py`            |
| Application 입력      | `{Action}{Job}Command`       |
| 실행 결과             | `{Job}Result`                |
| 도메인 모델           | `{Domain}`                   |
| 도메인 서비스         | `{domain}_service.py`        |
| Repository 인터페이스 | `{Domain}Repository`         |
| Repository 구현체     | `{job}_repository.py`        |
| 외부 API Client       | `{external_service}_client.py` |
| 작업 전용 유틸        | `{job}_util.py`              |

## 이슈 02 적용 예시

거래량 상위 200개 종목 선정 배치는 `stock_universe` 작업 패키지로 둔다.

```text
app/batch/src/jobs/stock_universe
├── application
│   ├── stock_universe_runner.py
│   └── dto.py
│
├── domain
│   ├── model.py
│   ├── service.py
│   └── repository.py
│
└── infrastructure
    ├── persistence
    │   └── stock_universe_repository.py
    └── client
        └── finance_data_reader_client.py
```

- `finance_data_reader_client.py`는 `FinanceDataReader.StockListing("KRX")` 호출을 담당한다.
- `domain/service.py`는 거래량 기준 상위 200개 선정과 비보통주 미제외 규칙을 담당한다.
- `domain/repository.py`는 `stock` 저장소 인터페이스를 정의한다.
- `stock_universe_repository.py`는 `stock` 테이블 upsert와 `tracked` 갱신을 담당한다.
- `stock_universe_runner.py`는 조회, 선정, 저장, 결과 로그 흐름을 조합한다.
