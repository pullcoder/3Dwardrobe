# API — REST API 명세

> FastAPI가 자동 생성하는 문서(`http://localhost:8000/docs`)가 실제 기준이고,
> 이 문서는 **팀이 합의한 설계**다. API를 바꾸면 이 문서도 같은 PR에서 고친다.

## 공통 규칙

- Base URL: `/api/v1`
- 형식: JSON (`Content-Type: application/json`), 파일 업로드는 `multipart/form-data`
- 인증: `Authorization: Bearer <access_token>` (🔒 표시 엔드포인트), B2B 파트너는 `X-API-Key: <key>` (🔑 표시)
- 필드명: **snake_case** (프론트 타입도 그대로 사용)
- 시간: ISO 8601 UTC (`2026-11-02T14:00:00Z`), 길이 단위: cm, 무게: kg
- ID: UUID 문자열

### 에러 응답

```json
{ "error": { "code": "ITEM_NOT_FOUND", "message": "옷을 찾을 수 없습니다." } }
```

| HTTP | 의미 |
|------|------|
| 400 | 잘못된 요청 (예: 지원하지 않는 파일 형식 `UNSUPPORTED_FILE_TYPE`) |
| 401 | 로그인 필요 / 토큰 만료 |
| 403 | 권한 없음 (다른 사람의 데이터) |
| 404 | 없음 |
| 413 | 파일이 너무 큼 (기본 10MB) |
| 422 | 요청 형식 검증 실패 (FastAPI 기본값 — 공통 핸들러로 위 에러 형식에 맞춰 변환) |
| 500 | 서버 오류 |

### 비동기 작업 (Job)

누끼·태깅·체형 분석·에셋 생성처럼 오래 걸리는 요청은 Celery 큐에 작업을 넣고 `202 Accepted`와 함께 `job_id`를 돌려준다.

```json
{ "job_id": "8f1c…", "status": "pending" }
```

프론트는 `GET /jobs/{job_id}`를 1~2초 간격으로 조회해 `done`이 되면 `result`를 사용한다.

**AI 처리 실패는 HTTP 에러가 아니라 Job 실패로 알려준다.** 업로드 요청 자체는 `202`로 성공하고, 워커에서 실패하면:

```json
{ "job_id": "…", "status": "failed", "result": null,
  "error": { "code": "POSE_NOT_DETECTED", "message": "사진에서 전신을 찾지 못했어요. 정면 전신 사진을 올려주세요." } }
```

| Job 에러 코드 | 의미 |
|---------------|------|
| `POSE_NOT_DETECTED` | 사진에서 사람·전신을 찾지 못함 |
| `SEGMENTATION_FAILED` | 누끼 실패 (배경이 복잡하거나 옷이 잘림) |
| `TAGGING_FAILED` | VLM 태깅 실패 |
| `OCR_NO_TEXT` | 사이즈표에서 글자를 읽지 못함 → 직접 입력 안내 |
| `INTERNAL_ERROR` | 그 외 서버 오류 |

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
| POST 🔒 | `/body/avatar` | 현재 체형으로 뷰어용 체형 생성 (Job) — MVP: 2.5D 템플릿, M+6: 3D 메시 |
| GET 🔒 | `/body/avatar` | 뷰어용 체형 정보 (`kind`: `2_5d` \| `mesh3d`, `asset_url` 등) |

```http
POST /api/v1/body/analyze      (multipart/form-data)
photo=<file>  height_cm=175

202 Accepted
{ "job_id": "…", "status": "pending" }
```

