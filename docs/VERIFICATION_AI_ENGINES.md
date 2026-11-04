# AI 생성 엔진 도입 검증 보고

2026-11-04 / 작업 브랜치 `feature/ai-generation-adapters`. 전체 모델 도입 완료가 아니라 **독립 어댑터·통합 경계 구현 및 실행 불가 조건 검증**이다. 실제 추론 성공으로 보고하지 않는다.

## 설치·실행 환경·라이선스

| 엔진 | 설치/추론 | 현재 환경과 판정 |
|---|---|---|
| 기존 템플릿 | 기존 설치, 실제 CPU 생성 | Windows / Python 3.12 / 기존 패널·바지 메시·GLB 유지 |
| TripoSR | 미설치 / 미실행 | GT 1030 2GB, CPU PyTorch 2.15.0+cpu. 기본 약 6GB GPU 실행 예산 부족. 본체/가중치 MIT는 확인했으나 고정 CUDA 환경·전이 종속성·가중치 해시 감사 미완료로 비활성화 |
| TRELLIS.2 | 미설치 / 미실행 | 공식 Linux/NVIDIA 24GB+ 미충족. 본체/가중치 MIT와 별개로 nvdiffrast v0.4.0/nvdiffrec의 NVIDIA 외 비상업 조건 확인. 상용 경로 차단 |

원문·URL·SHA-256 7건은 `docs/licenses/generation-engines/`에 보존했다. 미확인 가중치나 GPU 패키지는 설치하지 않았고 기존 CPU 환경을 바꾸지 않았다. 연구 재현 고지만으로 본체 MIT를 비상업으로 단정하지 않는다. [상세 라이선스 검토](../AI_LICENSE_AUDIT.md), [기술 상태와 잔여 조건](AI_GENERATION_ENGINES.md).

## 실제 산출물·품질 비교

동일 입력 해시별로 3개 엔진의 결과 행을 기록했다. 기본 입력은 합성 누끼이며 **실사진 기반 AI 품질 비교는 미수행**이다. 사용자의 실제 의류 사진을 테스트에 재사용하지 않았다.

| 합성 입력 | 생성 GLB (저장소 루트 기준) | CPU 생성시간 | 크기 | 삼각형 | 독립 Three.js 재로딩 |
|---|---|---:|---:|---:|---|
| 티셔츠 | `backend/storage/engine-comparison/tshirt-template.glb` | 0.203초 | 229,980 bytes | 10,048 | 통과 |
| 와이드 팬츠 | `backend/storage/engine-comparison/wide-pants-template.glb` | 0.489초 | 886,204 bytes | 38,784 | 통과 |

측정은 이 실행의 단일 샘플이며 성능 분포가 아니다. CPU 생성이므로 GPU 메모리는 미사용/null이다. 두 템플릿에서 퇴화면·비다양체 0, 경계 루프 4/3을 검사했다. 원본 실루엣·형태 정확도의 정량 점수는 측정하지 않았다. 일반 단색 텍스처 정책이다. 전역 자기 교차·물리적인 착용감은 미검증이다.

두 AI 엔진의 실루엣/정확도/텍스처/메시 오류/생성시간/VRAM/GLB 크기/착용 결과는 모두 미측정이다. AI GLB 경로는 없으며 템플릿 GLB를 AI 결과로 보고하지 않는다. 상세 데이터는 `backend/storage/engine-comparison/results.json`, 독립 재로딩은 `three-reload.json`. 사용자 누끼를 사용하는 재현 명령은 상태 문서에 있다.

## 마네킹·권리·기존 기능

- 기존 실제 상의·바지·겉옷 GLB를 마네킹에 장착하고 부위 조정·3겹 레이어·저장/재조회·권리 철회·캐시·모바일 터치를 브라우저 테스트로 확인했다. 티셔츠/바지 품질 시나리오도 기존 템플릿을 확인했다. 정밀 피팅·물리 시뮬레이션 성공이라는 뜻은 아니다.
- AI 메시에 템플릿 계약 메타데이터를 붙여도 서버 피팅 자원 API와 클라이언트 변형에서 차단하는 테스트를 통과했다. 목/팔/허리/다리 공간·두께·신체 충돌을 검증했다고 표시하지 않는다. 명시적 템플릿 재생성 대체 경로만 제공한다.
- A 실루엣의 원본 RGB 제거, 미분할 이미지 거절, B 권리 재검사 경계 유지, 미지원 엔진 요청 시 기존 GLB/작업 보존, 모델 자동 다운로드 미발생을 검증했다.
- 기존 1~7단계 소스와 경로를 삭제하지 않았다. 실제 확인 범위는 기존 저장소의 자동화 시나리오이며 모든 사용자 데이터/운영 환경을 망라하는 보증은 아니다. 새 단계 구현이나 공개 배포는 하지 않았다.

