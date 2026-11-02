# API — REST API 명세

> FastAPI가 자동 생성하는 문서(`http://localhost:8000/docs`)가 실제 기준이고,
> 이 문서는 **팀이 합의한 설계**다. API를 바꾸면 이 문서도 같은 PR에서 고친다.

## 공통 규칙

- Base URL: `/api/v1`
- 형식: JSON (`Content-Type: application/json`), 파일 업로드는 `multipart/form-data`
- 인증: `Authorization: Bearer <access_token>` (🔒 표시 엔드포인트)
- 필드명: **snake_case** (프론트 타입도 그대로 사용)
- 시간: ISO 8601 UTC (`2026-11-02T14:00:00Z`), 길이 단위: cm, 무게: kg
- ID: UUID 문자열

### 에러 응답

```json
{ "error": { "code": "ITEM_NOT_FOUND", "message": "옷을 찾을 수 없습니다." } }
```

| HTTP | 의미 |
|------|------|
| 400 | 잘못된 요청 (검증 실패) |
| 401 | 로그인 필요 / 토큰 만료 |
| 403 | 권한 없음 (다른 사람의 데이터) |
| 404 | 없음 |
| 413 | 파일이 너무 큼 (기본 10MB) |
| 422 | 처리 불가 (예: 사진에서 사람을 찾지 못함 `POSE_NOT_DETECTED`) |
| 500 | 서버 오류 |

### 비동기 작업 (Job)

누끼·태깅·체형 분석처럼 오래 걸리는 요청은 `202 Accepted`와 함께 `job_id`를 돌려준다.

```json
{ "job_id": "8f1c…", "status": "pending" }
```

프론트는 `GET /jobs/{job_id}`를 1~2초 간격으로 조회해 `done`이 되면 `result`를 사용한다.

---

## 1. 인증 `auth`

| Method | Path | 설명 |
|--------|------|------|
| POST | `/auth/signup` | 회원가입 |
| POST | `/auth/login` | 로그인 → 토큰 |
| GET 🔒 | `/users/me` | 내 정보 |
| PATCH 🔒 | `/users/me` | 선호 스타일 등 수정 |
| DELETE 🔒 | `/users/me` | 탈퇴 (체형·사진·옷장 데이터 전부 삭제) |

```http
POST /api/v1/auth/login
{ "email": "a@b.com", "password": "****" }

200 OK
{ "access_token": "eyJ…", "token_type": "bearer" }
```

## 2. 체형 `body`

| Method | Path | 설명 |
|--------|------|------|
| POST 🔒 | `/body/analyze` | 전신 사진 + 키 → 체형 분석 (Job) |
| GET 🔒 | `/body/profile` | 내 체형 조회 |
| PUT 🔒 | `/body/profile` | 치수 직접 입력/보정 (사진 없이도 가능) |
| DELETE 🔒 | `/body/profile` | 체형 데이터 삭제 |
| POST 🔒 | `/body/avatar` | 현재 체형으로 아바타 생성 (Job) |
| GET 🔒 | `/body/avatar` | 아바타 정보 (kind, mesh_url 등) |

```http
POST /api/v1/body/analyze      (multipart/form-data)
photo=<file>  height_cm=175

202 Accepted
{ "job_id": "…", "status": "pending" }
```

Job 완료 시 `result`:
```json
{
  "estimated": { "shoulder_cm": 44.1, "arm_cm": 58.3, "leg_cm": 81.0, "torso_cm": 52.4 },
  "confidence": 0.82,
  "original_photo_deleted": true
}
```

```http
PUT /api/v1/body/profile
{
  "height_cm": 175, "weight_kg": 68,
  "chest_cm": 94, "waist_cm": 78, "hip_cm": 95,
  "shoulder_cm": 45, "arm_cm": 58, "leg_cm": 81
}
```

## 3. 옷장 `closet`

| Method | Path | 설명 |
|--------|------|------|
| POST 🔒 | `/closet/items` | 옷 사진 업로드 → 누끼 + 태깅 (Job) |
| GET 🔒 | `/closet/items` | 목록 (`?category=top&color=white&page=1&size=20`) |
| GET 🔒 | `/closet/items/{item_id}` | 상세 |
| PATCH 🔒 | `/closet/items/{item_id}` | 태그·사이즈 수정 |
| DELETE 🔒 | `/closet/items/{item_id}` | 삭제 |
| POST 🔒 | `/closet/items/{item_id}/size-label` | 사이즈표 사진 OCR (Job) |

