# CONVENTIONS — 코딩 · 네이밍 · 주석 규칙

> 사람과 AI(Claude Code, Codex) 모두 이 규칙을 따른다. 자동 도구(ruff, ESLint, Prettier)가 잡아주는 건 도구에 맡긴다.

## 1. 공통

- **언어**: 코드 식별자는 영어, 주석·문서·커밋 메시지 본문은 한국어.
- **인코딩/줄바꿈**: UTF-8, LF. 저장소의 `.gitattributes`가 OS와 상관없이 LF로 맞춰준다.
- **들여쓰기**: Python 4칸, TS/TSX·JSON·CSS 2칸
- **한 함수는 한 가지 일**. 50줄이 넘어가면 나눌 수 있는지 본다.
- **매직 넘버 금지**: 의미 있는 상수로 뺀다. (`MAX_UPLOAD_MB = 10`)
- **비밀값은 `.env`**에서만 읽는다. 코드에 하드코딩 금지.
- 쓰지 않는 코드·`console.log`·`print` 디버깅은 커밋 전에 지운다.

## 2. 네이밍

| 대상 | 규칙 | 예시 |
|------|------|------|
| Python 변수·함수 | snake_case | `estimate_shoulder_cm()` |
| Python 클래스 | PascalCase | `BodyProfile` |
| Python 상수 | UPPER_SNAKE | `DEFAULT_HEIGHT_CM` |
| Python 파일 | snake_case | `body_service.py` |
| TS 변수·함수 | camelCase | `fetchClosetItems()` |
| React 컴포넌트·파일 | PascalCase | `FittingViewer.tsx` |
| React 훅 | `use` + PascalCase | `useClosetItems.ts` |
| TS 타입·인터페이스 | PascalCase (I 접두사 X) | `ClosetItem` |
| TS 일반 파일 | camelCase | `apiClient.ts` |
| CSS | Tailwind 유틸리티 우선, 커스텀 클래스는 kebab-case | `fitting-canvas` |
| DB 테이블 | snake_case 복수형 | `closet_items` |
| DB 컬럼 | snake_case, 단위 접미사 | `height_cm`, `weight_kg` |
| API 경로 | kebab-case, 복수형 명사 | `/closet/items`, `/recommend/match-score` |
| JSON 필드 | snake_case | `cutout_url` |
| TS의 API 응답 타입 필드 | snake_case 그대로 (변환하지 않음) | `item.cutout_url` |
| 환경변수 | UPPER_SNAKE | `DATABASE_URL` |
| 불리언 | is/has/can 접두사 | `is_confirmed`, `hasAvatar` |

**도메인 용어 통일** (코드·DB·UI 모두 같은 단어 사용)

| 한국어 | 코드 |
|--------|------|
| 체형 | `body_profile` |
| 아바타 | `avatar` |
| 옷장 / 내 옷 | `closet` / `closet_item` |
| 쇼핑몰 상품 | `product` |
| 코디 | `outfit` |
| 누끼 | `cutout` |
| 크로스 피팅 | `fitting` |
| 매칭 점수 | `match_score` |
| 빈자리 추천 | `gap` |
| 슬롯 (상의·하의·겉옷) | `slot`: `top` / `bottom` / `outer` |

## 3. 프론트엔드 (React + TS)

- 함수형 컴포넌트 + 훅만 사용. `any` 금지(불가피하면 `unknown` 후 좁히기).
- `strict: true` TypeScript.
- 컴포넌트 파일 하나에 컴포넌트 하나(작은 내부 컴포넌트는 예외).
- **API 호출은 `src/api/`에서만**. 컴포넌트에서 `fetch` 직접 호출 금지.
- 서버 데이터는 TanStack Query, 클라이언트 전역 상태는 Zustand. (`DECISIONS.md` D-007)
- 3D 코드: R3F 컴포넌트는 `src/three/` 또는 `features/fitting/`. `useFrame` 안에서 상태를 setState 하지 않는다(성능).
- 3D 에셋은 `.glb` 사용, 큰 파일은 저장소가 아닌 스토리지에 둔다.
- import 순서: 외부 라이브러리 → 절대경로(`@/…`) → 상대경로.

```tsx
// 좋은 예
export function ClosetItemCard({ item, onSelect }: ClosetItemCardProps) {
  return (
    <button className="rounded-xl border p-2" onClick={() => onSelect(item.id)}>
      <img src={item.cutout_url} alt={item.subcategory} />
    </button>
  );
}
```

## 4. 백엔드 (FastAPI)

- 타입 힌트 필수. Pydantic v2 스키마로 요청/응답 정의.
- **라우터는 얇게**: 검증 → 서비스 호출 → 응답. 로직은 `services/`, AI는 `ai/`.
- 요청 스키마 `XxxCreate`/`XxxUpdate`, 응답 스키마 `XxxRead`.
- DB 변경은 반드시 Alembic 마이그레이션.
- 에러는 `HTTPException` 대신 공통 예외 클래스(`AppError(code, message, status)`)로 던져 `API.md` 형식에 맞춘다.
- AI 모델은 **앱 시작 시 1회 로드**(요청마다 로드 금지).
- 사진·체형 수치를 로그에 남기지 않는다. 로그에는 ID만.

```python
@router.get("/closet/items/{item_id}", response_model=ClosetItemRead)
def get_closet_item(item_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return closet_service.get_item(db, user_id=user.id, item_id=item_id)
```

## 5. 주석 규칙

- **"무엇"이 아니라 "왜"**를 쓴다. 코드만 봐도 아는 내용은 쓰지 않는다.
- 공개 함수에는 짧은 docstring/JSDoc (한 줄 요약 + 단위·예외).
- 추정치·임시 로직에는 근거를 남긴다.

```python
def estimate_shoulder_cm(landmarks: PoseLandmarks, height_cm: float) -> float:
    """어깨너비(cm)를 추정한다. 키를 기준 길이로 픽셀 → cm 환산."""
    # 정면 사진에서 11·12번 랜드마크 사이 거리는 실제 어깨너비보다 약 8% 좁게 잡혀 보정한다. (실험 노트 2026-11)
    ...
```

- 태그: `# TODO(이름): 할 일`, `# FIXME:`, `# NOTE:` — TODO에는 이름을 붙인다.

## 6. 테스트

- 백엔드: `pytest`, 파일명 `test_*.py`. 서비스·매칭 로직은 단위 테스트 필수.
- 프론트: Vitest + Testing Library (핵심 훅·유틸 우선).
- AI 모델 결과는 고정 샘플 이미지로 "범위 안에 드는지" 검사한다(정확한 값 비교 X).

## 7. 도구

| 범위 | 도구 | 명령 |
|------|------|------|
| Python 린트·포맷 | ruff | `ruff check . && ruff format .` |
| Python 테스트 | pytest | `pytest` |
| TS 린트 | ESLint | `npm run lint` |
| TS 포맷 | Prettier | `npm run format` |
| 타입 체크 | tsc | `npm run typecheck` |
