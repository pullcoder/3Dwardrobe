# ARCHITECTURE — 시스템 구조 · 폴더 구조

## 1. 전체 구조

```
┌───────────────────────────┐   HTTPS/JSON   ┌───────────────────────────┐   작업 등록   ┌──────────────┐
│ Frontend (React + TS)     │ ─────────────▶ │ API 서버 (FastAPI)          │ ───────────▶ │ Redis        │
│ - 업로드 UI (Tailwind)     │ ◀───────────── │ - REST /api/v1, JWT        │              │ (브로커/결과)  │
│ - 2.5D 레이어드 뷰어 (MVP)  │                │ - 가벼운 로직만 직접 처리      │              └──────┬───────┘
│ - 3D 뷰어 R3F (M+6)       │                └─────┬───────────────────────┘                     │ 작업 가져감
└───────────────────────────┘                      │                                     ┌───────▼───────────────┐
                                                   │                                     │ AI 워커 (Celery)       │
                                            ┌──────▼──────┐   ┌───────────────────┐       │ - 누끼 / MediaPipe     │
                                            │ PostgreSQL  │◀──│ 파일 저장소          │◀──────│ - VLM 태깅 / OCR       │
                                            │ 사용자·옷장   │   │ 이미지·2.5D·3D 에셋  │       │ - 에셋 생성 / 매칭 점수  │
                                            └─────────────┘   │ (local → S3 호환)  │       └───────────────────────┘
                                                              └───────────────────┘
```

- **AI 추론은 서버의 Celery 워커**에서 한다. API 서버는 요청을 검증하고 작업을 큐에 넣은 뒤 `job_id`를 돌려준다.
- **Celery + Redis를 MVP부터** 사용한다 (사업계획서 5.2 GPU 비용 대응 전략). 워커 수로 트래픽을 분산하고, GPU가 필요한 작업만 GPU 워커로 보낸다.
- 프론트는 `GET /jobs/{job_id}`로 상태를 조회한다.

## 2. AI 파이프라인

### 2.1 체형
```
전신 사진(또는 수치만) → 배경 제거(RMBG/SAM) → MediaPipe 특징점·비율 → 키 기준 cm 환산
   → 원본 사진 즉시 삭제 → 사용자 수동 보정
   → (MVP)  2.5D 피팅 템플릿 선택·변형
   → (M+6) 상업용 인체 메시 파라미터 매핑 → 3D 메시 아바타
```
- 인체 메시 모델은 `BodyMeshModel` 인터페이스 뒤에 숨겨 교체 가능하게 만든다 (MakeHuman 기반 ↔ 유료 SMPL). `DECISIONS.md` D-010

### 2.2 의류 · B2B 자동 에셋 (같은 파이프라인)
```
의류 사진 → 누끼(RMBG/SAM + OpenCV 경계 보정) → VLM 태깅(카테고리·색상 팔레트·소재·패턴·스타일)
         + OCR(사이즈표·소재표) → 치수 매핑
         → (MVP) 2.5D 에셋(스키닝용 텍스처 + 앵커 포인트)
         → (M+6) 3D 메시 에셋
```
- 사용자 옷장 등록과 **B2B 브랜드 상품 등록이 같은 코드를 쓴다.** 입력 출처만 다르다 (`closet_items` vs `products`).

### 2.3 추천 · 매칭 점수
```
옷장 태그 + 신상품 태그 (+ 체형 비율, 선호 스타일)
  → 컬러 하모니 룰 점수 + 스타일 매칭 가중치 + 태그 임베딩 코사인 유사도
  → 0~100점 → 70점 이상 = 어울림 → 매칭 벌 수 · 빈자리 · 사이즈 추천
```
- 점수 가중치와 임계값(`MATCH_SCORE_THRESHOLD=70`)은 설정값으로 두고 사용성 테스트로 조정한다. `DECISIONS.md` D-012

## 3. 폴더 구조

