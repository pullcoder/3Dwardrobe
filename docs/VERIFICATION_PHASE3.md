# 3단계 의류 분석·비공개 등록 검증

검증일 2026-11-03, Windows / Node 24.21.0 / Python 3.12.10. 기존 1~2단계를 유지하며 3단계만 확장했다.
분석 모델을 마지막 라이선스 검토에서 OpenCLIP으로 교체했으며 아래 결과는 최종 체크포인트 기준이다.

## 실제 기능

앞면 필수·뒷면/사이즈표/소재표 선택, JPG/PNG/WebP 형식·10MiB·20MP 검사, 미리보기/드롭/교체/삭제.
권리 확인 → 로컬 계정 → 분석 전송 동의 → 단계별 처리 상태 → 원본/누끼 비교 → OCR/분류 JSON 확인 → 편집 → 별도 비공개 저장 동의 → 옷장 등록.
실제 분류·누끼·OCR을 호출하며 처리 오류는 재시도한다. 성공한 부분 결과는 유지한다. 원본 제안과 사용자 수정 정보는 별도 JSON이다.
로그인하지 않고도 기존 수동 탭 초안은 계속 사용할 수 있다. 3D 의류 생성·가상 피팅은 제공하지 않는다.

옷장 카테고리/검색/상세·원본/누끼 보기/수정/삭제/재로그인 불러오기. 서버는 사용자별 의류·에셋 소유권 검사와 revision 충돌 검사를 수행한다.
계정 삭제에는 암호 재확인이 필요하며 관련 세션·의류·이미지·분석·신고를 삭제한다. 신고는 실제 서버 접수/상태 조회/관리자 검토 API를 제공한다.
정확한 API와 데이터 스키마는 [API.md](API.md), 처리 구조는 [ARCHITECTURE.md](ARCHITECTURE.md)에 기록했다.

## 모델과 라이선스

