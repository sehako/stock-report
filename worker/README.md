# 주식 리포트 워커

Stock Reports Lab의 Python 워커 패키지 골격이다.

## 로컬 환경

이 프로젝트는 Python 3.12 계열과 표준 `venv` 및 `pip`를 사용한다. 의존성은 저장소 루트가 아니라 `worker/.venv`에 격리한다.

```bash
cd worker
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

기존 `worker/.venv`가 이전 방식으로 생성된 환경이면 `pip` 실행 파일이 없을 수 있다. 이 경우 기존 `.venv`를 삭제하고 표준 `venv`로 다시 생성해야 한다.

## 테스트

```bash
cd worker
source .venv/bin/activate
pytest
```

패키지 import만 확인하려면 다음 명령을 사용한다.

```bash
cd worker
source .venv/bin/activate
python -c "import stock_report_worker"
python -c "from stock_report_worker.cli import main; assert main() is None"
```

## 후속 단계 제약

- Python 워커는 Spring Flyway가 생성한 승인된 테이블만 사용한다.
- Python 워커는 스키마 생성이나 변경을 수행하지 않는다.
- 종목 단위 장애 격리를 유지하며, 한 종목의 실패를 전체 일괄 성공 조건으로 삼지 않는다.
- 후속 재시도 정합성은 스케줄러가 아니라 데이터베이스 제약, advisory lock, 명시적인 상태 전이로 보장한다.
- 실제 데이터 수집, 기술지표 계산, 데이터베이스 연결, 업서트, 스케줄러, 공개 CLI 엔트리포인트는 후속 계획에서 별도로 다룬다.
