# 디자인 지침

## 출처와 적용 범위

이 문서는 Coinbase `DESIGN.md` 사례의 신뢰 중심 금융 UI 분위기를 참고하되, `stock-report`의 국내 주식 데이터 조회 MVP에 맞게 Tailwind CSS 기반 레이아웃 시스템으로 재정리한 문서다.

원문 사례는 `awesome-design-md`의 Coinbase 분석 문서이며, Coinbase와 공식 제휴된 문서는 아니다. 이 프로젝트에서는 브랜드를 복제하지 않고, 흰 배경, 절제된 파란색, 숫자 데이터 가독성, 차분한 금융 대시보드 구조만 차용한다.

- 참고 출처: https://getdesign.md/coinbase
- 원문 저장소: https://github.com/VoltAgent/awesome-design-md

## 제품 성격

`stock-report`는 실시간 트레이딩 서비스가 아니라, 장 마감 후 수집된 국내 주식과 시장 지수 데이터를 조회하는 MVP 서비스다.

화면은 거래를 유도하는 앱이 아니라, 사용자가 코스피, 코스닥, 종목 목록, 종목 상세 데이터를 차분하고 정확하게 확인하는 금융 데이터 대시보드여야 한다.

## 기본 방향

- 흰 배경과 옅은 회색 구역을 기본으로 사용한다.
- 파란색은 주요 액션, 활성 상태, 핵심 링크에만 제한적으로 사용한다.
- 상승과 하락 색상은 등락률, 차트, 변화량 같은 데이터 의미 표현에만 사용한다.
- 테이블, 필터, 차트, 요약 패널의 일관성을 우선한다.
- 화면 전체를 카드로 감싸지 않고, 페이지는 넓은 캔버스 위에 섹션과 패널을 배치한다.
- 마케팅 랜딩 페이지처럼 과장된 hero, 장식 배경, 큰 그림자는 사용하지 않는다.

## Tailwind 사용 원칙

새 UI는 Tailwind CSS 유틸리티 조합으로 작성한다. 임의의 픽셀 값을 먼저 만들기보다 Tailwind 기본 스케일과 의미 있는 컴포넌트 패턴을 우선한다.

- 레이아웃은 `mx-auto`, `max-w-*`, `grid`, `flex`, `gap-*`, `space-y-*` 조합으로 구성한다.
- 여백은 `px-*`, `py-*`, `p-*`, `gap-*`를 사용하고 임의값 사용을 피한다.
- 색상은 `slate`, `blue`, `emerald`, `rose` 계열을 중심으로 사용한다.
- 경계는 `border`, `border-slate-200`, `divide-y`, `divide-slate-100`를 우선한다.
- 그림자는 기본적으로 쓰지 않고, 필요한 경우 `shadow-sm`까지만 사용한다.
- 둥근 형태는 `rounded-lg`, `rounded-xl`, `rounded-full` 중에서 선택한다.
- 숫자 데이터에는 `tabular-nums`를 적용한다.
- 상태 표현은 색상 하나에만 의존하지 않고 텍스트, 아이콘, 라벨을 함께 고려한다.

## 색상 역할

### 기본 화면

| 역할 | Tailwind 예시 | 용도 |
| --- | --- | --- |
| 기본 배경 | `bg-white` | 페이지 기본 바탕 |
| 보조 배경 | `bg-slate-50` | 섹션, 필터 영역, 빈 상태 |
| 패널 배경 | `bg-white` | 요약 카드, 차트 패널, 테이블 |
| 기본 텍스트 | `text-slate-950` | 제목, 핵심 값 |
| 보조 텍스트 | `text-slate-600` | 설명, 부가 정보 |
| 약한 텍스트 | `text-slate-400` | 캡션, placeholder, 비활성 |
| 기본 경계 | `border-slate-200` | 패널, 입력창, 구분선 |
| 약한 경계 | `divide-slate-100` | 테이블 행, 목록 행 |

### 액션과 데이터 의미

| 역할 | Tailwind 예시 | 용도 |
| --- | --- | --- |
| 주요 액션 | `bg-blue-600 text-white` | primary button |
| 주요 액션 hover | `hover:bg-blue-700` | primary button hover |
| 활성 텍스트 | `text-blue-600` | 활성 탭, 링크, 선택 상태 |
| 활성 배경 | `bg-blue-50 text-blue-700` | 선택된 필터, 선택된 기간 |
| 상승 | `text-emerald-600` | 양수 등락률, 상승 변화 |
| 하락 | `text-rose-600` | 음수 등락률, 하락 변화 |
| 보합 | `text-slate-500` | 변화 없음, 값 없음 |

상승/하락 색상은 버튼 배경으로 사용하지 않는다. 강한 빨강/초록 배경은 금융 화면을 과하게 긴장감 있게 만들 수 있으므로 피한다.

## 페이지 레이아웃 시스템

### Page Shell

모든 주요 페이지는 같은 바깥 구조를 사용한다.

