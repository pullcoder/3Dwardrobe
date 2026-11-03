# 4단계 A 우선 의류 3D 생성 검증

브랜치: feature/phase4-garment-generation. 이전 A/B 정책 작업의 미커밋 변경을 보존해 이어서 작업했다. 커밋·푸시·공개 배포·5단계 실제 피팅은 하지 않았다.

## 구현과 사용 기술

- A: 직접 작성한 9종 파라미터 템플릿의 실제 삼각형 표면·단색 PBR 재질·자체 포함 glTF 2.0 GLB를 CPU로 생성한다. 기존 AI의 앞/뒤 분석 제안과 사용자 수정 정보, 의미/단위가 분명한 의류 치수를 사용한다. 사진 픽셀/고유 그래픽/자유 서술은 생성기에 전달하지 않는다. 신경망 Image-to-3D나 물리 시뮬레이션을 실행했다고 표시하지 않는다.
- 종류: 티셔츠·셔츠·니트·재킷·코트·청바지·슬랙스·반바지·스커트. 소매 길이·넥라인·실루엣·색·유효 치수를 반영한다. 후드티·카디건·패딩·기타/unknown은 미지원으로 안내한다.
- 권한: 사진 처리 사용자 확인 confirmed와 관리자 문서 검증 verified를 구분한다. 사진 미확인은 보류, 사진 확인/나머지 미검증은 A, 세 권한 verified이면 B 자동 선택이다. 사용자가 verified를 직접 제출할 수 없다. B의 실제 생성 엔진은 없으므로 B 선택 시 503으로 명시 차단한다.
- 증빙: 실제 PDF/이미지를 별도 동의 후 비공개 저장한다. 참조/체크박스만으로 승인하지 않는다. 관리자 키 전용 문서 다운로드·세 범위별 판단·증빙 ID·근거·버전·시각·검토 이력을 제공한다. 법적 진위 판단은 담당자가 수행해야 한다.
- 생성: 영속 SQLAlchemy DB 큐→별도 프로세스 워커→메시·재질→GLB 검증→비공개 Asset 저장. 실제 단계만 표시한다. queued/processing/completed/failed/cancelled, 재시도, API 재시작 후 조회, lease 만료 복구를 지원한다.
- 중단/삭제: 모델·의류 삭제, 정보 수정, 권한 변경·철회·권리 신고 시 모델을 제거하고 작업을 취소한다. 작업 토큰·권한 버전·의류 revision을 저장 직전에 검사해 늦은 결과의 재생성을 차단한다. 소유권/현재 권한 검사는 모델 API와 기존 Asset 경로 모두에 적용한다.
- UI: 옷장→3D 복원→원본/분석·수정 정보/권한→생성 상태→인증된 GLB 뷰어. 실제 GLB를 Three.js GLTFLoader로 불러오고 R3F로 렌더링한다. 360도 드래그·확대/축소·정면/측면/후면·초기화를 제공한다. 모델 삭제/재생성, 원본 비보관 의류도 지원한다.

## 실제 GLB 산출물

합성 수동 의류 정보를 사용한 검증 파일이며 사용자 원본 사진이나 제3자 의류 자산은 아니다. Git 제외 storage에만 저장했다.

| 파일 | 바이트 | 메시/삼각형 | Three.js 재로딩 경계 크기 (m) |
|---|---:|---:|---|
| [tshirt.glb](../backend/storage/phase4-validation/tshirt.glb) | 21,332 | 3 / 768 | 0.792025 × 0.68 × 0.24 |
| [pants.glb](../backend/storage/phase4-validation/pants.glb) | 17,924 | 3 / 576 | 0.3744 × 1.02 × 0.2392 |
| [jacket.glb](../backend/storage/phase4-validation/jacket.glb) | 21,348 | 3 / 768 | 1.156025 × 0.72 × 0.238826 |

Python 자체 검증과 독립된 실제 Three.js GLTFLoader 재로딩, 유한 입체 범위·삼각형 비퇴화·법선 단위 길이·재질 연결·메타데이터·이미지 텍스처 부재를 확인했다. [해시/생성 메타데이터](../backend/storage/phase4-validation/results.json), [Three.js 결과](../backend/storage/phase4-validation/three-validation.json).
모델은 일반 표면이며 몸판/소매/바지통이 겹치는 별도 메시다. 봉제 가능한 연속 토폴로지나 정밀 실제 의류 복원을 보장하지 않는다. 뒤/깊이/없는 치수는 추정이다.

## 실행한 검사

검증 환경: Windows, Python 3.12.10의 backend/.venv-policy, Node 26.13.0/npm 11.20.0. 프로젝트 안내의 Node 24와 실제 검증 버전을 구분한다. 기존 Python 3.10 .venv는 변경하지 않았다. 검증 환경에는 기존 requirements.lock.txt 전체를 설치했고 pip check가 통과했다. 기존 고정 CLIP/SAM/Tesseract 가중치 4개도 prepare_models.py로 다운로드·SHA-256 검증했다. 새 생성형 모델은 설치하지 않았다.

