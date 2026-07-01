# 프론트엔드 스캐폴드 계획

상태: 사용자 승인 및 구현 완료

## 범위

`client/` 아래에 신규 프론트엔드 프로젝트를 생성한다.

## 결정 사항

- 런타임: Node.js 기반 프론트엔드 개발 환경
- 언어: TypeScript
- 프레임워크: React
- 빌드 도구: Vite
- 스타일링: TailwindCSS
- 프로젝트 위치: `client/`
- 초기 화면: 기능이 없는 빈 메인 화면
- 백엔드 연동: 없음

## 초기 파일

- `package.json`
- Vite 설정 파일
- TypeScript 설정 파일
- TailwindCSS 설정 파일
- PostCSS 설정 파일
- React 진입점
- 빈 메인 컴포넌트
- 전역 스타일 파일
- 기본 HTML 템플릿

## 구현 절차

1. `client/` 디렉터리에 Vite React TypeScript 프로젝트를 생성한다.
2. TailwindCSS 의존성과 설정 파일을 추가한다.
3. Vite 예제 UI를 제거하고 빈 메인 화면만 남긴다.
4. TailwindCSS가 전역 스타일에 적용되도록 구성한다.
5. 기본 실행 스크립트를 확인한다.
6. 가능하면 `npm run build`로 빌드 검증을 수행한다.

## 제외 범위

- 라우팅 구성
- API 클라이언트 구성
- 백엔드 API 연동
- 인증 및 권한 처리
- 상태 관리 라이브러리 도입
- 도메인 모델 또는 화면 구현
- 테스트 코드 작성
- 배포 설정

## 검증 계획

- `npm run build` 실행
- 빌드 실패 시 원인을 보고하고 임의로 범위를 확장하지 않는다.

## 위험 요소

- Node.js 또는 npm 버전이 Vite/TailwindCSS 최신 요구사항과 맞지 않을 수 있다.
- 의존성 설치에는 네트워크 접근이 필요할 수 있다.
- TailwindCSS 최신 버전의 설정 방식이 기존 문서나 예제와 다를 수 있다.