| 용도 | 최종 실제 모델 | 라이선스·출처 |
|---|---|---|
| 의류/색상/패턴/소매/넥라인 제안 | OpenCLIP ViT-B-32, LAION-2B s34B b79K, open_clip_torch 3.3.0 | 코드 MIT, [가중치 소유자 카드 MIT](https://huggingface.co/laion/CLIP-ViT-B-32-laion2B-s34B-b79K/blob/1a25a446712ba5ee05982a381eed697ef9b435cf/README.md) |
| 앞·뒷면 물체 분할 | SAM ViT-B 01ec64 | [공식 코드/모델 Apache-2.0](https://github.com/facebookresearch/segment-anything#license) |
| 한글·영문 OCR | Tesseract.js/core 7.0.0 + tessdata_fast kor/eng | [JS Apache-2.0](https://github.com/naptha/tesseract.js/blob/master/LICENSE.md), [학습 데이터 Apache-2.0](https://github.com/tesseract-ocr/tessdata_fast/blob/87416418657359cb625c412a48b6e1d6d41c29bd/LICENSE) |

가중치/데이터는 [고정 manifest](../backend/model_manifest.json)의 URL/커밋/SHA-256으로 준비하며 첫 사용 때 검증한다.
상업권 허용과 배포 적합성을 구분한다. OpenCLIP 모델 카드의 연구 목적/미평가 배포 범위 밖 안내에 따라 실제 의류 데이터셋 평가를 출시 전에 추가해야 한다.
원본 OpenAI CLIP 가중치는 코드 라이선스만으로 조건을 확정하지 않고 최종 파이프라인에서 제외했다. 상세 근거는 [AI_LICENSE_AUDIT.md](../AI_LICENSE_AUDIT.md).
외부 AI API·유료 제공자 키·의류 생성형 AI는 사용하지 않는다.

## 실제 추론 결과

`backend/scripts/verify_garment_ai.py`를 실행했다. 사용자 사진을 외부에서 수집하지 않고 직접 그린 합성 티셔츠/한글 라벨, 이전 단계의 공식 고정 체형 테스트 사진 일부만 사용했다.

- 합성 파란 반소매 티셔츠: 종류 티셔츠/top, 파랑, 무지, 반소매, 라운드넥. 종류 cosine similarity 0.27078, 후보 차이 0.02281. 정확도·확률 신뢰도로 표시하지 않는다.
- SAM 투명 PNG: 실제 RGBA, 모서리 alpha 0, 의류 중심 alpha 255, foreground bbox (62,102,539,600). 결과 이미지를 직접 열어 확인했다. predicted_iou 1.00916은 모델 원시 출력이며 100% 정확도라는 의미가 아니다.
- 한글 사이즈표: 사이즈 M, 가슴단면 50cm 인식. `총장`을 `종장`, 다른 행의 `cm`을 `07`로 오인식해 해당 치수를 자동 확정하지 않았다. 원문·수동 편집 제공. OCR 엔진 점수 89.
- 한글 소재표: 면 65%, 폴리에스터 35% 추출, 합계 100. OCR 엔진 점수 88. 제목의 일부 글자는 오인식했다.
- 기존 공식 실제 사진의 상반신 crop: 검정/긴소매 제안, 의류 종류는 unknown. 실제 의류 사진의 정확한 자동 분류 성공이나 14종 벤치마크 통과로 보고하지 않는다.
- 독립 검증 실행 시간 약 31.07초(첫 로딩 포함). GPU/CUDA 사용/드라이버 변경 없음. GTX 1060 6GB/드라이버 457.51은 확인만 했고 추론은 CPU다.
- 재현 산출물은 Git 제외 `frontend/e2e/fixtures/garments/`에 생성한다. 외부 사진 크롤링/학습/원격 추론 없음.

## 실행 검사

| 검사 | 결과 |
|---|---|
| backend ruff check / format --check | 통과 |
| backend pytest | 23개 통과: 기존 형식·접근 경계 + 의류 CRUD·계정·에셋·다른 사용자 차단·삭제·신고·수정 충돌·만료·전체 body 제한·모델 누락 오류 |
| pip check | 깨진 의존성 없음 |
| frontend ESLint / TypeScript / Vite build | 통과. 3D 지연 로드 청크 약 945KB min/249KB gzip 경고 유지, 초기 앱 약 312KB min/97KB gzip |
| Vitest | 기존 체형 추정·기하·암호화 저장 8개 통과 |
| Playwright | 18개 모두 통과 (약 3.2분). 기존 16개 회귀와 실제 의류 AI → 부분 실패/재시도 → OCR → 수정 → 저장 → 재로그인 → 삭제 desktop/mobile 2개. 가로 넘침·pageerror 없음 |
| 모델 독립 실행 | OpenCLIP·SAM·한글/영문 OCR 실제 CPU 추론 통과, 위 오인식 포함 |
| DB migration | 격리 SQLite에 upgrade → downgrade base → upgrade → alembic check 통과, 차이 없음 |
| PostgreSQL | Alembic PostgreSQL SQL 생성 성공. 서버/Docker 미설치로 실접속·실제 트랜잭션·성능 미실행 |
| 외부 AI API 실패 | 외부 API 미사용으로 해당 없음. 브라우저의 로컬 분류 요청 네트워크 실패를 주입해 오류·부분 결과·재시도를 검증 |

초기 브라우저 실패 원인은 테스트 fixture를 Playwright가 지우는 출력 폴더에 둔 점, 선택창의 label 탐색, 검색 입력과 의류 이름 입력의 중복 탐색이었다. fixture를 별도 Git 제외 경로에 준비하고 접근성 역할/정확한 이름으로 수정했다. 테스트 삭제·skip으로 우회하지 않았다.
첫 실행의 모델 검증 및 CPU 로딩으로 수십 초가 걸릴 수 있다. 진행률 수치를 만들어 표시하지 않고 실제 작업 단계만 안내한다.
PC·모바일 옷장 상세 스크린샷을 직접 열어 원본/누끼·치수·소재·카드 배치와 가로 넘침 여부를 확인했다. 이미지 산출물은 `frontend/test-results/garments-desktop.png`, `garments-mobile.png`이며 Git 제외다.

## 개인정보·권리

- 권리·처리·저장 확인을 구분하고 직접 촬영을 권장한다. 로고만으로 자동 차단하지 않으며 브랜드 제휴 표현/사용자 간 공유가 없다.
- 저장 전 분석 사진은 메모리, 저장은 본인 비공개 DB binary Asset. 원본 파일명/EXIF 제거, UUID, 다운로드까지 소유권 검사, no-store/nosniff.
- 계정 암호 scrypt, 서버 세션 토큰 해시·12시간 만료, 브라우저 토큰 메모리. 서버 제공 user_id를 사용하며 클라이언트 user_id를 신뢰하지 않는다.
- 학습 재사용·외부 AI 전송·이미지/암호/토큰/OCR 원문 로그 없음. 신체 사진은 계속 브라우저 MediaPipe 경로다.
- 계정 삭제와 의류 삭제의 실제 DB/Asset 제거를 검사했다. 매체·운영 백업 완전 소거까지 검증한 것은 아니다.
- loopback HTTP만 허용한다. 원격 서비스 HTTPS·운영 계정 복구/관리자 권한·백업/보관 만료/유해 콘텐츠 필터는 출시 준비 항목이다.
- 권리/분석 결과 신고는 서버 접수되며 본인 상태 조회와 관리자 키 기반 검토 API가 있다. 외부 권리자의 공개 연락처/운영 절차는 미완성이다.

## 기술적 한계·미구현

- CLIP 고정 후보 유사도 방식은 전문 의류 VLM이 아니다. 배경/조명/착용 인물과 유사한 종류에 민감하고 정책 임계값은 교정된 confidence가 아니다. 보조색·핏·단추/지퍼/주머니·사진만으로 소재 확정은 null/unknown이다.
- SAM 중앙 포인트는 일반 물체를 선택한다. 단독 의류 권장, 착용 인물/그림자/디테일 오류 가능, 위치 수정 재시도 제공. 정확한 의류 형태/알파 경계를 보장하지 않는다.
- OCR은 읽힌 단일 수치 행만 구조화한다. 복잡한 다중 사이즈 표의 열 대응, 범위/기울어진 라벨/흐린 글자/원단별 겉감·안감 구획은 자동 확정하지 않는다. 소재 백분율이 앞에 놓인 복합 표기 등은 수동 확인이 필요하다.
- 현재 SQLite는 PostgreSQL 실접속 검증을 대신하지 않는다. DB binary는 개발용 선택이며 대규모 서비스에는 비공개 객체 저장소·쿼터·워커·공유 제한기가 필요하다.
- AI 작업은 동시 1건이며 요청 완료까지 실행한다. 지속 작업 큐·분산 취소·자동 중단 복구는 없다.
- 운영 HTTPS/인터넷 배포/Android/Play 제출, 상표 선행 조사, 전체 의류 사진 데이터셋 정확도, 종속 바이너리의 최종 배포 고지는 미실행/미확인이다.
- 3D 의류 생성/GLB·물리 피팅·추천·코디 영구 저장을 구현하지 않았다.

## 변경·생성 파일

프론트:
- `frontend/src/features/garments/`: `types.ts`, `AccountPanel.tsx`, `AnalysisPanel.tsx`, `GarmentEditor.tsx`, `GarmentDetail.tsx`, `ReportPanel.tsx` 신규.
- `frontend/src/api/garments.ts` 신규. `routes/UploadPage.tsx`, `ClosetPage.tsx`, `SettingsPage.tsx`, `Dashboard.tsx`, `components/PhotoPicker.tsx`, `UI.tsx`, `stores/SessionContext.tsx`, `types/domain.ts`, `App.tsx`, `index.css` 변경.
- `frontend/e2e/garments.spec.ts`, `scripts/prepare-test-garments.mjs` 신규. `package.json`, `playwright.config.ts` 변경. 기존 body/foundation 테스트 유지.

백엔드:
- `backend/app/models.py`, `core/database.py`, `schemas/garments.py`, `services/auth.py`, `garment_ai.py`, `ocr_parser.py`, `api/v1/garments.py` 신규.
- `backend/app/main.py`, `core/config.py`, `api/v1/routes.py`, `requirements.txt`, `requirements.lock.txt` 변경.
- `backend/model_manifest.json`, `scripts/prepare_models.py`, `scripts/verify_garment_ai.py`, `ocr/package.json`, `ocr/package-lock.json`, `ocr/recognize.mjs`, `alembic.ini`, `migrations/` 신규.
- `backend/tests/test_garments.py`, `test_limits.py` 신규, `test_uploads.py` 상태 API 기대값 갱신.
- `backend/THIRD_PARTY_NOTICES.md` 서버 모델/코드 고지 신규.

문서/설정:
- 루트 `AGENTS.md`, `.env.example`, `.gitignore`, `README.md`, `PROJECT_PLAN.md`, `AI_LICENSE_AUDIT.md`, `PRIVACY_DESIGN.md`, `PLAY_STORE_CHECKLIST.md`, `TECHNICAL_RISKS.md`.
- `docs/API.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `SETUP.md`, `TASKS.md`, 이 보고서, `docs/licenses/`의 CLIP/OpenCLIP·SAM·Tesseract 라이선스/모델 카드.
- 0~3단계 변경은 협업용 기능 브랜치에서 백엔드·프론트엔드·문서/설정 커밋으로 분리해 PR로 제출한다. 기존 문서는 archive에 보존하며 main 직접 커밋/푸시·다른 작업 브랜치 변경·자동 병합·서비스 배포를 하지 않는다.

## 4단계 준비

의류 ID/user_id, 분리된 info/analysis, 원본/앞뒤 누끼 Asset, 치수·소재 의미와 원문을 후속 생성 입력으로 사용할 수 있다. model_3d_status/asset_id 확장 필드와 비활성 안내 버튼만 마련했다.
현재 코드로 의류가 생성/피팅된다고 표시하지 않는다. 실제 GLB 생성 모델과 종속 라이선스·GPU/품질 검증은 다음 사용자 지시 후 시작한다.