```tsx
<main className="min-h-screen bg-white">
  <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
    {/* page content */}
  </div>
</main>
```

페이지 안의 주요 흐름은 `space-y-6` 또는 `space-y-8`로 정리한다. 화면 전체를 하나의 큰 카드로 감싸지 않는다.

### Header

페이지 헤더는 현재 화면의 목적과 핵심 상태를 짧게 보여준다.

```tsx
<header className="flex flex-col gap-4 border-b border-slate-200 pb-6 sm:flex-row sm:items-end sm:justify-between">
  <div className="space-y-1">
    <h1 className="text-2xl font-semibold tracking-normal text-slate-950 sm:text-3xl">
      시장 개요
    </h1>
    <p className="text-sm text-slate-600">
      장 마감 후 수집된 코스피와 코스닥 지표
    </p>
  </div>
</header>
```

대시보드성 화면에서는 과도하게 큰 hero 제목을 사용하지 않는다.

### Section

섹션은 독립적인 정보 묶음이다. 필요할 때만 제목을 둔다.

```tsx
<section className="space-y-4">
  <div className="flex items-center justify-between gap-3">
    <h2 className="text-lg font-semibold text-slate-950">주요 지수</h2>
  </div>
  {/* section body */}
</section>
```

섹션 자체에 카드 스타일을 주지 않는다. 카드, 테이블, 차트 패널은 섹션 내부의 실제 정보 단위에만 적용한다.

### Responsive Grid

요약 정보는 반응형 grid를 기본으로 한다.

```tsx
<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
  {/* summary panels */}
</div>
```

차트와 보조 정보가 함께 있는 화면은 데스크톱에서 비대칭 grid를 사용할 수 있다.

```tsx
<div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(18rem,1fr)]">
  {/* chart */}
  {/* side panel */}
</div>
```

## 공통 컴포넌트 패턴

### Panel

반복되는 요약 카드, 차트, 상세 정보 패널에 사용한다.

```tsx
<div className="rounded-xl border border-slate-200 bg-white p-4">
  {/* panel content */}
</div>
```

패널 내부는 `space-y-3` 또는 `space-y-4`를 기본으로 한다. 패널 안에 또 다른 카드형 패널을 중첩하지 않는다.

### Primary Button

```tsx
<button className="inline-flex items-center justify-center gap-2 rounded-full bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:bg-blue-300">
  조회
</button>
```

아이콘이 있는 액션은 `gap-2`를 사용한다. 텍스트만으로 의미가 약한 액션에는 `lucide-react` 아이콘을 함께 사용한다.

### Secondary Button

```tsx
<button className="inline-flex items-center justify-center gap-2 rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-slate-200">
  초기화
</button>
```

### Segmented Control

기간, 시장 구분, 정렬 옵션처럼 선택지가 적은 제어에 사용한다.

```tsx
<div className="inline-flex rounded-full bg-slate-100 p-1">
  <button className="rounded-full px-3 py-1.5 text-sm font-medium text-blue-700 bg-white shadow-sm">
    1M
  </button>
  <button className="rounded-full px-3 py-1.5 text-sm font-medium text-slate-600">
    3M
  </button>
</div>
```

선택 상태는 `bg-white text-blue-700 shadow-sm` 또는 `bg-blue-50 text-blue-700`로 표현한다.

### Search Input

```tsx
<div className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 focus-within:border-blue-600">
  {/* Search icon */}
  <input className="min-w-0 flex-1 bg-transparent text-sm text-slate-950 outline-none placeholder:text-slate-400" />
</div>
```

검색창은 종목 목록 상단에서 가장 먼저 보이는 필터로 둔다.

### Badge

```tsx
<span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
  KOSPI
</span>
```

시장 구분, 데이터 상태, 기간 같은 짧은 상태값에 사용한다.

## 데이터 화면 패턴

### 지수 요약 카드

코스피와 코스닥은 같은 패널 구조로 보여준다.

```tsx
<article className="rounded-xl border border-slate-200 bg-white p-4">
  <div className="flex items-center justify-between gap-3">
    <h3 className="text-sm font-semibold text-slate-950">KOSPI</h3>
    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
      AVAILABLE
    </span>
  </div>
  <div className="mt-4 space-y-1">
    <p className="tabular-nums text-2xl font-semibold text-slate-950">2,812.05</p>
    <p className="tabular-nums text-sm font-medium text-emerald-600">+0.84%</p>
  </div>
</article>
```

`EMPTY`, `PARTIAL`, `AVAILABLE` 상태는 배지로 표현하되, 빈 데이터가 장애처럼 보이지 않게 중립 색상을 기본으로 한다.

### 종목 목록

데스크톱에서는 테이블을 기본으로 한다.

```tsx
<div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
  <table className="min-w-full divide-y divide-slate-100">
    <thead className="bg-slate-50">
      <tr className="text-left text-xs font-semibold uppercase text-slate-500">
        {/* columns */}
      </tr>
    </thead>
    <tbody className="divide-y divide-slate-100 text-sm">
      {/* rows */}
    </tbody>
  </table>
</div>
```

