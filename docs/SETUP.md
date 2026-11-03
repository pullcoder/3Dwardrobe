# 로컬 설치·실행·검증

Python 3.12와 Node 24/npm을 사용한다. 3단계 CPU 추론은 PyTorch·CLIP·SAM과 Node Tesseract OCR을 사용한다. 외부 AI API 키는 필요 없다.

## 백엔드

복원 정책 변경 후 기존 DB에는 서버 실행 전에 `backend/`에서 `.venv/Scripts/python -m alembic upgrade head`를 적용한다. Alembic 버전 없이 기존 3단계 테이블만 있는 DB는 스키마 비교 후 초기 revision 75730b3d1871에 stamp하고 upgrade한다. 데이터가 있는 DB를 삭제해서 초기화하지 않는다.

루트에서:
```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -r backend/requirements.lock.txt
cd backend
cd ocr
npm ci
cd ..
.venv/Scripts/python scripts/prepare_models.py
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

가상환경 활성화 없이 실행하므로 PowerShell 실행 정책을 변경할 필요가 없다.
macOS/Linux는 `.venv/Scripts/python` 대신 `.venv/bin/python`을 사용한다.
API: http://127.0.0.1:8000/docs . `APP_ENV=production`은 현재 설정에서 거절한다.
로컬 개발 API는 원격 클라이언트를 거절한다. 모바일 실기기 원격 접속용 배포를 하지 않는다.

## 프론트

5단계는 마이그레이션 d51e2a7b0903까지 적용한 API를 사용한다. 로그인→옷장 불러오기→피팅 스튜디오→실제 GLB가 생성된 의류 선택 순으로 실행한다. 새 GLB 생성에는 기존 4단계 워커가 필요하지만 이미 생성된 의류를 입히는 데는 워커가 필요하지 않다.
기본 편집은 탭 메모리다. 코디/피팅을 저장할 때만 최소 체형 수치 서버 저장 동의를 선택한다. 저장한 코디는 스튜디오 또는 옷장의 코디 보관함에서 불러온다. 사진 체형 원본/관절은 전송하지 않는다.
검사: `npx playwright test e2e/fitting.spec.ts`는 실제 워커로 GLB를 만들고 데스크톱/모바일의 장착·저장·재조회·철회·로딩 실패·터치를 확인한다. 테스트 전 `npm run prepare:test-garments`를 실행하거나 전체 `npm run test:e2e`를 사용한다. 검증용 Python은 STYLEFIT_TEST_PYTHON으로 지정할 수 있다.

4단계 생성에는 API 외에 `backend/`의 별도 터미널에서 `.venv/Scripts/python -m app.generation_worker`를 실행한다. 같은 DATABASE_URL을 사용해야 하며 워커가 없으면 queued 상태다. `--once`는 작업 한 건만 처리하는 점검용이다. 기존 DB는 API/워커 시작 전 Alembic upgrade head로 c41d8f03a902까지 적용한다.
직접 작성한 A 템플릿 생성은 기본 requirements.txt만으로 가능하며 외부 생성 가중치/GPU를 요구하지 않는다. 기존 3단계 AI 분석까지 실행하려면 requirements.lock.txt와 prepare_models.py의 가중치가 필요하다.

새 터미널, 루트에서:
```powershell
cd frontend
npm ci
npm run dev
```

http://127.0.0.1:5173 . 포트 5173이 사용 중이면 자동 우회하지 않고 종료한다.
필요 시 `frontend/.env.example` → `frontend/.env`로 복사한다. Vite는 루트 `.env`를 읽지 않는다.
백엔드는 루트 `.env`를 명시 경로로 읽으며 CORS_ORIGINS는 JSON 배열이다.

## 향후 사용할 DB/Redis (선택)

Docker Desktop이 설치된 경우에만 루트 `.env.example`을 `.env`로 복사하고 비밀번호를 설정한다.
```powershell
docker compose up -d db redis
docker compose ps
```
기본은 `backend/storage/stylefit.db` SQLite 개발 DB다. API 시작 시 로컬 초기 스키마를 생성한다.
PostgreSQL을 사용할 때 루트 `.env`의 `DATABASE_URL=postgresql+psycopg://사용자:암호@127.0.0.1:5432/stylefit`을 설정한다. Redis는 미사용이다.
새 DB에는 `backend/`에서 `.venv/Scripts/python -m alembic upgrade head`를 적용한다. 이미 3단계 create_all로 만든 동일 스키마는 비교 후 `alembic stamp head`로 기준 버전을 기록할 수 있다.
PostgreSQL 실행 환경은 이 머신에 없어 실접속 미검증이다. SQLite 마이그레이션 왕복·PostgreSQL SQL 생성은 별도로 검사한다.

