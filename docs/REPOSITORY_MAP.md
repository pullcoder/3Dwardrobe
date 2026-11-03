# 팀 공유용 파일 배치

현재 작업 소스를 기존 ARCHITECTURE/CONVENTIONS/GIT_GUIDE 기준으로 정리한 위치 안내다. 새 제품 기능이나 별도 규칙을 추가하는 문서가 아니다.

| 위치 | 들어가는 파일 |
|---|---|
| 루트 | README, AGENTS, 전체 계획, AI 라이선스/개인정보/출시/기술 위험 문서, 공통 설정 |
| backend/app/api/v1 | 의류·3D 생성·피팅·추천 API 요청 경계 |
| backend/app/models | users/garments/generation/fittings/recommendations/reports 등 도메인별 DB 모델 |
| backend/app/schemas | Pydantic 입력/응답 계약 |
| backend/app/ai | 기존 의류 분류·누끼·OCR 추론 구현 |
| backend/app/services | 권한·추천 규칙·의류 메시/재질/실루엣·GLB 검증 등 서비스 로직 |
| backend/app/workers | 생성 작업 실행/heartbeat, 기존 generation_worker는 호환 실행 진입점 |
| backend/app/local_dev.py | 같은 DB의 API/생성 워커를 함께 실행하는 로컬 진입점 |
| backend/migrations/versions | 순서가 있는 Alembic 스키마 변경 |
| backend/scripts | 모델 준비 및 별도 오프라인 검증 스크립트 |
| backend/tests | API/소유권/삭제/메시/추천/런타임 테스트 |
| frontend/src/api | 인증된 서버 호출 |
| frontend/src/features/body, mannequin | 체형 분석과 기본 마네킹 |
| frontend/src/features/garments | 의류 등록·상세·3D 생성 패널 |
| frontend/src/features/fitting | 피팅 뷰포트·변형·캐시·코디·관련 CSS/단위 테스트 |
| frontend/src/features/recommendations | 취향·추천 결과·피팅 적용 UI |
| frontend/src/routes | 화면 라우트와 화면 조립 |
| frontend/e2e | 실제 브라우저 시나리오 테스트 소스 |
| docs | API·설치·아키텍처·단계 검증/협업 문서 |
| docs/archive | 과거 계획 문서, 현재 범위 기준으로 사용하지 않음 |

기존 import를 보존하기 위해 models/__init__.py, services/garment_ai.py와 generation_worker.py는 호환 경로로 유지한다. 실험용 cloth_quality_experiment.py는 GPL-3.0-or-later 헤더와 별도 라이선스 감사 기록을 유지한다.

## Git에 포함하는 것

소스, 테스트 코드, migration, 패키지 manifest/lock, 재현 스크립트, 공개 가능한 설계·라이선스·실제 검증 기록을 포함한다. 변경 파일을 명시하여 stage하고 기능 브랜치에서 커밋/푸시한 뒤 PR로 검토한다. main 직접 푸시/자동 병합은 하지 않는다.

## 로컬에만 남기는 것

.env와 인증 정보, 사용자 사진/증빙/치수 DB, GLB/렌더 이미지/비교 HTML, AI 가중치, Blender 바이너리/압축파일, node_modules/.venv, 빌드와 테스트 실행 산출물은 Git에 올리지 않는다. backend/storage, frontend/test-results, playwright-report 등은 .gitignore로 제외한다.

검증 보고서의 `backend/storage/...`는 테스트를 실행한 PC의 로컬 전용 경로다. 개인정보/권리 보호를 위해 저장소에는 포함하지 않으며 GitHub에서 열 수 있는 공개 첨부파일이 아니다. 팀원이 결과를 재현하려면 SETUP과 테스트 소스를 사용하고 본인이 적법하게 사용할 수 있는 입력을 준비한다.

## 현재 공유 범위와 검증 상태

기존1~5단계 위에6단계 규칙 추천, GLB 워커 복구, 티셔츠 연결 패널/바지 품질 및 기존 시각적 피팅 보완을 포함한다.7단계 사진 가상 피팅은 취소 상태다. 새 셔츠/재킷/후드 템플릿과 정밀 물리 피팅은 미완료다.

실제 검증은 VERIFICATION_PHASE6/GLB_RECOVERY/PANTS_QUALITY/PANTS_REFINEMENT/GARMENT_PIPELINE 문서에 구분해 기록했다. 최신 기록은 backend99개/Vitest13개 통과, 전체 E2E28/30(2개 첫 로딩 시간 초과), 대기 시간 조정 후 관련6개 재검증 통과다. 전체30개를 다시 통과했다고 표현하지 않는다. 이번 업로드 정리는 제품 코드를 변경하지 않으며 이 실행 기록을 그대로 보존한다.
