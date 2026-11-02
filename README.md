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
| ① | 체형 분석 · 3D 아바타 | 전신 사진 + 키 입력 → MediaPipe 분석 → 치수 보정 → SMPL 아바타 |
| ② | 디지털 옷장 | 옷 사진 → 누끼 → AI 태깅(종류·색·무늬·소재) + OCR 사이즈 |
| ③ | 크로스 피팅 | 쇼핑몰 신상품 + 내 옷을 아바타에 함께 입혀 360° 확인 |
| ④ | AI 추천 | "옷장의 7벌과 어울립니다" 매칭 점수, 빈자리 추천, 사이즈 추천 |

자세한 기획은 [docs/PLAN.md](docs/PLAN.md)를 보세요.

## 기술 스택

- **Frontend**: React + TypeScript, Vite, Tailwind CSS
- **3D**: Three.js, React Three Fiber (`@react-three/fiber`, `@react-three/drei`)
- **Backend**: Python 3.11, FastAPI
- **AI**: MediaPipe Pose, SMPL 계열 모델, RMBG / SAM + OpenCV, VLM(의류 태깅), OCR
- **Data**: PostgreSQL, 로컬/오브젝트 스토리지(이미지·3D 파일)

## 폴더 구조 (요약)

```
3Dwardrobe/
├── frontend/        # React 웹 앱
├── backend/         # FastAPI 서버 + AI 파이프라인
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

# 1) DB (Docker)
docker compose up -d db

# 2) 백엔드
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload   # http://localhost:8000/docs

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
