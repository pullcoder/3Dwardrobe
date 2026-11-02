# 0·1단계 검증 보고

이 문서는 1단계 종료 시점 기록이다. 현재 2단계 상태는 [VERIFICATION_PHASE2.md](VERIFICATION_PHASE2.md)를 따른다.

검증일: 2026-11-03 / 브랜치: `feature/stylefit-foundation`.
로컬 Windows, Node 24.21.0, Python 3.12.10에서 검증했다. 원격 배포·Play 심사는 하지 않았다.

## 구현 결과

- 요청한 루트 문서 5개에 계획·모델 후보 감사·개인정보·Play 정책·기술 한계를 기록했다.
- React/TS/Vite/Tailwind 프론트와 FastAPI, 개발용 PostgreSQL/Redis Compose 구성을 추가했다.
- 대시보드, 체형 분석 준비, 마네킹 편집 준비, 의류 등록, 피팅 준비, 추천 준비, 옷장 초안, 설정 화면을 제공한다.
- 실제 동작: 이미지 선택/제거/미리보기, 수동 치수·의류 정보, 세션 초안 추가/필터/검색/삭제,
  슬롯 선택/해제, 전체 초기화, 사용자 동의 후 로컬 API 이미지 형식 검증.
- 미구현: AI 분석/누끼/OCR/생성/3D/추천, 인증/계정/영구 저장, 실제 신고 접수, Android 패키징.

## 실행한 검사

| 검사 | 결과 |
|---|---|
| backend `ruff check .` | 통과 |
| backend `ruff format --check .` | 통과 |
| backend `pytest -q` | 15개 통과 |
| frontend `npm run lint` | 통과 (ESLint, React Hooks, jsx-a11y) |
| frontend `npm run typecheck` | 통과 |
| frontend `npm run build` | 통과 |
| frontend `npm run test:e2e` | 데스크톱 Chromium 4개 + 모바일 에뮬레이션 Chromium 4개 통과 |
| 화면 캡처 검토 | 대시보드 PC/모바일·의류 등록·스튜디오 캡처 확인, 가로 넘침 검사 통과 |
| `npm audit --omit=dev` | 운영 의존성 취약점 0건 (검사 시점) |
| `npm audit` | 개발 도구에 중간 수준 12건 잔존. 아래 참고 |

## 확인한 흐름과 경계

- 브라우저에서 만든 실제 PNG → 사진 선택 → 명시적 동의 → FastAPI → Pillow 디코딩
  → 실제 가로/세로·보관 안 함 응답 → UI 결과 표시 → 초안 추가 → 검색/분류 → 슬롯 선택 → 삭제.
- 파일 선택만으로 API를 호출하지 않는지 요청 수를 검사했다.
- JPEG/PNG/WebP, 손상·빈 파일, MIME 불일치, 미지원 SVG, 요청 바이트/픽셀 초과, 권리 확인 누락,
  원격 클라이언트·외부 Origin 거절, production 설정 거절을 API 테스트로 확인했다.
- 브라우저에서 실패 파일·API 연결 실패 안내, 미연결 저장 버튼 비활성 상태를 확인했다.
- 치수는 페이지 이동 중 유지되며 전체 초기화/새로고침 후 제거된다. localStorage에 기록하지 않음을 확인했다.
- 이미지 객체 URL은 컴포넌트 제거/교체 시 해제하도록 코드 검토했다.
- 모바일 메뉴, 8개 화면 이동, 정상 흐름 중 브라우저 런타임 오류 없음과 가로 넘침 없음을 검사했다.

## 남아 있는 검증 한계