옷 아이템 응답 예시:
```json
{
  "id": "…",
  "category": "top",
  "subcategory": "knit",
  "colors": ["ivory"],
  "pattern": "solid",
  "material": "wool",
  "cutout_url": "/files/cutouts/….png",
  "size_info": { "label": "M", "chest_cm": 54, "length_cm": 68 },
  "tags_confirmed": false,
  "created_at": "2026-11-02T14:00:00Z"
}
```

`category` 값: `top` | `bottom` | `outer` | `dress` | `shoes` | `bag` | `accessory`
(MVP는 `top`, `bottom`, `outer`만 피팅 지원)

## 4. 코디 `outfits`

| Method | Path | 설명 |
|--------|------|------|
| POST 🔒 | `/outfits` | 코디 저장 |
| GET 🔒 | `/outfits` | 코디 목록 |
| GET 🔒 | `/outfits/{outfit_id}` | 코디 상세 |
| DELETE 🔒 | `/outfits/{outfit_id}` | 삭제 |

```json
{
  "name": "가을 출근룩",
  "items": [
    { "slot": "top",    "closet_item_id": "…" },
    { "slot": "bottom", "product_id": "…" },
    { "slot": "outer",  "closet_item_id": "…" }
  ]
}
```

## 5. 상품 `products`

| Method | Path | 설명 |
|--------|------|------|
| GET | `/products` | 상품 목록 (`?category=&q=&page=`) |
| GET | `/products/{product_id}` | 상품 상세 (사이즈표 포함) |

MVP는 시드 데이터. 제휴몰 연동 시 출처(`partner_id`)와 `product_url`(제휴 링크) 포함.

## 6. 피팅 `fitting`

| Method | Path | 설명 |
|--------|------|------|
| POST 🔒 | `/fitting/preview` | 아바타 + 슬롯별 아이템 → 렌더링 정보 |

```json
// 요청
{ "items": [ { "slot": "top", "product_id": "…" }, { "slot": "bottom", "closet_item_id": "…" } ] }

// 응답 (MVP 2.5D)
{
  "avatar": { "kind": "2_5d", "proportions": { "shoulder_ratio": 0.26, "leg_ratio": 0.47 } },
  "layers": [
    { "slot": "bottom", "texture_url": "…", "z": 1, "anchor": "waist" },
    { "slot": "top",    "texture_url": "…", "z": 2, "anchor": "shoulder" }
  ]
}
```

## 7. 추천 `recommend`

| Method | Path | 설명 |
|--------|------|------|
| GET 🔒 | `/recommend/match-score?product_id=…` | 옷장 매칭 점수 |
| GET 🔒 | `/recommend/gaps` | 빈자리 추천 (P1) |
| GET 🔒 | `/recommend/size?product_id=…` | 사이즈 추천 (P1) |
| GET 🔒 | `/recommend/outfits?product_id=…` | 코디 추천 + 이유 (P1) |

```json
// match-score 응답
{
  "product_id": "…",
  "match_count": 7,
  "message": "이 옷은 당신 옷장의 7벌과 어울립니다",
  "matches": [ { "closet_item_id": "…", "score": 0.91, "reason": "톤온톤 베이지 조합" } ]
}

// size 응답
{ "recommended": "M", "fit": { "chest": "적당", "length": "약간 김" }, "confidence": 0.74 }

// gaps 응답
{ "gaps": [ { "category": "bottom", "attribute": "light_color", "message": "밝은 색 하의가 없어 코디가 막힙니다", "products": ["…"] } ] }
```

## 8. 작업 `jobs`

| Method | Path | 설명 |
|--------|------|------|
| GET 🔒 | `/jobs/{job_id}` | 작업 상태 조회 |

```json
{ "job_id": "…", "type": "closet_item_process", "status": "done", "result": { "item_id": "…" }, "error": null }
```

`status`: `pending` → `running` → `done` | `failed`

---

## 변경 이력

| 날짜 | 변경 | 작성자 |
|------|------|--------|
| 2026-11-02 | 초안 작성 | |
