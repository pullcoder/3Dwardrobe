# 4단계 GLB 생성 긴급 복구 보고

## 정확한 원인과 기존 구현

사용자 사이트의 FastAPI와 Vite만 실행되고 실제 생성 워커가 빠져 있었다. 서버는 `storage/stylefit-site-preview.db`를 사용했으며 같은 DB에 queued 생성 2건(티셔츠/청바지)이 남아 있었다. API는 정상적으로 202 작업 등록을 반환했지만 작업을 소비할 프로세스가 없어 완료되지 않았다. 이 사이트를 열 때 워커를 함께 실행하지 않은 실행 구성 누락이 원인이다.

버튼/API만 있는 상태는 아니었다. 기존 `services/garment_mesh.py`에는 직접 제작한 9종 파라미터 템플릿, make_meshes, 실제 삼각형/정점/노멀/PBR 색상, 자체 포함 GLB writer와 재검증이 있었다. `services/generation.py`에는 영속 큐·claim/lease·권한/변경 검사·DB binary Asset 저장과 generated_model_path 갱신이 구현되어 있었다. 같은 DB의 실제 워커를 연결하자 기존 대기 티셔츠/바지가 completed로 바뀌었고 각각 539/441 정점의 입체 GLB를 확인했다. 사용자 사진/의류 데이터는 삭제하지 않았다.

## 수정 내용

- `app.local_dev`: 같은 DATABASE_URL/Python으로 API와 GLB 워커를 함께 실행한다. 기존 DB의 Alembic head를 확인하며 기존 데이터를 자동 변경하지 않는다. `--initialize-empty`는 테이블 없는 새 DB만 초기화한다. 자식 장애 시 함께 종료하고 Windows에서는 venv의 하위 Python 프로세스도 정리한다.
- 실제 워커의 같은 DB heartbeat를 저장하고 생성 상태 응답/화면에 워커 응답 없음 안내를 추가했다. 202는 생성 완료를 뜻하지 않으며 실제 완료 전에는 대기/처리 중으로 표시한다.
- 실제 메시/GLB 내보내기·검증·모델 저장·DB 갱신/커밋 실패 단계와 예외 유형을 기록한다. 원문 예외, SQL 매개변수, 사진, 치수, DB 주소를 로그에 넣지 않는다. 기존 에러 코드는 유지한다.
- 빈 GLB 씬을 검증에서 거부한다. 기존 실제 메시 생성 알고리즘과 A/B 권한/소유권·취소/삭제 경계는 유지했다.
- 마이그레이션 f71a4c9d1105: generation_workers 및 GenerationJob의 failure_stage/exception_type. 현재 사용자 미리보기 DB는 별도 백업 후 적용했다. 원본 `storage/stylefit.db`는 변경하지 않았다.
- 브라우저 테스트에서 숨겨진 테스트 전용 워커 실행을 제거했다. 실제 사용자용 통합 명령이 API와 워커를 시작하도록 변경해 실행 누락 문제가 테스트에 가려지지 않게 했다.

## 실제 생성한 GLB 파일

아래 파일은 이번 브라우저 시나리오에서 API로 실제 생성·다운로드한 binary를 재파싱한 검증용 사본이다. canonical 저장은 여전히 인증된 DB garment_assets이며 공개 static 폴더로 옮기지 않았다. generated_model_path는 `private:garment/{garment_id}/{asset_id}.glb` 참조다. 모델 다운로드/피팅 자원 API에서 소유권과 현재 권리를 검사한다. 파일·스크린샷·DB/백업은 Git 제외 경로이며 커밋하지 않았다.

| 의류 | 실제 경로 | 바이트 | 메시 | 정점 | 삼각형 |
|---|---|---:|---:|---:|---:|
| 티셔츠 | `backend/storage/glb-recovery/tshirt.glb` | 21,368 | 3 | 539 | 768 |
| 청바지 | `backend/storage/glb-recovery/jeans.glb` | 17,960 | 3 | 441 | 576 |
| 재킷 | `backend/storage/glb-recovery/jacket.glb` | 21,384 | 3 | 539 | 768 |

티셔츠/재킷 부위: body, sleeve_left, sleeve_right. 청바지 부위: waist, leg_left, leg_right. 티셔츠 범위는 약 0.792×0.68×0.24m이며 깊이가 있는 실제 삼각형 표면이다. 이미지 평면이나 빈 GLB가 아니다. 노멀·재질 연결·인덱스·유한 좌표·3차원 범위·GLB 헤더/길이/바이너리를 검사했다. Three.js GLTFLoader로 로드해 정면/측면/후면·회전·확대/축소를 확인했다.

## 실제 테스트 결과

