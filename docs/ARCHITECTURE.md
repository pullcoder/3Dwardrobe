# ARCHITECTURE — 시스템 구조 · 폴더 구조

## 1. 전체 구조

```
┌────────────────────────────┐        HTTPS / JSON         ┌──────────────────────────────┐
│  Frontend (React + TS)     │  ───────────────────────▶  │  Backend (FastAPI)           │
│  - 업로드 UI (Tailwind)     │  ◀───────────────────────  │  - REST API  /api/v1         │
│  - 3D 뷰어 (Three.js/R3F)   │                            │  - 인증(JWT)                  │
└────────────────────────────┘                            │  - AI 파이프라인 (services/ai) │
                                                          └──────┬───────────────┬───────┘
                                                                 │               │
                                                       ┌─────────▼─────┐  ┌──────▼─────────────┐
                                                       │ PostgreSQL    │  │ 파일 저장소          │
                                                       │ 사용자·옷장·코디 │  │ 이미지·누끼·3D 파일   │
                                                       └───────────────┘  │ (local → S3 호환)   │
                                                                          └────────────────────┘
```

- **AI 추론은 서버에서** 한다 (브라우저에서 무거운 모델을 돌리지 않음).
- 오래 걸리는 작업(누끼·태깅·아바타 생성)은 **비동기 작업(Job)** 으로 처리하고, 프론트는 상태를 조회한다.
  - MVP: FastAPI `BackgroundTasks` + `jobs` 테이블
  - 확장: Celery/RQ + Redis 워커로 분리 (필요해지면 `DECISIONS.md`에 기록 후 도입)

## 2. AI 파이프라인

### 체형
```
전신 사진 → 배경 제거(RMBG/SAM) → MediaPipe Pose 특징점 → 키 기준 cm 환산
        → 사용자 수동 보정 → (MVP) 2.5D 실루엣 / (M+6) SMPL 파라미터 → 아바타
        → 원본 사진 삭제
```

### 의류
```
옷 사진 → 누끼(RMBG/SAM + OpenCV 경계 보정) → VLM 태깅(종류·색·무늬·소재)
       + OCR 치수(사이즈표 사진) → (MVP) 2.5D 텍스처 / (확장) 3D 메시
```

### 추천
```
옷장 태그 + 체형 비율 + 선호 스타일 → 조합 점수 계산 → 매칭 점수 · 빈자리 · 사이즈 추천
```
- MVP 매칭 점수는 **규칙 기반**(색 조화, 카테고리 조합, 스타일 일치)으로 시작하고, 데이터가 쌓이면 학습 모델로 교체한다.

## 3. 폴더 구조

```
3Dwardrobe/
├── README.md
├── AGENTS.md                  # AI 에이전트 공통 지시서
├── CLAUDE.md                  # Claude Code 지시서 (@AGENTS.md)
├── .env.example
├── .gitignore
├── docker-compose.yml         # PostgreSQL (로컬 개발용)
├── docs/
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── public/
│   │   └── models/            # 샘플 3D 에셋(.glb) — 용량 작은 것만
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── routes/            # 페이지 단위 (BodyPage, ClosetPage, FittingPage …)
│       ├── features/          # 기능별 묶음
│       │   ├── body/          #   체형 등록·보정 UI, hooks
│       │   ├── closet/        #   옷장 목록·업로드·태그 수정
│       │   ├── fitting/       #   피팅 뷰어 (R3F Canvas, 슬롯)
│       │   └── recommend/     #   매칭 점수·빈자리·사이즈
│       ├── components/        # 여러 기능에서 쓰는 공용 UI (Button, Modal …)
│       ├── three/             # 공용 3D 컴포넌트 (Avatar, Garment, CameraRig)
│       ├── api/               # API 클라이언트 (fetch 래퍼, 엔드포인트별 함수)
│       ├── stores/            # 전역 상태 (Zustand)
│       ├── types/             # 공용 타입 (API 응답 타입 등)
│       └── lib/               # 유틸 함수
│
└── backend/
    ├── requirements.txt
    ├── pyproject.toml         # ruff / pytest 설정
    ├── alembic/               # DB 마이그레이션
    ├── app/
    │   ├── main.py            # FastAPI 앱 생성, 라우터 등록
    │   ├── core/              # 설정(config), 보안(JWT), 로깅
    │   ├── db/                # 세션, Base
    │   ├── models/            # SQLAlchemy 모델 (테이블)
    │   ├── schemas/           # Pydantic 요청/응답 스키마
    │   ├── api/v1/            # 라우터 (auth, users, body, closet, outfits, products, fitting, recommend, jobs)
    │   ├── services/          # 비즈니스 로직 (라우터는 얇게, 로직은 여기)
    │   ├── ai/                # AI 파이프라인 모듈
    │   │   ├── segmentation.py   # RMBG / SAM 누끼
    │   │   ├── pose.py           # MediaPipe 특징점, cm 환산
    │   │   ├── avatar.py         # 2.5D / SMPL 아바타
    │   │   ├── tagging.py        # VLM 의류 태깅
    │   │   ├── ocr.py            # 사이즈표 OCR
    │   │   └── matching.py       # 매칭 점수 · 빈자리 · 사이즈
    │   └── storage/           # 파일 저장 추상화 (local / s3)
    ├── models/weights/        # 모델 가중치 (git 제외)
    └── tests/
```

**레이어 규칙 (백엔드)**: `api` → `services` → (`models`, `ai`, `storage`). 라우터에서 DB나 AI를 직접 호출하지 않는다.

## 4. 데이터 모델 (초안)

| 테이블 | 주요 컬럼 | 설명 |
|--------|----------|------|
| `users` | id, email, password_hash, preferred_styles[], created_at | 회원 |
| `body_profiles` | id, user_id, height_cm, weight_kg, chest_cm, waist_cm, hip_cm, shoulder_cm, arm_cm, leg_cm, source(photo/manual), landmarks(jsonb), updated_at | 체형 (사용자당 1개) |
| `avatars` | id, body_profile_id, kind(2_5d/smpl), smpl_params(jsonb), mesh_url | 아바타 |
| `closet_items` | id, user_id, category, subcategory, colors[], pattern, material, image_url, cutout_url, size_info(jsonb), tags_confirmed, created_at | 내 옷 |
| `products` | id, partner_id, name, brand, price, category, subcategory, colors[], image_url, cutout_url, size_chart(jsonb), product_url | 쇼핑몰 상품 |
| `outfits` | id, user_id, name, created_at | 저장한 코디 |
| `outfit_items` | outfit_id, slot(top/bottom/outer/…), closet_item_id 또는 product_id | 코디 구성 |
| `jobs` | id, user_id, type, status(pending/running/done/failed), result(jsonb), error, created_at | 비동기 AI 작업 |

- ID는 UUID, 시간은 UTC `timestamptz`.
- **사진 원본 URL은 저장하지 않거나 분석 후 지운다** (`DELETE_ORIGINAL_BODY_PHOTO=true`).

## 5. 배포 (예정)

- MVP 데모: 프론트 정적 호스팅(Vercel 등) + 백엔드 컨테이너(GPU 없는 CPU 인스턴스, 경량 모델)
- 고도화: GPU 워커 분리. 결정 시 `DECISIONS.md`에 기록.
