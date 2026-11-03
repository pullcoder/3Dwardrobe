# 4단계 바지 실루엣 품질 개선 검증

검증일: 2026-11-03. 범위는 기존 4단계 바지 생성과 기존 마네킹 장착의 호환성 보완이다. 7단계는 계속 취소 상태이며 다른 개발 단계는 진행하지 않았다. 저장된 실제 체크 와이드 팬츠 앞면/누끼와 기존 GLB를 사용했다. 원본 이용 권한을 임의로 B로 승격하지 않았다.

## 원인과 실제 변경

기존 생성 알고리즘은 실제로 존재했지만 허리와 두 다리를 각각 높이 3개 링의 타원 단면으로 생성했다. 사진 픽셀의 외곽을 사용하지 않았고 `wide`가 지원 핏으로 보존되지 않았으며 체크 정보도 재질에 반영하지 않았다. 피팅 단계도 바지통을 고정된 다리 중심/반경에 맞춰 좁혔다. 따라서 색상만 바뀐 원통형 결과였다. 워커 부재에 따른 생성 장애는 별도 [복구 보고](VERIFICATION_GLB_RECOVERY.md)를 따른다.

새 알고리즘은 새 AI 모델이나 이미지 생성 API를 사용하지 않는 결정적 이미지 처리와 직접 제작 파라메트릭 표면이다.

1. EXIF 방향을 보정한 앞면 누끼의 알파 마스크를 우선 사용한다. 누끼가 없으면 단순한 단색 배경에 한해 배경과의 색상 차이로 전경을 분리한다. 연결 성분과 내부 구멍을 처리하고 복잡한 배경·여러 물체·불분명한 다리 분기는 실패/추정 상태로 안내한다.
2. 높이별 49개 외곽/다리 사이 간격을 대칭 프로필로 추출하고 허리·골반·밑위·허벅지·밑단 비율을 구한다. 유효한 선택 사이즈의 명시적 의류 치수가 있으면 단위·단면·길이를 구분하여 우선한다. 사진만으로 절대 cm를 측정하지 않는다.
3. 허리에서 골반으로 이어지고 밑위 아래에서 두 다리로 분기하는 앞뒤 패널 표면을 생성한다. 가로 25개 표본, 상부 기본 17행과 허리밴드 추가 행, 다리 37행을 사용한다. 허리밴드의 작은 요철·봉제선·일반 주름을 기하구조로 더한다. 실제 봉제 패턴이나 천 시뮬레이션은 아니다.
4. A는 원본 이미지 픽셀/로고를 GLB에 넣지 않는다. 의류 정보의 색상과 `체크` 분류에 따라 직접 생성한 일반 체크 PNG와 UV를 사용한다. 원본 체크 주기·로고·보호되는 그래픽을 복제하지 않는다.
5. B는 서버의 세 권한 모두 verified, 지원 바지, 비공개 저장 앞면이 있을 때만 앞면 투영 근사를 제공한다. 원본 앞면은 작업 메모리에서만 읽으며 job snapshot에 픽셀을 넣지 않는다. 뒤쪽은 자체 일반 패턴으로 추정한다. 고정밀 복원·주머니/지퍼 3D 복원·다중 사진 복원은 구현하지 않았다.
6. 실제 미터/Y-up/Z-front GLB를 내보내고 UV·정점·삼각형·이미지 포함 규칙을 검증한다. 새 `stylefit.pants.v2` 피팅 계약은 외곽과 부위 연결을 유지하고 관측되지 않은 깊이에 신체 여유를 더한다. 기존 상의/겉옷 계약은 유지한다.

## 실제 개선 전후

비공개 원본과 테스트 산출물은 모두 git ignore된 `backend/storage/pants-quality/`에만 보관하고 커밋하지 않는다. 브라우저 검증은 별도 SQLite QA DB/사용자로 진행했다.

- 정면·측면·후면 전후 및 장착 비교 — 로컬 전용 `backend/storage/pants-quality/actual-reference/comparison.html`
- 기존 실제 GLB — 로컬 전용 `backend/storage/pants-quality/before-original-pants.glb`
- 새 실제 A모드 GLB — 로컬 전용 `backend/storage/pants-quality/actual-reference/desktop-pants-after-A.glb`
- 현재 사이트의 원래 체크 팬츠도 preview DB 백업 후 A모드로 실제 재생성했다. 상태 completed, 버전 stylefit-pants-2.0, 권한 변경 없음. 현재 옷장 실제 GLB — 로컬 전용 `backend/storage/pants-quality/live-user-pants-after-A.glb`는 255,764 bytes다. 기존 원본 DB stylefit.db는 수정하지 않았다.
- 새 모델 메타데이터 — 로컬 전용 `backend/storage/pants-quality/actual-reference/desktop-pants-metadata.json`

| 항목 | 개선 전 | 개선 후 |
|---|---:|---:|
| 의미 부위 메시 | 3 | 3 |
| 정점 | 441 | 5,700 |
| 삼각형 | 576 | 10,560 |
| GLB 크기 | 17,976 bytes | 255,748 bytes |
| 사진 외곽 기하 반영 | 없음 | 49행 프로필 |
| 재질 | 단색 | 자체 일반 체크와 허리밴드 |

