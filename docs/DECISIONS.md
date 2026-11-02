# StyleFit AI 결정 기록

## S-007. 사용자 요청으로 의류 AI·등록과 필수 저장 기반 착수

- 날짜: 2026-11-03 / 근거: 사용자 3단계 개발 프롬프트 / 상태: 구현
- OpenCLIP ViT-B-32 LAION-2B s34B b79K 코드·가중치 MIT, SAM ViT-B Apache-2.0, Tesseract.js/core·tessdata_fast kor+eng Apache-2.0. 공식 출처·커밋·해시·LICENSE를 고정한다. 원본 OpenAI CLIP 가중치는 별도 조건 확인 질의가 미해결이라 최종 파이프라인에서 제외했다.
- GTX 1060 6GB/드라이버 457.51 환경에서 CUDA 업그레이드 없이 CPU를 사용한다. 분류·분리·OCR 순차 처리, threadpool·동시 1건. 운영 워커/큐 분리는 보류한다.
- OCR의 Node 실행 의존성을 명시한다. stdin으로 사진을 넘겨 Node worker/WASM에서 처리하고 디스크 사진·캐시를 만들지 않는다.
- PostgreSQL용 SQLAlchemy/psycopg와 Alembic을 도입한다. 이 머신에 PostgreSQL/Docker가 없어 SQLite 개발 DB로 실제 저장·삭제를 검증하고 PostgreSQL SQL 생성만 별도 확인한다. 실접속 검증 완료로 표시하지 않는다.
- UUID DB binary 에셋과 본인 소유권 다운로드, 암호 재확인 계정 삭제. 원본 분석과 사용자 수정 정보는 별도 JSON이다.
- 간단한 로컬 계정은 실명/이메일 수집 없이 scrypt와 Bearer 해시 세션을 사용한다. 운영 인증 복구·공유 제한기·관리자 인증 강화·HTTPS는 출시 전 필요하다.
- 실제 생성형 모델은 도입하지 않는다. 4단계 의류 복원과 5단계 피팅은 다음 지시까지 착수하지 않는다.

## S-001. 사용자 통합 개발 프롬프트 v2.0 채택

- 날짜: 2026-11-03 / 근거: 사용자 명시 요청 / 상태: 확정
- CLOSET-VERSE·제휴몰/B2B 중심 계획을 StyleFit AI·사용자 업로드 전용 계획으로 전환한다.
- 과거 문서는 `docs/archive/`에 보존하며 현재 원본은 루트의 5개 검토 문서다.
- 이번에는 0·1단계만 구현하고 보고 후 다음 지시를 기다린다.

## S-002. 1단계는 로컬 메모리 세션 프로토타입

- 날짜: 2026-11-03 / 상태: 현재 단계 구현 선택
- 인증·비공개 영구 저장이 없는 단계에서 사진을 서버에 보관하지 않는다.
- 권리·전송 안내 확인 뒤 로컬 API가 원시 이미지 바이트를 검증하고 폐기한다.
- 8개 화면 중 AI·3D·신고·저장은 준비 상태를 명시한다. 가짜 점수·가짜 생성 결과 없음.
- PostgreSQL/Redis Compose 구성만 준비하며 현재 연결 상태라고 표시하지 않는다.

## S-003. 도구와 런타임

- 날짜: 2026-11-03 / 근거: 사용자 지정 스택·현재 머신 환경
- Node 24, Python 3.12에서 기반을 검증한다. AI 워커 런타임은 모델 선정 후 별도 고정한다.
- Vite 템플릿의 TypeScript 7은 typescript-eslint의 지원 범위를 벗어나 5.9로 고정했다.
- Tailwind Vite 플러그인, Lucide(ISC/일부 Feather 파생 아이콘 MIT) 아이콘, ESLint/React Hooks/접근성 규칙, Prettier, Playwright를 사용한다.
- 백엔드는 FastAPI/Pydantic Settings/Uvicorn, Pillow 디코딩, pytest/httpx/ruff.
- TanStack Query/Zustand/Three.js/R3F/Celery/SQLAlchemy/Alembic은 실제 기능 단계에 도입한다.
- 외부 사진·폰트·모델 없이 직접 제작한 SVG 컨셉 일러스트와 시스템 폰트를 사용한다.

## S-004. AI 모델은 아직 선택·연결하지 않음

- 날짜: 2026-11-03 / 상태: 사전 검토 완료, 도입 결정 보류
- Hunyuan3D-2.1 공개 라이선스의 한국 지역 제외, RMBG-2.0 공개 가중치 상업 계약 조건 확인.
- TRELLIS 본체 MIT만으로 전체 파이프라인이 승인된다고 보지 않는다.
- 모든 후보·근거·미확인은 `AI_LICENSE_AUDIT.md`에 기록한다.

## S-005. 사용자 요청으로 2단계 착수

- 날짜: 2026-11-03 / 근거: 사용자 2단계 개발 프롬프트 / 상태: 확정
- 0·1단계 구조와 의류 흐름을 유지하고 체형 분석·3D 마네킹만 확장한다. 의류 AI·가상 피팅은 착수하지 않는다.
- MediaPipe Tasks Vision 0.10.35, Pose Full float16 v1을 고정하고 SHA-256을 검사한다.
- 브라우저 classic Worker에 공식 standalone CJS 번들을 격리한다. ESM Worker의 importScripts 제약을 피한다.
- 입력 사진은 최대 변 1600px로 처리하며 CPU 추론한다. 동일 출처 에셋과 Worker CSP로 외부 통신을 차단한다.
- 정수리와 둘레는 관절만으로 직접 관찰할 수 없다. 정수리 높이는 경험적 근사, 둘레는 직접 입력/기본값으로 둔다.
- 사진·수동 프로필은 별개다. 키 변경은 사진 추정 길이만 갱신하며 사용자 수정 길이는 유지한다.

## S-006. 파라미터 마네킹과 선택적 기기 저장

- 날짜: 2026-11-03 / 상태: 2단계 구현 선택
- Three.js/R3F를 요청에 따라 도입한다. torso 타원 단면, 팔다리 capsule, 중립 얼굴을 직접 생성한다.
- 부위 name·meter/Y-up/Z-front 규격·garment_anchors로 이후 의류 모듈 경계를 제공한다. 실제 리깅/드레이핑은 아니다.
- 기본 체형은 탭 메모리만 사용한다. 명시 저장은 Web Crypto(PBKDF2-SHA256 310k → AES-256-GCM)로 치수·출처·요약 비율만 암호화한다.
- 저장마다 무작위 salt/IV, 암호·사진·개별 관절 좌표 저장 금지. 기존 보관함 덮어쓰기/삭제는 같은 이름과 암호로 검증한다.
- 이 저장소는 서버 계정 인증/인가를 대체하지 않는다. 실제 서버 개인정보 저장은 인증·소유권·삭제 기반을 갖춘 뒤 도입한다.
- Vitest로 추정/출처/기하와 저장 경계를 검사하며, Playwright로 실제 MediaPipe·Canvas·저장 동작을 검증한다.