```
3Dwardrobe/
├── README.md
├── AGENTS.md                  # AI 에이전트 공통 지시서
├── CLAUDE.md                  # Claude Code 지시서 (@AGENTS.md)
├── .env.example
├── .gitignore / .gitattributes
├── docker-compose.yml         # PostgreSQL + Redis (로컬 개발용)
├── docs/
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── public/
│   │   └── templates/         # 2.5D 바디 템플릿 등 작은 에셋만
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── routes/            # 페이지 (BodyPage, ClosetPage, FittingPage …)
│       ├── features/
│       │   ├── body/          #   체형 등록·보정 UI
│       │   ├── closet/        #   옷장 목록·업로드·태그 수정
│       │   ├── fitting/       #   피팅 뷰어
│       │   │   ├── layered/   #     2.5D 스키닝 레이어드 뷰어 (MVP)
│       │   │   └── avatar3d/  #     3D 아바타 뷰어 (M+6, R3F)
│       │   └── recommend/     #   매칭 점수·빈자리·사이즈
│       ├── components/        # 공용 UI
│       ├── three/             # 공용 3D 컴포넌트 (M+6)
│       ├── api/               # API 클라이언트
│       ├── stores/            # 전역 상태 (Zustand)
│       ├── types/             # 공용 타입
│       └── lib/               # 유틸
│
└── backend/
    ├── requirements.txt
    ├── pyproject.toml         # ruff / pytest 설정
    ├── alembic/
    ├── app/
    │   ├── main.py            # FastAPI 앱
    │   ├── core/              # 설정, 보안(JWT), 로깅
    │   ├── db/                # 세션, Base
    │   ├── models/            # SQLAlchemy 모델
    │   ├── schemas/           # Pydantic 스키마
    │   ├── api/v1/            # 라우터 (auth, users, body, closet, outfits, products, fitting, recommend, jobs, partner)
    │   ├── services/          # 비즈니스 로직
    │   ├── workers/           # Celery 앱 + 작업 정의 (tasks)
    │   ├── ai/                # AI 파이프라인 모듈 (워커에서 호출)
    │   │   ├── segmentation.py   # RMBG / SAM 누끼
    │   │   ├── pose.py           # MediaPipe 특징점, cm 환산
    │   │   ├── body_template.py  # 2.5D 피팅 템플릿 (MVP)
    │   │   ├── body_mesh.py      # 3D 인체 메시 (M+6, 교체 가능 인터페이스)
    │   │   ├── tagging.py        # VLM 태깅
    │   │   ├── ocr.py            # 사이즈표·소재표 OCR
    │   │   ├── garment_asset.py  # 2.5D/3D 의류 에셋 + 치수 매핑 (B2B 공용)
    │   │   └── matching.py       # 컬러 하모니 + 스타일 가중치 + 코사인 → 0~100
    │   └── storage/           # 파일 저장 추상화 (local / s3)
    ├── models/weights/        # 모델 가중치 (git 제외)
    └── tests/
```

**레이어 규칙 (백엔드)**: `api` → `services` → (`models`, `storage`, `workers`). AI 모듈(`ai/`)은 **워커에서만** 호출한다. 라우터에서 DB·AI를 직접 부르지 않는다.

## 4. 데이터 모델 (초안)

| 테이블 | 주요 컬럼 | 설명 |
|--------|----------|------|
| `users` | id, email, password_hash, preferred_styles[], created_at | 회원 |
| `body_profiles` | id, user_id, height_cm, weight_kg, chest_cm, waist_cm, hip_cm, shoulder_cm, arm_cm, leg_cm, source(photo/manual), landmarks(jsonb), template_id, updated_at | 체형 (사용자당 1개) |
| `avatars` | id, body_profile_id, kind(`2_5d`/`mesh3d`), mesh_model(예: `makehuman`), params(jsonb), asset_url | 뷰어용 체형 |
| `closet_items` | id, user_id, category, subcategory, color_palette(jsonb), material, pattern, style_tags[], image_url, cutout_url, asset_2_5d(jsonb), mesh_url, size_info(jsonb), tags_confirmed, created_at | 내 옷 |
| `partners` | id, name, api_key_hash, plan, created_at | 제휴몰·B2B 브랜드 |
| `products` | id, partner_id, external_id, name, brand, price, category, subcategory, color_palette(jsonb), material, pattern, style_tags[], image_url, cutout_url, asset_2_5d(jsonb), mesh_url, size_chart(jsonb), product_url | 쇼핑몰 상품 (공식 API/업로드) |
| `outfits` | id, user_id, name, created_at | 저장한 코디 |
| `outfit_items` | outfit_id, slot(top/bottom/outer/…), layer, closet_item_id 또는 product_id | 코디 구성 |
| `match_scores` | closet_item_id, product_id, score(0~100), breakdown(jsonb), computed_at | 매칭 점수 캐시 |
| `jobs` | id, user_id 또는 partner_id, type, status(pending/running/done/failed), celery_task_id, result(jsonb), error, created_at | 비동기 AI 작업 |

- ID는 UUID, 시간은 UTC `timestamptz`.
- **원본 체형 사진은 저장하지 않는다.** 분석 직후 삭제 (`DELETE_ORIGINAL_BODY_PHOTO=true`).
- `color_palette` 예: `[{"hex": "#E8DCC8", "ratio": 0.7, "tone": "warm_light"}]`

## 5. 배포 (예정)

- MVP 데모: 프론트 정적 호스팅 + API 서버(CPU) + Celery 워커(경량 모델, CPU 또는 소형 GPU) + 관리형 PostgreSQL/Redis
- 고도화: GPU 워커 분리 (3D 메시·드레이핑). 결정 시 `DECISIONS.md`에 기록.
- 예산: 서버·인프라 30% (총 3,000만 원 가정 시 약 900만 원) 안에서 운영.
