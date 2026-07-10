# 워커 스캐폴드 계획

상태: 구현 전 계획

## 범위

`worker/` 아래에 Python 워커 패키지의 기본 골격을 생성한다.

이번 단계는 프로젝트 디렉터리, 패키지 구조, 로컬 가상환경, placeholder job, 기본 테스트만 포함한다. 산출물은 `.venv` 안에서 import 가능한 패키지 골격이며, 수동 실행 가능한 배치 엔트리포인트는 아직 만들지 않는다. 실제 금융 데이터 수집, 기술지표 계산, 데이터베이스 연결, 업서트, 스케줄러, 마이그레이션은 포함하지 않는다.

이 문서는 MVP 배치 실행 기반 전체가 아니라 Python 워커 프로젝트 생성만 다룬다.

## 결정 사항

- 언어: Python 3.12 계열
- 패키지 관리 및 실행: 표준 `venv` + `pip`
- 로컬 실행 환경: `worker/.venv`를 프로젝트 로컬 가상환경으로 고정해 의존성을 격리하며, 전역 Python 환경에 프로젝트 의존성이 설치되어 있지 않아도 동작해야 한다
- 패키지 구조: `src/stock_report_worker`
- 패키징 방식: `src` 레이아웃을 사용하는 installable package로 구성한다
- Python 버전 계약: `pyproject.toml`의 `requires-python`은 `>=3.12,<3.13`으로 고정한다
- 설정 관리: 이번 단계에서는 도입하지 않는다
- 데이터베이스 접근: 이번 단계에서는 도입하지 않는다
- 데이터 처리 의존성: `FinanceDataReader`, `pandas`, `numpy`는 실제 수집·계산 단계에서 도입한다
- 테스트: `pytest`
- 프로젝트 위치: `worker/`
- 실행 방식: 이번 단계에서는 공개 엔트리포인트를 만들지 않는다. `python -m stock_report_worker` 또는 console script 중 후속 구현에서 결정한다
- CLI 계약: `cli.py`의 `main()`은 import 검증용 무부작용 stub이다. 이번 단계에서는 `__main__.py`, `[project.scripts]`, 인자 파싱, 종료 코드, `python -m`, console script 실행 계약을 만들지 않는다
- 데이터베이스 계약: 후속 DB 접근 단계에서도 Python 워커는 Spring Flyway가 생성한 테이블만 사용하며 스키마 생성·변경을 수행하지 않는다

## 초기 파일

- `pyproject.toml`
- `requirements.txt`
- `requirements-dev.txt`
- `README.md`
- `.gitignore`
- `src/stock_report_worker/__init__.py`
- `src/stock_report_worker/cli.py`
- `src/stock_report_worker/jobs/__init__.py`
- `src/stock_report_worker/jobs/daily_report.py`
- `tests/test_cli.py`

## 구현 절차

1. `worker/` 디렉터리에 `src` 레이아웃 기반 Python 프로젝트 골격을 생성한다.
2. `pyproject.toml`에 `[project]`, `requires-python = ">=3.12,<3.13"`, `[build-system]`, pytest 설정을 추가한다.
3. `requirements.txt`와 `requirements-dev.txt`를 추가하고 Python 3.12 기반 `worker/.venv` 생성 및 `pip install -r requirements-dev.txt` 흐름을 문서화한다.
4. 설치 후 `worker/.venv` 경로가 존재하는지 확인한다.
5. placeholder 일간 리포트 job과 import 가능한 최소 `main()` 함수를 추가한다.
6. README에 로컬 가상환경 생성, 테스트 실행 방법, 후속 단계에서 지켜야 할 ADR 제약을 문서화한다.
7. `main()` 함수 import와 호출을 검증하는 pytest를 추가한다. 테스트는 `main()` 직접 import, 호출 시 예외 없음, 반환값 `None`까지만 검증한다.
8. 가능하면 가상환경에서 `pytest`를 실행한다.

## 제외 범위

- FinanceDataReader 실제 데이터 수집
- FinanceDataReader 의존성 도입
- pandas/numpy 의존성 도입
- pandas/numpy 기반 계산 로직
- DB URL 설정
- SQLAlchemy/psycopg 의존성 도입
- 데이터베이스 연결 팩토리 구현
- 데이터 적재용 SQL 작성 및 upsert 구현
- 공개 CLI 엔트리포인트
- `src/stock_report_worker/__main__.py`
- `[project.scripts]`
- 인자 파싱
- 종료 코드 계약
- `python -m stock_report_worker` 실행 계약
- console script 실행 계약
- 테이블 메타데이터 정의 및 reflection
- 스케줄러 또는 배치 실행 orchestration
- 도메인 상태 enum 도입
- Flyway 외 마이그레이션 도구 도입
- `.env` 파일 제공
- 운영 배포 설정

## 검증 계획

- `cd worker && python3.12 -m venv .venv` 실행
- `test -d worker/.venv` 실행
- `cd worker && . .venv/bin/activate && python -m pip install --upgrade pip && pip install -r requirements-dev.txt` 실행
- `cd worker && . .venv/bin/activate && pytest` 실행
- `cd worker && . .venv/bin/activate && python -c "import stock_report_worker"` 실행
- `cd worker && . .venv/bin/activate && python -c "from stock_report_worker.cli import main; assert main() is None"` 실행
- 테스트 실행이 불가능하면 원인을 보고하고 임의로 범위를 확장하지 않는다.

## 위험 요소

- 기존 `worker/.venv`가 이전 방식으로 생성된 환경이면 `pip` 실행 파일이 없을 수 있으므로 표준 `venv`로 재생성이 필요할 수 있다.
- 로컬에 Python 3.12가 없으면 가상환경 생성과 테스트 실행이 불가능할 수 있다.
- 의존성 설치가 필요한 경우 네트워크 접근 제약으로 검증이 막힐 수 있다.
- 실행 방식이 아직 확정되지 않았으므로 후속 단계에서 `python -m`과 console script 중 하나를 선택해야 한다.
- 이번 단계는 데이터베이스 연결을 포함하지 않으므로 DB URL, 연결 성공 여부, 스키마 계약 검증은 후속 단계에서 수행해야 한다.

## 후속 구현 계획

- 서버 스키마/Flyway 단계에서 실행 상태 테이블, 리포트 리비전 테이블, publish 제약, 인덱스, 마이그레이션을 정의한다.
- 실제 데이터 수집 단계에서 `FinanceDataReader`를 도입한다.
- 실제 계산 단계에서 `pandas`, `numpy`를 도입한다.
- 워커 DB 접근 단계에서 `SQLAlchemy Core`, `psycopg 3`, `pydantic-settings`, DB URL 설정과 승인된 테이블 접근 방식을 도입한다.
- 배치 실행/재시도 단계에서 advisory lock, 종목별 처리 상태 전이, 재시도 흐름, publish 트랜잭션 사용 방식을 별도 계획으로 다룬다.
