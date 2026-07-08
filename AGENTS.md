# 프로젝트 구조

- `client/`: TypeScript / React.js / TailwindCSS
- `server/`: Kotlin / Spring Boot / JPA
- `worker/`: Python / FinanceDataReader / pandas / SQLAlchemy Core
- `docs/`: 기획서, 코드베이스 조사, 구현 계획, API 문서, 목업 등 프로젝트 문서 산출물

# 핵심 원칙

- 사용자의 명시적인 구현 지시 없이는 코드베이스를 수정하지 않는다.
- 조사, 계획, 검증 단계에서는 파일을 수정하지 않는다.
- 사용자가 승인한 계획 파일이 있는 경우에만 구현을 수행한다.
- 코드베이스 조사 또는 구현 작업을 수행할 때는 `.agents/workflows/`에 정의된 서브 에이전트 활용 워크플로우를 반드시 먼저 참고하고 따른다.
- 구현 중 계획 밖 변경이 필요하면 임의로 수정하지 않고 사용자에게 보고한다.
- 모든 문서 산출물은 한글로 작성한다.
- 커밋 메시지는 type(scope): description 형식을 따르고, description은 한글로 작성한다. body나 footer는 작성하지 않는다.