가격, 거래량, 등락률은 `tabular-nums text-right`를 기본으로 한다. 종목명은 `font-medium text-slate-950`, 종목코드는 `text-slate-500`로 구분한다.

모바일에서는 테이블 가로 스크롤 또는 카드형 행을 사용한다. 핵심 정보인 종목명, 종목코드, 종가, 등락률은 접히지 않아야 한다.

### 차트 영역

```tsx
<section className="rounded-xl border border-slate-200 bg-white p-4">
  <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
    <h2 className="text-lg font-semibold text-slate-950">가격 추이</h2>
    {/* period segmented control */}
  </div>
  <div className="min-h-72">
    {/* chart */}
  </div>
</section>
```

차트는 데이터 해석을 위한 요소다. 장식용 배경, 불필요한 3D 효과, 강한 그림자는 사용하지 않는다.

### 빈 상태

```tsx
<div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
  <p className="text-sm font-medium text-slate-950">조회 가능한 데이터가 없습니다</p>
  <p className="mt-1 text-sm text-slate-600">필터를 변경하거나 다른 기간을 선택하세요.</p>
</div>
```

빈 상태는 오류가 아니라 데이터 조건의 결과로 표현한다.

### 로딩 상태

```tsx
<div className="space-y-3">
  <div className="h-5 w-1/3 animate-pulse rounded bg-slate-100" />
  <div className="h-48 animate-pulse rounded-xl bg-slate-100" />
</div>
```

로딩 중에도 최종 레이아웃의 크기를 유지해 화면 흔들림을 줄인다.

## 화면별 조립 기준

### 시장 개요 화면

- Page Shell 안에 Header, 지수 요약 grid, 지수 차트 섹션을 순서대로 배치한다.
- 코스피와 코스닥은 같은 크기의 요약 패널로 비교 가능하게 둔다.
- 차트 기간 선택은 차트 제목 오른쪽에 배치한다.

### 종목 목록 화면

- Header 아래에 검색과 필터 toolbar를 둔다.
- toolbar는 `flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between`를 기본으로 한다.
- 테이블은 페이지의 핵심 영역으로 두고, 불필요한 설명 문구를 줄인다.
- 페이지네이션은 테이블 하단 오른쪽 또는 모바일 하단 전체 폭에 배치한다.

### 종목 상세 화면

- 상단에는 종목명, 종목코드, 시장 구분, 최신 거래일을 배치한다.
- 그 아래 최신 종가, 등락률, 거래량을 요약 grid로 배치한다.
- 가격 차트는 가장 넓은 영역을 차지한다.
- 보조 정보는 오른쪽 사이드 패널 또는 차트 아래에 배치한다.

## 반응형 기준

- 모바일에서는 `grid-cols-1`을 기본으로 한다.
- 태블릿 이상에서 `sm:grid-cols-2`를 사용해 요약 카드 비교를 지원한다.
- 데스크톱에서는 `lg:grid-cols-*`와 custom grid track을 사용해 차트 영역을 넓게 둔다.
- 긴 테이블은 `overflow-x-auto`로 처리하되, 핵심 열이 너무 작아지면 카드형 목록으로 전환한다.
- 터치 대상은 `min-h-11`, `py-2`, `px-3` 이상의 조합을 사용한다.

## 해야 할 것

- Tailwind 기본 스케일과 색상 체계를 우선 사용한다.
- `tabular-nums`로 숫자 열의 흔들림을 줄인다.
- `border`와 `divide-*`로 데이터 영역을 정리한다.
- `bg-blue-600`은 주요 액션에만 제한적으로 사용한다.
- 상승은 `text-emerald-600`, 하락은 `text-rose-600`로 표현한다.
- 빈 상태, 로딩 상태, 오류 상태도 실제 화면 레이아웃 안에서 설계한다.

## 하지 말아야 할 것

- 임의의 px 값으로 여백과 크기를 계속 추가하지 않는다.
- 페이지 전체를 카드 안에 넣지 않는다.
- 카드 안에 카드를 중첩하지 않는다.
- 상승/하락 색상을 버튼 배경으로 사용하지 않는다.
- 큰 그림자, 그라데이션 배경, 장식용 blob을 사용하지 않는다.
- 대시보드 내부에서 hero급 타이포그래피를 남용하지 않는다.

## 프론트엔드 구현 메모

- `docs/architecture/frontend.md`의 기능 중심 구조를 따른다.
- 공통 컴포넌트는 `shared/component`에 두고, 도메인 전용 UI는 각 `features/{domain}/ui`에 둔다.
- Tailwind 클래스 조합이 반복되면 공통 컴포넌트로 추출한다.
- 색상, 간격, 상태 표현을 화면별로 임의 변경하지 않는다.
- 차트, 테이블, 필터는 재사용 가능한 데이터 UI 패턴으로 유지한다.
