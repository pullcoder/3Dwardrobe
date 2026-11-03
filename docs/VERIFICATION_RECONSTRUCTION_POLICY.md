# A/B 복원 정책 변경 검증

작업 브랜치: feature/reconstruction-rights-policy. 커밋·푸시·공개 배포는 하지 않았다.

## 적용 범위

현재 의류 3D 생성은 미구현이다. 3단계 의류 등록에 8개 정책 필드, A 기본, 비공개 고정, 기본 원본 임시 보관, 증빙 참조 접수를 추가했다. 클라이언트의 B 전환·승인·공개 상태 위조는 거절한다. 참조 접수는 pending으로만 바뀌며 승인이나 문서 검증이 아니다.
4단계 A의 독립 메시/재질·보호 그래픽 복제 방지 및 추정치 표시, B의 세 권한 증빙 승인 절차, 5단계 공통 피팅 계약은 설계 문서에 반영했다. 이번에 실제 생성 엔진이나 새 모델/라이브러리를 도입하지 않았다.

## 결과

| 검사 | 결과 |
|---|---|
| backend ruff check . | 통과 |
| backend ruff format --check . | 29개 파일 통과 |
| backend pytest | 32개 통과 |
| SQLite 기존 행/사진 보존 및 Alembic upgrade → downgrade → upgrade | pytest에서 통과 |
| PostgreSQL alembic upgrade head --sql | SQL 생성 통과, 실제 접속은 미검증 |
| frontend npm run lint | 통과 |
| frontend npm run typecheck | 통과 |
| frontend npm run build | 통과, 기존 마네킹 청크 500KB 초과 경고 |
| frontend npm test | 8개 통과 |
| npx playwright test e2e/reconstruction-policy.spec.ts | 데스크톱·모바일 2개 통과 |
| npm run test:e2e | 실패: pretest:e2e의 fixture 준비에서 ModuleNotFoundError: No module named 'PIL' |

서버 검증은 기존 Python 3.10 `.venv`를 변경하지 않고 Python 3.12.10 `.venv-policy`에 기존 requirements.txt의 기본 의존성을 설치해 수행했다. 새 환경은 로컬 Git 제외이며 커밋 대상이 아니다. Node는 앞서 설치된 26.13.0/npm 11.20.0을 사용했다. 요구사항 lock 전체 AI 환경에서 재검증한 결과가 아니다. FastAPI TestClient의 httpx 사용에 대한 종속성 deprecation 경고가 있다.
브라우저 검증은 별도 SQLite policy-verification.db와 API를 사용했다. 실제 CLIP/SAM/OCR 가중치를 실행하지 않았고, A/B 3D 생성·보호 그래픽 차단 정확도도 검증한 것이 아니다. 전체 E2E 통과로 보고하지 않는다.

서버 테스트는 임시 원본/누끼 비보관, 명시 보관 시 기존 Asset CRUD/소유권/삭제, B·승인·공개·모델 경로 위조 차단, 참조 접수 인증·소유권·중복·revision 충돌·A 유지, 기존 저장 동의/사진 마이그레이션 보존을 확인했다.
브라우저는 기본 원본 비보관·직접 촬영 선택에도 권한 미확인, 등록→재로그인→사진 없는 의류 표시→참조 접수→pending/A 유지→B 비활성/위조 거절→테스트 계정 삭제를 확인했다.

## 변경 파일과 이유

| 파일 | 이유 |
|---|---|
| backend/app/models.py | 의류 복원 정책 8개 컬럼 |
| backend/app/schemas/garments.py | 출처·원본 보관·A만 입력 허용, 서버 관리 필드 위조 거절 |
| backend/app/services/reconstruction.py | 증빙 참조 접수와 revision 충돌 처리 |
| backend/app/api/v1/garments.py | 정책 응답, 임시 이미지 비보관, 본인 검토 요청 API |
| backend/migrations/versions/b34a9c12d701_reconstruction_policy.py | 기존 사진/동의를 보존하는 스키마 변경 |
| backend/tests/test_garments.py | 정책·접근 권한·위조·보관·마이그레이션 회귀 검증 |
| frontend/src/features/garments/types.ts | 공통 정책 타입·기본값·상태 한글 표시 |
| frontend/src/types/domain.ts | 초안/서버 의류 정책과 사진 없는 의류 타입 |
| frontend/src/api/garments.ts | 정책 전송/복원, 사진 없는 서버 의류 로딩, 검토 요청 |
| frontend/src/routes/UploadPage.tsx | 출처·권리 안내·A 기본·B 비활성·정보/사진 저장 동의 분리 |
| frontend/src/features/garments/GarmentDetail.tsx | 모드/권한/보관 표시, 증빙 참조 접수와 B 차단 안내 |
| frontend/src/components/PhotoPicker.tsx | 사진 비보관 의류의 미리보기 대체 표시 |
| frontend/src/routes/ClosetPage.tsx | 사진 비보관 카드 배지 |
| frontend/e2e/garments.spec.ts | 기존 원본 보관 시나리오의 분리된 동의 반영 |
| frontend/e2e/reconstruction-policy.spec.ts | 실제 브라우저 정책 흐름과 우회 차단 검증 |
| docs/RECONSTRUCTION_POLICY.md | A/B 정책·세 권한 증빙 승인·4/5단계 계약 설계 |
| docs/API.md | 입력·응답·보관 정책·검토 요청 명세 |
| docs/ARCHITECTURE.md | 변경 스키마·기존 데이터 처리·미구현 경계 |
| docs/SETUP.md | 기존 DB 마이그레이션 안내 |
| docs/DECISIONS.md | 사용자 요청에 따른 정책 변경 결정 |
| docs/PLAN.md | 현재 단계 및 정책 기준 |
| docs/TASKS.md | 정책 변경과 다음 단계 범위 |
| PROJECT_PLAN.md | 3단계 메타데이터·4단계 A 우선·5단계 공통 피팅 |
| PRIVACY_DESIGN.md | 기본 임시/별도 보관 동의와 권한 분리 |
| docs/VERIFICATION_RECONSTRUCTION_POLICY.md | 변경 및 검증 결과와 제한 기록 |

## 남은 작업

기존 데이터가 있는 DB는 API 시작 전에 Alembic upgrade head를 적용해야 한다. 버전 없이 초기 create_all로 만든 DB는 초기 revision 스키마 비교 후 stamp한다. 사용자 DB에는 이번 작업 중 마이그레이션을 실행하지 않았다.
권리 증빙 원문 제출·담당자 진위/세 권한 검증·승인/거절·철회/만료·관리자 감사, 외부 권리자 공개 신고/삭제 운영, 실제 A/B 3D 생성과 피팅은 후속 작업이다. 다음 단계 지시를 기다린다.