- 모바일은 Playwright 기기 에뮬레이션이다. 실제 Android/iOS, Safari/Firefox 검증은 하지 않았다.
- Docker 실행 파일이 없어 PostgreSQL/Redis 컨테이너를 실행하지 않았다. 현재 API도 DB를 사용하지 않는다.
- GPU·MediaPipe·생성 모델·OCR 성능 실험은 하지 않았다. 모델 후보의 라이선스 검토가 도입 승인이라는 의미는 아니다.
- 서버 원본 저장·외부 AI 전송은 구현하지 않았다. 사진을 메모리에서 사용 후 참조를 해제하며 메모리 안전 소거를 보장하지 않는다.
- 자동화된 접근성 린트와 키보드 개선은 했으나 전문 접근성 감사·스크린리더 실기기 검증은 하지 않았다.
- 법령 본문 자동 추출에 한계가 있어 개별 법적 근거와 생체정보 분류는 미확인이다. 상표명 사용 가능성도 미확인이다.

## 의존성 경고

`npm audit`의 12건은 ESLint/TypeScript ESLint/접근성 플러그인의 개발 의존성 경로에서
`minimatch`의 glob 처리 서비스 거부 취약점으로 전파된 경고다.
[공개 보안 권고](https://github.com/advisories/GHSA-g3hv-75wg-m249)
운영 번들 의존성 검사에서는 0건이었다. 호환성을 무시하는 강제 다운그레이드나 major override는 하지 않았다.
개발 도구 호환 패치가 제공되면 업데이트 후 린트를 재검증해야 한다.
pytest는 설치된 Starlette의 httpx TestClient 사용 중단 예정 경고 1건을 출력하지만 테스트는 통과한다.

## 파일과 이유

| 경로 | 목적 |
|---|---|
| `PROJECT_PLAN.md` | v2.0 범위와 단계별 통과 기준 |
| `AI_LICENSE_AUDIT.md` | 모델 후보·버전/가중치/코드/지역·상업 조건·미확인 |
| `PRIVACY_DESIGN.md` | 현재 메모리 흐름과 향후 소유권·보관·삭제 설계 |
| `PLAY_STORE_CHECKLIST.md` | 정책별 필수·조건부·권장 구분과 근거 |
| `TECHNICAL_RISKS.md` | 사진 복원/실제 피팅 한계와 후속 실험 |
| `AGENTS.md`, `README.md`, `.env.example`, `.gitignore` | 현재 개발 규칙·실행·설정·산출물 제외 |
| `docs/PLAN.md`, `TASKS.md`, `DECISIONS.md` | 현재 기획·진행·의사결정 |
| `docs/ARCHITECTURE.md`, `API.md`, `CONVENTIONS.md`, `SETUP.md`, `GIT_GUIDE.md` | 구현과 일치하는 구조·계약·검사·브랜치 흐름 |
| `docs/archive/` | 기존 CLOSET-VERSE 기획을 과거 기록으로 보존 |
| `backend/app/{main,core,api,services,schemas}` | 로컬 API와 파일 검증, 설정·오류·응답 |
| `backend/tests/test_uploads.py`, `pyproject.toml`, `requirements*.txt` | 15개 경계 테스트, 도구, 재현 가능한 의존성 |
| `frontend/src/{App,main,index.css,components,routes,api,lib,stores,types}` | 반응형 8개 화면과 실제 세션 동작, 향후 연동 경계 |
| `frontend/{package*.json,tsconfig*.json,vite.config.ts,eslint.config.js,index.html,.env.example}` | React/TS/Vite/Tailwind 설정과 lock |
| `frontend/e2e/`, `playwright.config.ts` | 실제 브라우저와 API 연결 회귀 검사 |
| `frontend/public/third-party-notices.txt` | 포함한 React/Lucide/Tailwind 라이선스 고지 |
| `docker-compose.yml` | 다음 단계용 로컬 DB/Redis 구성 (이번 단계 실행 안 함) |

## 다음 지시 후 계획

2단계는 MediaPipe 모델 번들·가중치 조건 고정 → 기기 내 포즈 특징점 → 키 기준 상대 길이 추정
→ 추정 출처/수동 치수 구분 → 중립 마네킹 파라미터 뷰어 순으로 진행할 예정이다.
얼굴 재현·의복 아래 실제 체형 복원·정밀한 피팅을 구현된 것처럼 표시하지 않는다.
현재 작업은 0·1단계에서 종료하고 다음 지시를 기다린다.