## 검사

`backend/`에서:
```powershell
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m ruff format --check .
.venv/Scripts/python -m pytest -q
```

`frontend/`에서:
```powershell
npm run lint
npm run typecheck
npm run build
npm test
npm run prepare:test-photo
npx playwright install chromium
npm run test:e2e
```

Playwright는 로컬 프론트/API를 띄워 실제 파일 업로드 경로를 검사한다. 기존 5173/8000 서버가 있으면 재사용한다.
별도 검증 가상환경을 쓰면 PowerShell에서 `$env:STYLEFIT_TEST_PYTHON = '사용할 python.exe 절대 경로'`를 설정한다. E2E 설정·합성 fixture 준비·4단계 테스트 워커가 이 경로를 사용하며 기본은 backend/.venv다. 루트 .env를 자동으로 테스트 프로세스 환경에 주입하는 기능은 아니다.
4단계 단독 브라우저 검사: `npx playwright test e2e/generation.spec.ts`. 이 테스트는 실제 별도 워커를 시작/종료하며 상의·바지·겉옷을 생성한다. API와 같은 DATABASE_URL을 지정한다. 사용자 데이터가 없는 별도 테스트 DB를 권장한다.
검증 산출물: backend에서 `.venv/Scripts/python scripts/verify_generation.py` → Git 제외 storage/phase4-validation/{tshirt,pants,jacket}.glb 및 results.json. 별도 Three.js 재로딩 검사는 frontend에서 `node scripts/verify-garment-glb.mjs`로 실행한다.
실행 결과·제약은 `docs/VERIFICATION.md`를 참고한다.

## 2단계 모델과 테스트 준비

`npm run dev`/`npm run build`의 사전 스크립트가 SDK 0.10.35의 WASM과 Full float16 v1을 같은 출처에 준비한다.
모델 해시가 다르면 시작/빌드를 중단한다. 이미 받은 파일이 있으면 모델을 다시 다운로드하지 않는다.
오프라인 최초 설치에는 `npm run prepare:vision`을 미리 실행해야 한다.
`npm run prepare:test-photo`는 MediaPipe 공식 테스트 사진 한 장을 Git 제외 폴더에 받는다. 제품에는 포함하지 않는다.
생성된 `dist/mediapipe/`를 배포에서 누락하면 분석이 실패한다. 아직 공개 배포하지 않는다.
Worker CSP: `default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self';`.
개발/미리보기 외 호스팅에서는 `/pose-worker.js` 응답에도 해당 정책을 설정해야 한다.
현재 2단계 검사 결과는 [VERIFICATION_PHASE2.md](VERIFICATION_PHASE2.md)에 기록한다.

## 3단계 모델·실행

- `backend/requirements.lock.txt`는 CPU PyTorch 인덱스와 Git 커밋을 고정한다. GPU/CUDA 설치나 시스템 드라이버 변경은 하지 않는다.
- `backend/scripts/prepare_models.py`: 공식 고정 URL 다운로드와 4개 가중치 SHA-256 검사. 런타임에서도 모델 첫 사용 시 해시를 확인한다. 누락/불일치는 503 오류이며 대체 가짜 결과를 만들지 않는다.
- `backend/ocr`의 `npm ci`가 필요하다. OCR은 Node worker와 로컬 kor+eng 학습 데이터를 사용하며 사진 임시 파일을 만들지 않는다.
- `frontend`에서 `npm run test:e2e`는 합성 티셔츠·라벨 fixture를 먼저 준비한다. 한글 fixture는 Windows `C:/Windows/Fonts/malgun.ttf`가 필요하며 다른 OS에서는 검증 스크립트의 폰트 경로를 조정해야 한다.
- 실제 AI 독립 검증: `backend/`에서 `.venv/Scripts/python scripts/verify_garment_ai.py`. 테스트 이미지는 Git 제외 fixture 폴더에만 생성한다.
- 의류 CPU 분석 동시 1건, 추가 요청 429. 브라우저에서 재시도할 수 있으며 서버 큐·작업 영속화는 없다. Playwright는 실제 AI 경합을 피하려고 worker 1개로 실행한다.
- SQLite DB·가중치·언어 데이터·node_modules·fixture·테스트 결과는 커밋하지 않는다. `ADMIN_REVIEW_KEY`는 관리자 신고 검토 API용 서버 비밀값이다. 프론트 환경변수로 넣지 않는다.
