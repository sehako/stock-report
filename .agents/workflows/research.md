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
