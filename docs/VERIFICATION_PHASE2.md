# 2단계 — 체형 분석·3D 마네킹 구현 보고

검증일: 2026-11-03 / 브랜치: `feature/stylefit-body-mannequin`.
Windows, Node 24.21.0, Python 3.12.10. 0·1단계의 의류 업로드·옷장 초안·FastAPI를 유지했다.

## 구현된 기능

- 사진/수동 체형을 별도 프로필로 편집·탭 저장·전환·삭제.
- 실제 MediaPipe Pose Full v1으로 어깨·팔꿈치·손목·골반·무릎·발목 등 33개 관절 추출.
- 단일 인물·가시성·화면 경계·머리/발 여백 검사와 인식 실패 안내·취소·재시도.
- 키 기준 상대 길이 추정, 사진 추정/직접 입력/미입력 기본 비율 구분.
- 키 변경 시 추정 길이 재계산, 사용자가 직접 수정한 값 유지. 둘레는 자동 추정하지 않음.
- R3F/Three.js 중립 마네킹과 실제 Canvas 렌더링. 시점·드래그 회전·확대/축소·초기화.
- 치수 변경 시 실제 메시 갱신. 선택 체형을 스튜디오에 전달하되 의류 피팅은 하지 않음.
- 성공 후 원본 제거 기본값, 수동 사진 삭제, 분석 Worker 종료와 Bitmap/객체 URL 해제.
- 선택적 기기 보관함: 두 체형의 치수·출처·요약 비율을 암호화 저장/복원/삭제.
- 모바일은 마네킹 상단·편집 패널 하단 배치. 기존 8개 화면 이동과 의류 흐름 유지.

## MediaPipe 분석 방식

1. 사용자 동의와 키 입력 후 사진을 브라우저에서 디코딩한다. 파일 제한은 기존 10 MiB·20MP다.
2. 최대 변 1600px의 ImageBitmap을 전용 classic Worker에 전달한다.
3. SDK 0.10.35·Full float16 v1 가중치·WASM을 동일 출처에서 로드한다. CPU/IMAGE, 최대 2인 탐지로 다중 인물을 거절한다.
4. x/y를 이미지 너비·높이로 각각 픽셀 환산한다. 어깨 관절 간 거리, 팔 2구간, 다리 2구간의 좌우 평균을 계산한다.
5. 코와 어깨 중심의 간격에서 정수리 높이를 근사하고 발끝까지의 영상 높이를 키 기준 길이로 사용한다.
6. 실제 정수리·둘레·의복 아래 피부 표면을 관찰한 측정이 아니다. 원근·포즈·가림에 따라 오차가 있다.

가중치 SHA-256 및 공식 상업 라이선스 근거는 [AI_LICENSE_AUDIT.md](../AI_LICENSE_AUDIT.md)에 있다.
SDK/모델은 수정하지 않았다. 별도 Face Landmarker 모델은 로드하지 않는다.
Worker 응답 CSP는 외부 연결을 차단한다. 실제 분석 브라우저 테스트에서 외부 HTTP 요청과 POST 요청이 0건이었다.

## 3D 생성 방식

- 인체 메시 생성 AI 대신 직접 작성한 파라미터 기하를 사용한다.
- torso는 가슴·허리·엉덩이 둘레로부터 타원 단면을 만들고 링 사이에 삼각형을 연결한다.
- 단면 깊이/너비 0.72는 관측되지 않은 가정이다. 빈 치수는 키에 비례하는 기본값을 쓴다.
- 머리는 중립 타원체, 목·팔·다리는 capsule, 손·발·골반은 타원체다. 사진 텍스처를 사용하지 않는다.
- 부위별 mesh name·`body_part`, meter/Y-up/Z-front, `garment_anchors`를 제공한다.
- OrbitControls로 회전·줌, 정면/측면/후면 버튼을 제공한다. 프레임은 변화 시만 렌더링한다.
- FaceLandmarkProvider와 실제 FaceLandmarker 주입 어댑터를 마련했다. 실제 얼굴 특징점 추론/유사 얼굴 복원은 미구현이다.

## 저장·권한 경계

- 기본 저장은 탭 메모리. 선택 저장만 해당 origin의 localStorage에 암호문으로 남는다.
- PBKDF2-SHA256 310,000회, salt 16바이트, AES-256-GCM, 매 저장 새 12바이트 IV.
- 암호·원본 사진·개별 관절 좌표는 저장하지 않는다. 허용 필드만 직렬화한다.
- 다른 이름/암호로 복원하거나 기존 보관함을 덮어쓰지 못하도록 검증한다. 암호 복구·기기 간 동기화는 없다.
- 서버 로그인/계정 인증·인가·계정별 DB 저장은 구현하지 않았다. 브라우저 보관함을 서버 사용자 권한 분리로 표시하지 않는다.
- 세션 초기화와 기기 저장 삭제는 별도다. 서버 신체 사진 저장·분석 API는 추가하지 않았다.

## 실제 검사 결과

| 검사 | 결과·범위 |
|---|---|
| ESLint/React Hooks/접근성 규칙 | 통과 |
| TypeScript strict | 통과 |
| Vite build | 통과. 3D 청크 크기 경고 있음 |
| Vitest | 8개 통과: 출처/키 갱신/픽셀 비율/품질 실패/치수 범위/실제 geometry 크기/암호화 격리/변조 |
| Playwright | 16개 통과: 데스크톱 Chromium 8개 + 모바일 Chromium 에뮬레이션 8개 |
| 기존 backend ruff·format·pytest | 통과, API 테스트 15개 유지 |
| npm audit --omit=dev | 운영 의존성 취약점 0건 (검사 시점) |