| 명령/검사 | 결과 |
|---|---|
| backend ruff check . | 통과 |
| backend ruff format --check . | 36개 파일 통과 |
| backend pytest | 53개 통과 |
| SQLite Alembic upgrade head / check / downgrade b34a9c12d701 / upgrade head | 통과, ORM과 스키마 차이 없음 |
| PostgreSQL alembic upgrade head --sql | SQL 생성 통과, 실제 DB 접속 미검증 |
| frontend npm run lint / typecheck / build | 통과, 기존 Three.js 관련 큰 청크 경고 |
| frontend npm test | 8개 통과 |
| npm run test:e2e | 최종 전체 재실행 22개 통과 (3.2분), 실제 CLIP/SAM/OCR·체형·마네킹·3D 생성 포함 |
| 추가 모바일 터치/핀치 검증 | generation.spec.ts 모바일 1개 통과, 세 의류에서 실제 touchStart/touchMove/touchEnd 회전·두 손가락 확대 후 캔버스 변화 확인 |
| scripts/verify_generation.py → scripts/verify-garment-glb.mjs | 세 GLB 저장/실제 재불러오기 통과 |

첫 전체 E2E는 21/22 통과였다. 실제 CLIP/SAM/OCR·3D 생성은 양쪽 모두 통과했으며 기존 모바일 메뉴 테스트에서 이전 해시 이동의 메뉴 닫힘을 기다리지 않는 타이밍 문제가 있었다. 클릭 전후 메뉴 상태를 기다리도록 helper를 보완했다. 테스트/검증 항목을 삭제·skip하거나 강제 클릭으로 우회하지 않았다. 해당 모바일 4개 회귀 테스트는 별도 재실행으로 통과했다.

백엔드는 사진 미확인 차단, A/B 자동 선택, 사용자/타인/관리자 경계, 실제 증빙 요구, 9종 실제 GLB/재질/좌표, 실패/잘못된 GLB/재시도, lease 회수, API 재시작 후 큐 유지, 삭제/신고/철회/수정 중 늦은 결과 차단, 실제 증빙/판단/모델/작업의 계정 삭제 cascade를 확인했다.
브라우저는 실제 별도 워커로 티셔츠·청바지·재킷 생성, 인증 모델 GET/GLB 헤더, 실제 WebGL 렌더링, 정면/측면/후면/확대/축소/초기화·드래그에 따른 캔버스 변화, 종류별 다른 형상, 모델 삭제 및 가로 넘침 부재를 데스크톱/모바일에서 확인했다. 이후 추가한 Chromium 터치 이벤트의 회전·핀치 확대도 모바일 테스트에서 통과했다. 자동 테스트의 모바일 뷰포트는 Android 실기기 인증을 의미하지 않는다. [모바일 상의 화면](../frontend/test-results/phase4-top-mobile.png), [바지](../frontend/test-results/phase4-bottom-mobile.png), [겉옷](../frontend/test-results/phase4-outer-mobile.png).

## 라이선스와 미구현

A의 기하/재질/GLB writer는 프로젝트 직접 작성이며 외부 의류 자산/가중치/원본 텍스처를 포함하지 않는다. 기존 Three.js/R3F(MIT), 기존 3단계 AI 라이선스와 고지를 유지한다. [AI_LICENSE_AUDIT.md](../AI_LICENSE_AUDIT.md)의 공식 근거와 B 후보 재검토를 확인한다.
B의 TRELLIS/TRELLIS.2 후보는 본체 라이선스 외 전체 렌더링 종속성·의류 품질·다중 이미지 경로·실제 GPU/속도/비용/출력 조건을 검증하지 못했다. 설치/상업 승인/실제 생성으로 표시하지 않는다. B_ENGINE_AVAILABLE=false다.
PostgreSQL 실접속, 실제 저사양 모바일/Android, 운영 HTTPS·담당자별 관리자 인증·자동 만료/지역/기간 제한·공개 외부 권리자 신고/삭제 운영, 대규모 GPU/Celery 분산 큐는 미구현/미검증이다.

## 5단계 준비

GLB garment_root.extras에 카테고리·크기/출처·미터/Y-up/Z-front·right-handed·pivot/attachment_anchor·마네킹 chest/waist/shoulder 대응·layer·메시/재질 이름·A/B 모드·생성 버전/날짜를 포함한다. 공통 모델 계약만 준비했으며 체형에 실제 장착·리깅·충돌·원단 시뮬레이션은 하지 않았다. 5단계 지시를 기다린다.

## 변경 파일