| 검사 | 결과 |
|---|---|
| backend ruff check / format --check | 통과 |
| backend pytest | 85 통과 |
| frontend ESLint / TypeScript / production build | 통과 |
| frontend Vitest | 13 통과 |
| Playwright 전체 | 데스크톱/모바일 26 통과, 5.8분 |
| 실제 통합 명령 | 격리 DB에서 API+워커 자동 실행 → 티셔츠 생성/다운로드 통과 |
| 단계별 실패 | 메시·내보내기·검증·저장·DB 경로 갱신·커밋 오류 주입, failed 기록/모델 비공개/민감 문구 비노출 통과 |
| 색상·크기 | red/blue 재질 차이, 60/85cm 총장의 실제 메시 범위 차이 확인 |
| 소유권·철회·삭제 | 타인 모델/Asset 접근 차단, 철회/삭제/늦은 작업 게시 방지 기존 테스트 통과 |
| 마이그레이션 | 별도 SQLite upgrade/check/downgrade/upgrade/check 통과 |

브라우저에서는 실제 티셔츠 GLB 1벌 장착 후 2벌·3벌로 확장하고, 상의 교체·하의/겉옷 유지·제거·숨김·체형 갱신·코디 저장/복원·권한 철회에 따른 접근 차단까지 검사했다. 기하 bounds와 Canvas 픽셀 변화, mounted_count 1→2→3을 함께 확인했다. 기존 1~6단계 MediaPipe/의류 AI·OCR·옷장·추천 흐름도 통과했다. 최종 티셔츠 단독 장착 후 Canvas 변화/캡처를 추가해 피팅 시나리오 데스크톱·모바일 2개도 재통과했다(50.8초).

티셔츠 단독 착용 — 로컬 전용 `backend/storage/glb-recovery/tshirt-on-mannequin-desktop.png`, 3벌 장착 확인 — 로컬 전용 `backend/storage/glb-recovery/fitting-desktop.png`, 모바일 장착 확인 — 로컬 전용 `backend/storage/glb-recovery/fitting-mobile.png`. 스크린샷을 직접 확인했으며 실제 입체 의류가 렌더링된다. 현재 모델은 각진 일반 템플릿이고 일부 관통이 남는다.

## 변경 파일 (이번 복구 범위)

기존 비커밋 1~6단계/파일 정리와 별도로 이번에 수정한 파일은 다음과 같다.

- backend/app/local_dev.py
- backend/app/workers/generation.py
- backend/app/services/generation.py
- backend/app/services/generation_runtime.py
- backend/app/services/garment_mesh.py
- backend/app/models/generation.py
- backend/app/models/__init__.py
- backend/migrations/versions/f71a4c9d1105_generation_runtime.py
- backend/tests/test_generation_runtime.py
- backend/tests/test_local_dev.py
- frontend/src/features/garments/GenerationPanel.tsx
- frontend/src/features/garments/types.ts
- frontend/playwright.config.ts
- frontend/e2e/generation.spec.ts
- frontend/e2e/fitting.spec.ts
- frontend/e2e/recommendations.spec.ts
- README.md
- docs/SETUP.md
- docs/API.md
- docs/ARCHITECTURE.md
- docs/DECISIONS.md
- docs/TASKS.md
- docs/VERIFICATION_GLB_RECOVERY.md
- AI_LICENSE_AUDIT.md
- PRIVACY_DESIGN.md
- TECHNICAL_RISKS.md

## 한계와 실행

A 모드는 일반 파라미터 의류의 실제 GLB이며 사진 고유 디자인/로고/질감·봉제 구조를 복원하지 않는다. 지원 9종 이외 의류, B 고정밀 생성, 물리 드레이프/정확한 착용감은 미구현이다. 새로운 AI 모델/가중치/외부 API/자산을 도입하지 않았다. PostgreSQL 실접속·실제 Android 기기는 이번에도 미검증이며 기존 3D 공통 청크 용량/Three.Clock 폐기 예정 경고가 남아 있다. heartbeat는 15초 유효 기간 때문에 즉각적인 장애 보장이 아니며 운영 프로세스 관리 시스템을 대체하지 않는다.

backend에서 현재 미리보기 DB를 지정하고 `python -m app.local_dev`를 실행한다. frontend는 `npm run dev`다. [실행 안내](SETUP.md). 이번 작업은 `fix/glb-generation-runtime` 로컬 브랜치이며 원격 푸시/main 통합은 하지 않았다. 7단계 사진 가상 피팅은 취소 상태로 유지했다.

현재 사이트는 API와 실제 생성 워커를 함께 실행하는 상태로 복구했다. 저장된 옷장을 다시 불러오면 생성 완료된 의류를 선택할 수 있다.
