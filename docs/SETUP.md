# SETUP — 개발 환경 설치

> Windows 기준으로 쓰고, macOS/Linux 차이는 괄호로 적었습니다.
> 막히면 이 문서에 해결 방법을 추가해 주세요 (맨 아래 "문제 해결").

## 1. 필요한 프로그램

| 프로그램 | 버전 | 확인 명령 | 비고 |
|---------|------|----------|------|
| Git | 최신 | `git --version` | |
| Node.js | 20 LTS 이상 | `node -v` | npm 포함 |
| Python | **3.11** | `python --version` | MediaPipe 호환 때문에 3.11 권장 |
| Docker Desktop | 최신 | `docker --version` | PostgreSQL 실행용 |
| VS Code | 최신 | | 권장 에디터 |

**VS Code 추천 확장**: Python, Pylance, Ruff, ESLint, Prettier, Tailwind CSS IntelliSense, GitLens

> Docker를 못 쓰면 PostgreSQL 16을 직접 설치해도 됩니다. 이 경우 `.env`의 접속 정보만 맞추면 됩니다.

## 2. 저장소 받기

```bash
git clone https://github.com/pullcoder/3Dwardrobe.git
cd 3Dwardrobe
git config user.name "이름"
git config user.email "메일"
```

## 3. 환경변수

```bash
cp .env.example .env          # Windows PowerShell: copy .env.example .env
```

`.env`에서 최소한 다음을 채웁니다: `POSTGRES_PASSWORD`, `DATABASE_URL`의 비밀번호, `JWT_SECRET`.
AI 관련 키(`VLM_API_KEY`, `OCR_API_KEY`)는 팀 비공개 채널에서 받습니다. **채팅·이슈·커밋에 키를 붙여넣지 마세요.**

## 4. 데이터베이스 (PostgreSQL) + Redis

Redis는 Celery 작업 큐(AI 비동기 추론)에 쓰입니다.

```bash
docker compose up -d db redis # 실행
docker compose ps             # 상태 확인
docker compose down           # 종료 (데이터는 볼륨에 유지)
```

> `docker-compose.yml`은 초기 세팅 작업(TASKS T0-3)에서 추가됩니다.

## 5. 백엔드 (FastAPI)

```bash
cd backend
python -m venv .venv

# 가상환경 켜기
.venv\Scripts\activate         # macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
alembic upgrade head           # DB 테이블 생성
uvicorn app.main:app --reload
```

AI 작업은 별도 워커가 처리합니다. **새 터미널**에서 (backend 폴더, 가상환경 켠 상태):

```bash
celery -A app.workers.celery_app worker --loglevel=info --pool=solo
```

- `--pool=solo`: Windows에서 Celery 기본 실행 방식이 동작하지 않아 필요합니다. macOS/Linux는 빼도 됩니다.
- 워커를 켜지 않으면 업로드 후 작업이 계속 `pending`으로 남습니다.

- API 문서: http://localhost:8000/docs
- PowerShell에서 `activate`가 막히면: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### AI 모델 가중치

- 가중치는 Git에 올리지 않습니다. `backend/models/weights/`에 둡니다.
- **3D 인체 메시 (M+6부터)**: 상업 이용이 허용된 오픈소스 메시(MakeHuman 기반 등)를 사용합니다. 받는 방법은 T2-1 결정 후 여기에 추가합니다.
- **SMPL/SMPL-X는 비상업용 라이선스**라 개인 실험용으로도 이 저장소에 넣지 않습니다. (`DECISIONS.md` D-010)
- MediaPipe, RMBG 등은 첫 실행 시 자동 다운로드되거나 설치 스크립트로 받습니다. (방법이 정해지면 여기 추가)

## 6. 프론트엔드 (React)

```bash
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

| 명령 | 설명 |
|------|------|
| `npm run dev` | 개발 서버 |
| `npm run build` | 배포용 빌드 |
| `npm run lint` | ESLint |
| `npm run typecheck` | 타입 검사 |
| `npm run test` | Vitest |

## 7. 실행 확인 체크리스트

- [ ] http://localhost:8000/docs 가 열린다
- [ ] http://localhost:5173 이 열린다
- [ ] 프론트에서 백엔드 호출 시 CORS 에러가 없다 (`.env`의 `CORS_ORIGINS` 확인)

## 8. AI 코딩 도구

- **Claude Code**: 저장소 루트에서 실행하면 `CLAUDE.md`(→ `AGENTS.md`)를 자동으로 읽습니다.
- **Codex**: 저장소 루트의 `AGENTS.md`를 자동으로 읽습니다.
- 공통 규칙을 바꿀 때는 `AGENTS.md`만 고치면 두 도구에 모두 반영됩니다.

## 9. 문제 해결

| 증상 | 해결 |
|------|------|
| `pip install mediapipe` 실패 | Python 버전 확인 (3.11 권장). 3.13 이상이면 휠이 없을 수 있음 |
| 작업이 계속 `pending` | Celery 워커가 켜져 있는지, Redis가 실행 중인지(`docker compose ps`) 확인 |
| `port 5432 already in use` | 로컬에 설치된 PostgreSQL 종료하거나 `.env`/compose 포트 변경 |
| `npm install` 권한 에러 | 관리자 권한 터미널 X, 프로젝트 폴더를 OneDrive 밖으로 옮겨보기 |
| (추가해 주세요) | |