브라우저 테스트는 SDK 추론이나 Canvas를 모킹하지 않는다.
MediaPipe 공식 `male_full_height_hands.jpg` 테스트 사진에서 실제 특징점이 추출되었고,
빈 사진과 발목 아래가 잘린 파생 사진의 실패 안내를 확인했다.
시점·줌·드래그·편집 전후 Canvas 이미지가 달라지는지 비교했다.
탭 저장→스튜디오 전달, 새로고침→암호 복원, 잘못된 암호 거절, 삭제도 확인했다.
테스트 이미지는 Git 제외 폴더에서만 사용하며 앱 UI나 배포 산출물에는 포함하지 않는다.

## 기술적 한계와 미실행 검사

- 실제 Android/iOS 기기와 Safari/Firefox는 검사하지 않았다. 모바일 테스트는 Chromium 에뮬레이션이다.
- 터치 핀치 실기기 동작·스크린리더 전문 감사·실제 GPU/메모리 성능 벤치마크는 하지 않았다.
- 전신 사진 1개와 실패 사례를 확인했으며 다양한 사람/의복/촬영 조건의 치수 정확도 통계는 없다.
- 얼굴 특징점 어댑터는 구조만 제공하며 실제 Face Landmarker 추론·얼굴 복원은 테스트하지 않았다.
- 프로시저 마네킹은 리깅·해부학적 스캔·의류 충돌·물리 시뮬레이션·GLB 의류 착용 결과가 아니다.
- 마네킹 청크 약 945KB(minified), gzip 약 249KB. 지연 로드하지만 큰 청크 경고가 남는다.
- MediaPipe 사전 컴파일 WASM의 전체 내장 고지/provenance는 상업 출시 전 추가 확인 항목이다.
- 기존 개발 도구 minimatch 계열 중간 경고 12건, backend Starlette/httpx 사용 중단 예정 경고 1건이 남는다.
- 신체 관련 서버 API/DB 변경이 없어 새 마이그레이션은 없다. Docker·PostgreSQL 실행 검증을 추가하지 않았다.
- 원본 제거는 앱 참조 해제이며 디스크 원본 삭제·브라우저 메모리 안전 소거를 보장하지 않는다.

## 변경 파일과 목적

| 파일 | 목적 |
|---|---|
| `frontend/src/features/body/types.ts`, `measurements.ts` | 두 체형·출처·비율·품질 검사·키 재계산 |
| `features/body/poseClient.ts`, `public/pose-worker.js` | 실제 기기 내 MediaPipe와 취소·종료 |
| `features/body/PosePlot.tsx`, `body.css` | 관절도와 모바일 3D 상단 편집 UI |
| `features/body/faceAdapter.ts` | 향후 검증된 FaceLandmarker를 주입하는 경계 |
| `features/body/vault.ts`, `BodyVault.tsx` | 암호화 기기 저장·복원·삭제 |
| `features/mannequin/geometry.ts`, `MannequinModel.tsx`, `MannequinViewport.tsx` | 실제 파라미터 메시·부위·카메라 조작 |
| `routes/BodyPage.tsx`, `stores/SessionContext.tsx` | 체형 분석→수정→저장과 독립 상태 |
| `routes/StudioPage.tsx` | 선택한 실제 3D 체형 표시, 의류 피팅 미구현 유지 |
| `routes/Dashboard.tsx`, `SettingsPage.tsx`, `App.tsx` | 현재 기능과 데이터 보관 안내 갱신 |
| `features/body/measurements.test.ts`, `vault.test.ts`, `vitest.config.ts` | 실제 로직·기하·저장 경계 검사 |
| `e2e/body.spec.ts`, `foundation.spec.ts`, `playwright.config.ts` | 새 흐름과 기존 기능 회귀 검사 |
| `scripts/prepare-vision.mjs`, `prepare-test-photo.mjs` | 검증된 가중치와 내부 테스트 사진 재현 |
| `package.json`, `package-lock.json`, `vite.config.ts`, `eslint.config.js`, `.gitignore` | 의존성 고정·모델 준비·Worker CSP·산출물 제외 |
| `public/third-party-notices.txt`, `docs/licenses/` | 도입 라이선스 고지 |
| `AGENTS.md`, `README.md`, `PROJECT_PLAN.md`, `AI_LICENSE_AUDIT.md`, `PRIVACY_DESIGN.md`, `TECHNICAL_RISKS.md` | 2단계 범위·정책·도입·한계 기록 |
| `docs/ARCHITECTURE.md`, `API.md`, `CONVENTIONS.md`, `DECISIONS.md`, `SETUP.md`, `TASKS.md`, `VERIFICATION.md` | 현재 구조·상태·설치·과거 검증 구분 |

## 3단계 준비 상태

의류 분석은 아직 착수하지 않았다. 기존 사진 슬롯·수동 정보·세션 옷장 구조를 유지했으며
다음에는 상업 조건을 확정한 의류 분리/VLM/OCR를 별도 모듈로 연결할 수 있다.
의류 GLB·피팅은 현재 마네킹의 좌표계·부위 이름·기준점을 사용하되 리깅·충돌·변형을 별도로 검증해야 한다.
2단계 종료 후 다음 지시를 기다린다.