Job 완료 시 `result`:
```json
{
  "estimated": { "shoulder_cm": 44.1, "arm_cm": 58.3, "leg_cm": 81.0 },
  "proportions": { "shoulder_ratio": 0.26, "leg_ratio": 0.47 },
  "confidence": 0.82,
  "is_estimate": true,
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
| POST 🔒 | `/closet/items` | 옷 사진(+ 선택: 사이즈표 사진) 업로드 → 누끼 + VLM 태깅 + OCR + 2.5D 에셋 (Job) |
| GET 🔒 | `/closet/items` | 목록 (`?category=top&color=white&page=1&size=20`) |
| GET 🔒 | `/closet/items/{item_id}` | 상세 |
| PATCH 🔒 | `/closet/items/{item_id}` | 태그·사이즈 수정 |
| DELETE 🔒 | `/closet/items/{item_id}` | 삭제 |
| POST 🔒 | `/closet/items/{item_id}/size-label` | 사이즈표·소재표 사진 추가 OCR (Job) |

옷 아이템 응답 예시:
```json
{
  "id": "…",
  "category": "top",
  "subcategory": "knit",
  "color_palette": [ { "hex": "#EFE6D8", "ratio": 0.85, "tone": "warm_light" } ],
  "pattern": "solid",
  "material": "wool",
  "style_tags": ["minimal", "casual"],
  "cutout_url": "/files/cutouts/….png",
  "asset_2_5d": { "texture_url": "/files/assets/….png", "anchors": { "shoulder_l": [0.12, 0.05], "shoulder_r": [0.88, 0.05], "hem": [0.5, 0.98] } },
  "mesh_url": null,
  "size_info": { "label": "M", "chest_cm": 54, "length_cm": 68 },
  "tags_confirmed": false,
  "created_at": "2026-11-02T14:00:00Z"
}
```

`category` 값: `top` | `bottom` | `outer` | `dress` | `shoes` | `accessory`
(MVP는 `top`, `bottom`, `outer`만 피팅 지원. 신발·액세서리·헤어는 M+12)

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

MVP는 팀이 만든 샘플 상품. 이후 제휴몰 **공식 오픈 API/데이터**와 B2B 업로드(아래 9번)로만 채운다 (크롤링 금지). 응답에 출처(`partner_id`), `product_url`(제휴 링크), `asset_2_5d`, `size_chart` 포함.

## 6. 피팅 `fitting`

| Method | Path | 설명 |
|--------|------|------|
| POST 🔒 | `/fitting/preview` | 뷰어용 체형 + 슬롯별 아이템 → 레이어 렌더링 정보 |

```json
// 요청
{ "items": [ { "slot": "top", "product_id": "…" }, { "slot": "bottom", "closet_item_id": "…" } ] }

// 응답 (MVP: 2.5D 스키닝 레이어드 뷰어)
{
  "avatar": { "kind": "2_5d", "template_id": "slim_m_02", "proportions": { "shoulder_ratio": 0.26, "leg_ratio": 0.47 } },
  "layers": [
    { "slot": "bottom", "layer": 1, "asset_2_5d": { "texture_url": "…", "anchors": { … } } },
    { "slot": "top",    "layer": 2, "asset_2_5d": { "texture_url": "…", "anchors": { … } } },
    { "slot": "outer",  "layer": 3, "asset_2_5d": { "texture_url": "…", "anchors": { … } } }
  ]
}
// M+6: avatar.kind = "mesh3d", 각 layer에 mesh_url 추가
```

## 7. 추천 `recommend`

| Method | Path | 설명 |
|--------|------|------|
| GET 🔒 | `/recommend/match-score?product_id=…` | 옷장 매칭 점수 (0~100, 70점 이상 벌 수) |
| GET 🔒 | `/recommend/gaps` | 빈자리 추천 (P1) |
| GET 🔒 | `/recommend/size?product_id=…` | 사이즈 추천 (P1) |
| GET 🔒 | `/recommend/outfits?product_id=…` | 코디 추천 + 이유 (P1) |

```json
// match-score 응답
{
  "product_id": "…",
  "threshold": 70,
  "match_count": 7,
  "best_score": 91,
  "message": "옷장 속 7벌과 70점 이상으로 어울립니다",
  "matches": [
    {
      "closet_item_id": "…",
      "score": 91,
      "breakdown": { "color_harmony": 38, "style": 30, "similarity": 23 },
      "reason": "톤온톤 베이지 조합"
    }
  ]
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

`type` 예: `body_analyze`, `avatar_build`, `closet_item_process`, `size_label_ocr`, `partner_asset_build`

## 9. B2B 파트너 `partner` (P1 파일럿 → P2 정식)

브랜드가 2D 이미지와 사이즈표만 올리면 의류 파이프라인과 **같은 코드**로 2.5D/3D 에셋과 치수 매핑을 자동 생성한다.

| Method | Path | 설명 |
|--------|------|------|
| POST 🔑 | `/partner/products` | 상품 이미지 + 사이즈표 + 메타데이터 업로드 → 에셋 생성 (Job) |
| GET 🔑 | `/partner/products` | 내가 올린 상품 목록 |
| GET 🔑 | `/partner/products/{product_id}` | 상품·에셋 상태 |
| DELETE 🔑 | `/partner/products/{product_id}` | 삭제 |
| GET 🔑 | `/partner/jobs/{job_id}` | 작업 상태 |

```http
POST /api/v1/partner/products     (multipart/form-data)
X-API-Key: …
image=<file>  size_chart=<file>  external_id=SKU-1234  name=오버핏 니트  price=59000  product_url=https://…

202 Accepted
{ "job_id": "…", "product_id": "…", "status": "pending" }
```

위젯(P2)은 이 API로 만든 에셋과 사용자 옷장을 연결해 "내 옷과 입어보기"를 보여준다. 위젯 전용 API는 P2에서 설계.

---

## 변경 이력

| 날짜 | 변경 | 작성자 |
|------|------|--------|
| 2026-11-02 | 초안 작성 | |
| 2026-11-02 | 최종 사업계획서 반영: 2.5D/mesh3d 구분, 매칭 점수 0~100·임계값 70, color_palette·style_tags, B2B partner API | |
