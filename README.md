# CLOSET-VERSE (3Dwardrobe)

> AI 체형 분석 기반 3D 가상 옷장 + 크로스 피팅 커머스 플랫폼

사진 한 장으로 **내 체형**과 **내 옷장**을 디지털화하고, 사려는 새 옷이 이미 가진 옷과
얼마나 어울리는지 AI가 알려주는 웹 서비스입니다.

```
내 체형 등록 → 내 옷장 등록 → 함께 입혀보기(크로스 피팅) → AI 판단(매칭 점수·빈자리·사이즈)
```

## 핵심 기능

| # | 기능 | 한 줄 설명 |
|---|------|-----------|
| ① | 체형 분석 | 전신 사진 또는 수치 → MediaPipe 분석 → 수동 보정 → 2.5D 템플릿(MVP) / 3D 메시 아바타(M+6) |
| ② | 디지털 옷장 | 옷 사진 → 누끼 → VLM 태깅(카테고리·색상 팔레트·소재·패턴·스타일) + OCR 사이즈표 |
| ③ | 크로스 피팅 | 쇼핑몰 상품 + 내 옷을 겹쳐 입히기: 2.5D 레이어드 뷰어(MVP) → 3D 360° 회전(M+6) |
| ④ | AI 추천 | 매칭 점수 0~100, "옷장 속 7벌과 70점 이상으로 어울립니다" + 빈자리·사이즈 추천 |
| B2B | 자동 에셋 변환 | 브랜드가 이미지 + 사이즈표만 올리면 2.5D/3D 에셋과 치수 매핑 자동 생성 (위젯·API) |

자세한 기획은 [docs/PLAN.md](docs/PLAN.md)를 보세요.

## 기술 스택

- **Frontend**: React + TypeScript, Vite, Tailwind CSS
- **피팅 뷰어**: 2.5D 스키닝 레이어드 뷰어(MVP), Three.js + React Three Fiber 3D 뷰어(M+6)
- **Backend**: Python 3.11, FastAPI, Celery + Redis (비동기 AI 추론)
- **AI**: MediaPipe Pose, 상업용 오픈소스 3D 인체 메시(MakeHuman 기반 등), RMBG / SAM + OpenCV, VLM, OCR
- **Data**: PostgreSQL, 로컬/오브젝트 스토리지(이미지·3D 파일)

## 폴더 구조 (요약)

```
3Dwardrobe/
├── frontend/        # React 웹 앱
├── backend/         # FastAPI 서버 + Celery 워커 + AI 파이프라인
├── docs/            # 기획·설계·규칙 문서
├── AGENTS.md        # AI 코딩 도구 공통 지시서 (Codex 등)
├── CLAUDE.md        # Claude Code 지시서 (AGENTS.md를 불러옴)
└── .env.example     # 환경변수 예시
```

전체 구조는 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)에 있습니다.

## 빠른 실행

> 처음이라면 [docs/SETUP.md](docs/SETUP.md)부터 따라 하세요.
> ⚠️ 아직 코드 뼈대가 없어서 아래 명령은 `docker-compose.yml`, `backend/`, `frontend/`가 추가된 뒤(TASKS T0-3~T0-5)부터 동작합니다.

```bash
# 0) 환경변수
cp .env.example .env            # Windows PowerShell: copy .env.example .env

# 1) DB + Redis (Docker)
docker compose up -d db redis

# 2) 백엔드
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload   # http://localhost:8000/docs

# 2-1) AI 워커 (새 터미널, backend 폴더, 가상환경 켠 상태)
celery -A app.workers.celery_app worker --loglevel=info --pool=solo   # --pool=solo는 Windows용

# 3) 프론트엔드 (새 터미널)
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

## 문서 안내

| 문서 | 내용 |
|------|------|
| [PLAN.md](docs/PLAN.md) | 기획 요약, 기능 명세 |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 시스템 구조, 폴더 구조, DB 개요 |
| [API.md](docs/API.md) | REST API 명세 |
| [CONVENTIONS.md](docs/CONVENTIONS.md) | 코딩·네이밍·주석 규칙 |
| [GIT_GUIDE.md](docs/GIT_GUIDE.md) | Git 사용법과 협업 흐름 |
| [SETUP.md](docs/SETUP.md) | 개발 환경 설치 |
| [TASKS.md](docs/TASKS.md) | 단계별 할 일, 담당자 |
| [DECISIONS.md](docs/DECISIONS.md) | 주요 결정과 이유 |

## 팀

팀원과 역할은 [docs/TASKS.md](docs/TASKS.md#팀-역할)에서 관리합니다.
