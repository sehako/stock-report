# 프로젝트 구조

- `client/`: TypeScript / React.js / TailwindCSS
- `server/`: Kotlin / Spring Boot / JPA
- `worker/`: Python / FinanceDataReader / pandas / SQLAlchemy Core
- `docs/`: 기획서, 코드베이스 조사, 구현 계획, API 문서, 목업 등 프로젝트 문서 산출물

# 핵심 원칙

- 사용자의 명시적인 구현 지시 없이는 코드베이스를 수정하지 않는다.
- 조사, 계획, 검증 단계에서는 파일을 수정하지 않는다.
- 사용자가 승인한 계획 파일이 있는 경우에만 구현을 수행한다.
- 구현 중 계획 밖 변경이 필요하면 임의로 수정하지 않고 사용자에게 보고한다.
- 모든 문서 산출물은 한글로 작성한다.
- 커밋 메시지는 type(optional scope): description 형식을 따르고, description은 한글로 작성한다. body나 footer는 작성하지 않는다.

# 조사 워크플로우

사용자가 코드베이스 조사, 영향 범위 파악, 구현 가능성 검토를 요청한 경우 서브에이전트를 사용한다.

조사 단계에서는 파일을 수정하지 않는다.
조사 결과는 관련 파일, 현재 구조, 영향 범위, 구현 후보 지점, 위험 요소 중심으로 요약한다.

## 백엔드 조사

- Kotlin/Spring 구조 조사: `spring-boot-engineer`
- Kotlin 코드 스타일 및 null-safety 조사: `kotlin-specialist`
- API 계약 조사: `api-designer`
- DB, query, schema 영향 조사: `sql-pro`
- 구조적 영향 검토: `architect-reviewer`

## 프론트엔드 조사

- React 구조, component, hook, state 조사: `react-specialist`
- TypeScript type, API type 조사: `typescript-pro`
- API 계약 조사: `api-designer`
- 구조적 영향 검토: `architect-reviewer`

조사 후에는 구현하지 말고 사용자에게 다음 지시를 기다린다.

# 코드 작업 워크플로우

사용자가 명시적으로 코드 수정을 승인한 뒤의 서브에이전트 흐름을 정의한다.

## 1. 구현

작업 단위에 따라 아래 중 필요한 구현 에이전트를 선택한다.

- Kotlin/Spring 기능 구현: `spring-boot-engineer`
- Kotlin 코드 품질, null-safety, idiomatic Kotlin 개선: `kotlin-specialist`
- JVM/Spring 아키텍처 검토 또는 구조 변경: `java-architect`
- React 컴포넌트, hook, route, state 구현: `react-specialist`
- TypeScript type, API type, type guard 구현: `typescript-pro`
- SQL, query, schema, migration, index 작업: `sql-pro`

풀스택 작업은 백엔드 작업 단위와 프론트엔드 작업 단위를 분리해 각각 적절한 에이전트를 사용한다.

## 2. 기본 리뷰

구현 후 항상 `code-reviewer`를 사용한다.

`code-reviewer`는 correctness, regression risk, data contract, missing test를 우선 검토한다.

## 3. 조건부 에이전트

변경 내용에 따라 필요한 경우 아래 에이전트를 추가로 사용한다.

- 인증, 권한, 입력 검증, 암호화, 민감정보 처리 변경: `security-auditor`
- 쿼리, 캐시, 병렬 처리, 대량 데이터, 응답 시간 변경: `performance-engineer`
- 테스트 추가 또는 수정 필요: `test-automator`
- 테스트 실패, 빌드 실패, 런타임 오류 발생: `debugger`

## 4. 실패 처리

`code-reviewer`가 blocking issue를 발견하면 구현 에이전트에게 피드백을 전달해 1회 재작업한다.

blocking issue의 기준은 다음과 같다.

- correctness 문제
- regression 가능성
- security 위험
- data contract 불일치
- missing test
- build/test 실패

최대 재작업 횟수는 1회다. 재작업 후에도 남은 이슈는 임의로 계속 수정하지 않고 사용자에게 보고한다.

## 5. 결과 보고

작업이 끝나면 다음 항목만 간단히 보고한다.

- 사용한 구현 에이전트
- 사용한 리뷰 에이전트
- 변경 요약
- 테스트 결과
- 남은 이슈
