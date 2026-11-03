# 5단계 구현·검증 보고

## 구현

개인화 마네킹과 실제 GLB를 같은 React Three Fiber 씬에서 표시한다. TOP/BOTTOM/OUTERWEAR 독립 장착·교체·제거·숨김, 체형 수정, 부위별 조절, 회전·확대·시점 복원, 피팅 저장 및 코디 목록·복원·삭제를 구현했다. 삭제·재생성·권한 철회된 의류는 해당 슬롯만 사용 불가로 반환한다. 소유권은 서버에서 검증한다. 최소 체형 7개 수치 저장에는 별도 동의가 필요하다.

## 방식·라이선스·한계

기존 직접 제작한 A모드 실제 입체 GLB를 사용한다. Three.js 정점 변형으로 어깨·가슴·허리·골반·소매·바지 길이를 각각 조절하고 신체 둘레와 의류 단면을 구분한다. 미터/Y 상방/Z 정면을 유지한다. 알려진 부위 계약이 없는 모델은 호환 오류로 표시한다. 신체 타원체·팔다리 캡슐과 의류 Raycaster 검사를 사용하며 겉옷 소매는 같은 쪽 소매 축을 기준으로 보정한다. 보정량은 제한된다.

시각적 근사 피팅이다. 실제 원단·압력·착용감·모든 삼각형 교차를 계산하지 않는다. 남은 관통을 표시한다. A/B 인터페이스와 서버 권리 검증은 공통이지만 실제 고정밀 B 생성 엔진은 계속 비활성화되어 있다. B 계약 테스트는 실제 B 생성 검증이 아니다. 기존 Three.js/R3F 및 직접 작성한 자산을 재사용하며 새 라이브러리·가중치·외부 자산은 추가하지 않았다. 라이선스는 AI_LICENSE_AUDIT.md에 기록했다.

## 검사 결과

- 백엔드 ruff check/format 통과, pytest 61개 통과.
- 프론트엔드 lint/typecheck/build 통과, Vitest 13개 통과. 기존 Three 공용 청크의 500KB 경고는 남아 있다.
- 전체 Playwright 24개 통과. 이후 소매 보정 수정 후 피팅 E2E 데스크톱·모바일 2개, Vitest 및 정적 검사 재통과.
- SQLite Alembic upgrade/check/downgrade/upgrade 통과. PostgreSQL 오프라인 SQL 생성 통과. 실제 PostgreSQL 적용은 미실행.
- git diff --check 통과.

실제 워커가 생성한 티셔츠·니트·바지·재킷을 사용했다. 3벌 동시 장착, 교체·제거, 신체 변경, 치수별 변형, 좌표·범위, 카메라, 코디 CRUD, 타인 접근 차단, 권리 철회, 로딩 실패·재시도, 로그아웃·계정 삭제를 검증했다. 모바일 에뮬레이션의 핀치와 화면 배치를 검증했다. 실제 휴대전화 터치·GPU 성능·장시간 메모리는 미실행이다.

최종 시험의 최초 3벌 표시 시간은 데스크톱 291ms, 모바일 에뮬레이션 265ms이다. 캐시 5개/103,444바이트, CDP JS 힙은 63,883,180/59,525,852바이트이다. GPU 메모리나 정상상태 상한을 의미하지 않는다. 신체 진입 정점은 329→156개, 의류 간 표본 교차는 401→0개였다. 신체 관통은 남아 있으며 표본 0개도 모든 면 무교차를 보장하지 않는다. 산출물은 frontend/test-results/phase5-metrics-*.json 및 phase5-*.png에 있다.

## 변경 파일과 이유

- backend/app/models.py, schemas/fittings.py, services/fittings.py, api/v1/fittings.py, main.py: 비공개 피팅·불변 마네킹·코디와 API.
- backend/migrations/versions/d51e2a7b0903_visual_fitting.py: 테이블·인덱스·삭제 연동.
- backend/app/services/generation.py, garment_mesh.py: B 권리 검증 강화·피팅 부위 계약.
- backend/app/core/database.py: SQL 매개변수 로그 노출 방지.
- backend/tests/test_fittings.py, test_uploads.py: 보안·저장·삭제 검증 및 테스트 DB 격리.
- frontend/src/features/mannequin/fitting.ts, fittingAssets.ts, FittingViewport.tsx, fitting.test.ts: 메시 변형·충돌 보정·GLB 캐시·3D 씬·검증.
- frontend/src/types/fitting.ts, api/fittings.ts: 타입·API.
- frontend/src/routes/StudioPage.tsx, studio.css: 슬롯·체형·조절·반응형 UI.
- frontend/src/features/garments/OutfitLibrary.tsx, routes/ClosetPage.tsx: 코디 목록·복원·삭제.
- frontend/src/stores/SessionContext.tsx, features/garments/AccountPanel.tsx: 세션별 상태·로그아웃 초기화.
- frontend/src/features/mannequin/MannequinViewport.tsx, api/garments.ts: 기존 카메라·오류 경계·요청 재사용.
- frontend/src/App.tsx, routes/Dashboard.tsx: 화면 안내.
- frontend/e2e/fitting.spec.ts, body.spec.ts, foundation.spec.ts: 실제 흐름 검증·화면 선택자 갱신.
- docs/PHASE5_DESIGN.md, API.md, ARCHITECTURE.md, DECISIONS.md, TASKS.md, SETUP.md, CONVENTIONS.md, PLAN.md 및 이 보고서: 설계·API·실행·검증 기록.
- AGENTS.md, README.md, PROJECT_PLAN.md, AI_LICENSE_AUDIT.md, PRIVACY_DESIGN.md, PLAY_STORE_CHECKLIST.md, TECHNICAL_RISKS.md: 범위·보호 정책·한계 갱신.

기존 미커밋 3·4단계 파일은 유지했다. 위 목록은 5단계 변경 기준이다. feature/phase5-visual-fitting에서 작업했으며 커밋·푸시는 하지 않았다.

## 실행·후속 준비

기본 DB의 부분 스키마를 확인하여 storage/stylefit.before-phase5-a3a2a55c.db로 백업하고 누락 열을 추가했다. 기존 데이터 삭제 없이 메타데이터 일치와 Alembic check를 확인한 뒤 d51e2a7b0903으로 정렬했다. 백업은 비공개 로컬 파일이며 Git에 포함하지 않는다.

기본 DB로 API와 별도 생성 워커를 실행했다. 프론트엔드는 http://127.0.0.1:5173/ 이다. Python은 backend/.venv-policy의 3.12 환경을 사용한다. PowerShell에서는 npm.cmd를 사용한다.

6단계에 재사용할 슬롯·코디·카테고리·조절값과 권리 검증 API는 준비됐다. 추천·6단계 기능은 구현하지 않았다. 정밀 물리 시뮬레이션, 임의 B 메시 변형, 완전 충돌 제거, 실제 모바일 성능 검증은 남은 과제다.