이전 A/B 정책 파일도 작업 트리에 보존되어 있다. 그 파일별 기록은 [이전 보고서](VERIFICATION_RECONSTRUCTION_POLICY.md)를 참고한다. 이번 4단계 변경은 다음과 같다.

| 파일 | 이유 |
|---|---|
| backend/app/services/garment_mesh.py | 직접 제작 템플릿·정보/치수 해석·GLB writer/검증 |
| backend/app/services/generation.py | 자동 선택·영속 큐·claim/lease·생성·무효화·모델 접근 |
| backend/app/generation_worker.py | API와 분리된 워커 명령 |
| backend/app/api/v1/generation.py | 생성/상태/모델/증빙/관리자 판단 API |
| backend/app/api/v1/garments.py | 생성 정책 응답·사진 사용자 확인·수정/신고 무효화·Asset 보호 |
| backend/app/services/reconstruction.py | 검토 재신청의 증빙/소유권 검사 및 기존 작업 무효화 |
| backend/app/models.py | 권한·생성 상태·작업/증빙/판단 DB 모델 |
| backend/app/schemas/garments.py | 관리자 범위별 판단·증빙 참조·신고 종류 입력 |
| backend/app/main.py | 4단계 라우터/CORS·API 버전 |
| backend/migrations/versions/c41d8f03a902_phase4_generation.py | 기존 스키마를 보존하는 4단계 마이그레이션 |
| backend/scripts/verify_generation.py | 합성 입력의 GLB 검증 파일 생성 |
| backend/tests/test_generation.py | 실제 메시·작업·권한·실패/삭제/재시작 회귀 |
| frontend/src/features/garments/GenerationPanel.tsx | 자동 모드/권한·큐 상태·생성/재시도/삭제·모델 로딩 |
| frontend/src/features/garments/GarmentModelViewer.tsx | 실제 GLB 로더·R3F 뷰어·회전/줌/시점·자원 해제 |
| frontend/src/features/garments/GarmentDetail.tsx | 생성 화면·증빙/보완 제출·신고 종류 연결 |
| frontend/src/features/garments/types.ts | 생성/권한/GLB 메타데이터 타입 |
| frontend/src/types/domain.ts | 옷장의 3D 상태 타입 |
| frontend/src/api/garments.ts | 실제 생성/상태/모델/권한/증빙 API 경계 |
| frontend/src/routes/ClosetPage.tsx | 3D 복원 진입·저장/처리 배지 |
| frontend/src/routes/UploadPage.tsx | 실제 A 지원·B 비활성 안내 |
| frontend/src/App.tsx, frontend/src/routes/Dashboard.tsx | 현재 4단계 범위 표시 |
| frontend/e2e/generation.spec.ts | 실제 워커/GLB/캔버스/모바일 검증 |
| frontend/e2e/foundation.spec.ts | 기존 모바일 메뉴의 비동기 상태 대기 |
| frontend/scripts/verify-garment-glb.mjs | Three.js로 독립 재로딩/삼각형/법선 검사 |
| frontend/playwright.config.ts, frontend/scripts/prepare-test-garments.mjs, .env.example | 검증 Python 실행 경로 선택 및 no-access-log |
| AGENTS.md, PROJECT_PLAN.md, README.md, docs/PLAN.md, docs/TASKS.md | 현재 허용 범위·구현·실행 안내 |
| docs/API.md, docs/ARCHITECTURE.md, docs/SETUP.md, docs/DECISIONS.md | API·스키마·큐·마이그레이션·결정 기록 |
| docs/RECONSTRUCTION_POLICY.md, docs/PHASE4_DESIGN.md | 현재 A/B 정책·실제 엔진·후속 운영 경계 |
| AI_LICENSE_AUDIT.md, PRIVACY_DESIGN.md, PLAY_STORE_CHECKLIST.md, TECHNICAL_RISKS.md | 자산/모델·데이터·출시·기술 한계 갱신 |
| docs/VERIFICATION_PHASE4.md | 산출물·검사·변경/미구현 보고 |

사용자 기본 DB에는 마이그레이션을 적용하지 않았다. 기존 DB는 API/워커 시작 전 Alembic 업그레이드가 필요하며 버전 없이 create_all로 만든 경우 SETUP의 초기 stamp 검토 절차를 따른다. 검증에는 별도 phase4-e2e.db/phase4-migrationcheck.db를 사용했다.
검증용 API와 워커는 종료했다. 현재 PC에서 재실행할 때는 기존 3.10 .venv 대신 검증에 사용한 .venv-policy/Scripts/python.exe를 선택할 수 있다. API와 생성 워커는 같은 DATABASE_URL을 지정한 별도 터미널에서 실행해야 한다. 저장소의 일반 설치 경로는 SETUP의 Python 3.12 .venv 절차를 따른다.