## 실행한 검사

- backend: ruff check / ruff format --check 통과, 전체 pytest **109개 통과**.
- frontend: lint / typecheck / build 통과, Vitest **14개 통과**. build의 기존 대형 청크 경고는 남아 있다.
- Playwright: 초기에는 테스트 브라우저가 없어 시작 실패. 공식 Chromium 설치 후 전체 실행에서 **28개 통과**, 새 엔진 옵션 검증 2개가 Playwright `toBeDisabled` 판정 때문에 실패했다. DOM에는 disabled가 있었으며 검증을 실제 JS disabled 속성으로 수정했다. 수정 후 generation.spec의 데스크톱/모바일 **2개 재실행 통과**. 전체 30개를 한 번의 최종 실행에서 모두 통과한 것으로 표시하지 않는다. 실패 실행에서 남은 전용 테스트 계정 2개는 테스트 암호를 확인한 후 정리했다.
- `compare_generation_engines.py`, `verify-engine-comparison.mjs` 통과. 프론트 5173/API health 8000 모두 HTTP 200. 기존 API·생성 워커를 새 코드로 재실행했으며 계속 실행 중이다.
- git diff --check 통과. 커밋/푸시/배포하지 않았다. 사진·가중치·DB·검증 GLB·브라우저 산출물은 Git 제외다.

## 수정 파일과 이유

| 파일 | 이유 |
|---|---|
| `.gitignore` | 향후 격리 엔진 가중치/설정 디렉터리 커밋 방지 |
| `backend/app/ai/generation_adapters.py` | 두 공식 Python API의 독립·비활성 어댑터 |
| `backend/app/ai/generation_input.py` | 누끼 검증·실루엣 보존·A 세부 픽셀 제거 |
| `backend/app/ai/generated_mesh.py` | 별도 GLB 재파싱·면/UV/재질/이미지/토폴로지 검사 |
| `backend/app/services/generation_engines.py` | 하드웨어/감사 가용성, 사용 불가 사유, 피팅 차단 |
| `backend/app/services/ai_generation.py` | 워커 전용 전처리/어댑터/후처리 경계·AI 메타데이터 |
| `backend/app/services/generation.py` | 큐 스냅샷 엔진 분리·권한 재검사·기존 경로 유지 |
| `backend/app/api/v1/generation.py` | 호환되는 선택 engine 요청 필드 |
| `backend/app/services/garment_mesh.py` | 기존 결과를 template/procedural로 명시 |
| `backend/app/services/fittings.py` | 검증되지 않은 AI 착용 차단 |
| `backend/scripts/compare_generation_engines.py` | 공통 입력·실측 baseline·미실행 AI 기록 |
| `backend/tests/test_generation_engines.py` | 환경/권리/기존 모델 보존/전처리/32비트 GLB/피팅 경계 회귀 |
| `frontend/src/api/garments.ts`, `frontend/src/features/garments/types.ts` | 엔진 요청/가용성 응답 타입 |
| `frontend/src/features/garments/GenerationPanel.tsx` | 엔진 선택·사유·후처리·피팅 보류 안내 |
| `frontend/src/features/fitting/fitting.ts`, `fittingAssets.ts`, `fitting.test.ts` | AI 메시의 클라이언트 자동 착용 차단·검증 |
| `frontend/e2e/generation.spec.ts` | 실제 UI 옵션 비활성/사유와 기존 생성 흐름 검사 |
| `frontend/scripts/verify-engine-comparison.mjs` | 독립 Three.js 로더 재검증 |
| `AI_LICENSE_AUDIT.md`, `backend/THIRD_PARTY_NOTICES.md`, `docs/licenses/generation-engines/*` | 원문 근거·고지·도입 보류 기록 |
| `TECHNICAL_RISKS.md`, `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/SETUP.md`, `docs/DECISIONS.md` | 변경 계약·실제 요건·미해결 조건 |
| `docs/AI_GENERATION_ENGINES.md`, 이 문서 | 재현·검증 결과·수정 목록·한계 |

## 해결하지 못한 문제

실제 AI 설치/추론·독립 CUDA 워커 배포·전체 전이 종속성 및 가중치 고정 감사·TRELLIS 상업 허용 경로·실사진 비교·착용 구조 변환기·장시간 GPU lease/취소·원본 실루엣 정량 평가·자동 메시 복구는 미완료다. 적합한 환경과 권리/라이선스 조건이 확보되어야 다음 검증을 진행할 수 있다.