실제 원본 외곽에서 넓은 밑단과 낮은 밑위가 반영된다. 실측 기장이 없어 기본 102cm를 가정한 예시 수치는 허리 단면 약39.3cm, 골반 단면45.9cm, 밑위53.0cm, 허벅지 단면24.7cm, 밑단 단면23.1cm다. 이는 **기본 기장에 비례 환산한 사진 추정값**이며 실측이 아니다. 깊이18.3cm와 뒷면도 관측값이 아니다. 실제 마네킹에서는 기본 체형과 길이 설정에 따라 근사 변형한다.

## 테스트

- backend `ruff check .`, `ruff format --check .`: 통과.
- backend 전체 pytest: **93개 통과**, 52.48초. 새 바지 테스트 8개 포함.
- frontend lint/typecheck/build: 통과. Vitest **13개 통과**.
- E2E 전체 회귀 **28개 통과**(7.1분). 마지막 골반 여유 보정 후 바지/기존 피팅의 PC·모바일 **4개 추가 통과**(1.5분). 최종 스크린샷을 다시 확인해 앞뒤 골반 노출을 수정한 결과를 보관했다.
- 새 테스트: 알파/단색 배경 외곽, 좁은/넓은 원본의 실제 기하 차이, 명시 치수 우선, 임시 처리 사진 미저장, forged silhouette 배제, A 원본 픽셀 미포함, 자체 PNG/UV 검증, B 자체 소유 합성 테스트 사진의 허용 투영, 타인 접근/권한 철회 차단.
- 실제 원본 A모드: 워커/API→GLB 다운로드→GLTFLoader 재로딩→세 시점→마네킹 장착→모바일 넘침 검사. 기존 GLB는 동일 뷰어의 파일 응답만 교체하여 개선 전 모습을 캡처했고 개선 후 파일은 실제 새 워커 결과다.
- B는 권한을 갖춘 **자체 제작 테스트 이미지**로만 실행했다. 사용자 원본은 A 권한 상태를 그대로 유지한다.
- GPU 사용·학습 모델 품질·실물 착용감·상업 배포 정책 최종 심사는 검증한 항목이 아니다.

## 변경 파일

이번 품질 보완 파일만 열거한다. 이전 단계에서 남아 있던 미커밋 변경은 보존했다.

- 신규: `backend/app/services/pants_silhouette.py`, `pants_mesh.py`, `pants_materials.py`, `backend/tests/test_pants_quality.py`, `frontend/e2e/pants-quality.spec.ts`.
- 수정: `backend/app/services/garment_mesh.py`, `generation.py`, `backend/app/api/v1/garments.py`, `generation.py`.
- 수정: `frontend/src/features/fitting/fitting.ts`, `frontend/src/api/garments.ts`, `frontend/src/features/garments/{GenerationPanel,GarmentDetail}.tsx`, `types.ts`.
- 문서: `AGENTS.md`, `README.md`, `PROJECT_PLAN.md`, `AI_LICENSE_AUDIT.md`, `PRIVACY_DESIGN.md`, `PLAY_STORE_CHECKLIST.md`, `TECHNICAL_RISKS.md`, `docs/{API,ARCHITECTURE,DECISIONS,RECONSTRUCTION_POLICY,SETUP,TASKS,VERIFICATION_PANTS_QUALITY}.md`.

## 개인정보·라이선스·한계

새 라이브러리·모델·가중치·외부 API를 추가하지 않았다. 기존 감사된 Pillow/NumPy 및 Three.js/R3F를 사용한다. 패널 메시·일반 체크는 프로젝트에서 직접 제작했다. 원본/산출물 비공개, 소유권 검사, 삭제, 권한 철회, 모델 무효화와 저장 동의를 유지한다. 임시 실루엣 분석은 사진을 영구 저장하지 않으며 숫자 프로필만 저장한다. 외부 서버로 사진을 전송하거나 학습에 사용하지 않는다.

단일 사진의 원근·걸이/주름·비대칭 때문에 외곽 추정은 오차가 있다. 수평 대칭화와 밑위 검출 제한(높이18~52%)을 적용한다. 기장이 없으면 실제 길이는 알 수 없다. 복잡한 배경의 정밀 의류 분할은 보장하지 않는다. 사진의 뒷면 파일이 있어도 이번 바지 엔진은 **앞면만 사용**하며 뒤와 깊이·일반 주름은 추정한다. B도 한 장의 앞면 투영 근사로, 보호되는 디테일의 정밀 입체 복원을 보장하지 않는다. 개별 앞뒤 패널 경계는 좌표상 연결되지만 봉제/물리용 watertight 자산은 아니다. 마네킹 피팅은 시각적 근사이며 모든 삼각형 교차를 해결하는 물리 시뮬레이션이 아니다.

빌드의 기존 큰 3D 청크 경고, Three.Clock deprecated 경고와 Windows E2E의 간헐적 연결 종료 로그는 별도로 남아 있다. 테스트 실패를 숨기거나 skip하지 않았다.

후속 요청: [2.1 원단 표면·드레이프·가장자리 품질 추가 보완](VERIFICATION_PANTS_REFINEMENT.md). 앞의2.0 수치는 당시 검증 기록이며 최신 결과는 후속 보고서를 따른다.
