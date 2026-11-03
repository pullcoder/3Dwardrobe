# 현재 아키텍처

## 5단계 피팅·코디 경로

React StudioPage: 탭의 사진/수동 체형 + 세 의류 슬롯 → 인증 GET fittings/resources → 권한/카테고리/메타데이터 검사 → 인증 GLB → 계정/화면 수명에 한정한 제한 캐시 → 지원 부위별 정점 복제/변형 → 신체 근사·내부 의류 방사선 검사 → 동일 Canvas의 MannequinModel + 의류 3벌.
스튜디오 변경은 기본 탭 메모리다. 별도 동의+저장 시 최소 체형/출처·모드 → SavedMannequin 불변 스냅샷 → Fitting(현재 의류/모델 UUID, 조절값, revision) → Outfit(이름/저장 당시 마네킹·모델/조절값).
원본 신체 사진/얼굴/관절은 서버로 보내지 않는다. 기존 BodyVault의 암호화 기기 저장과 별도 경로다. 서버 DB는 계정별 접근 제어이며 디스크 암호화/운영 HTTPS를 검증했다는 의미가 아니다.
새 테이블 saved_mannequins/fittings/outfits는 users FK cascade, mannequin_id는 SET NULL이다. 의류 ID/모델 UUID는 스냅샷 JSON에 보존해 의류 삭제 후에도 코디가 오류 없이 누락 안내를 반환한다. 모든 참조를 쓰기/조회 시 서버에서 소유권·현재 권한과 대조한다. 피팅 PATCH는 새 마네킹을 만들고 이미 저장된 코디의 체형을 바꾸지 않는다.
마이그레이션 d51e2a7b0903은 c41d8f03a902 다음이다. 본인 피팅·코디 삭제 후 참조가 없는 마네킹을 정리하며 계정 삭제로 전부 제거한다. 상세는 [PHASE5_DESIGN.md](PHASE5_DESIGN.md).

## 3단계 의류 경로

```text
React PhotoPicker: 권리 확인 → 로컬 파일 검증·미리보기·드롭·교체/삭제
 → 계정 Bearer 인증 + 분석 전송 안내
 → 원시 이미지 /garments/analyze|segment|ocr
 → 바이트·픽셀·실제 형식 검사 → 동시 1건 threadpool CPU 추론
    ├ CLIP: 고정 영문 후보와 cosine similarity, 불명확하면 unknown
    ├ SAM: 중앙/수정 포인트 → 투명 PNG (앞/뒤 별개)
    └ Node Tesseract WASM: stdin 이미지 → 한글/영문 OCR → 보수적 행 파싱
 → 브라우저 결과 비교·원본 JSON/OCR·수동 정보 편집
 → 별도 저장 동의 + POST /garments
 → SQLAlchemy: User / LoginSession / Garment(JSON info·analysis 분리) / Asset(binary) / Report
 → 인증된 본인 목록·이미지·수정(PATCH revision)·삭제(FK cascade)
```

추론 중 사진/임베딩은 요청 범위만 유지하고 자동 DB 저장하지 않는다. 모델 객체/텍스트 후보 임베딩만 재사용한다.
추론 엔진 구현은 `ai/garment_analysis.py`(호환 진입점 `services/garment_ai.py`), 모델 준비/해시는 `model_manifest.json`과 `scripts/prepare_models.py`다.
OCR은 `backend/ocr`의 Node 24 subprocess가 로컬 언어 데이터와 WASM만 사용하며 임시 이미지·OCR 캐시를 쓰지 않는다.
현재 서버 큐/Celery/Redis는 없다. CPU 경합은 429로 응답하며 UI에서 재시도한다. 로컬 개발용 선택이다.
SQLAlchemy/Alembic/PostgreSQL 드라이버를 도입했지만 현재 실행은 SQLite 개발 DB다. PostgreSQL 실접속·운영 마이그레이션은 미검증이다.
원본 이미지 메타데이터는 제거하되 픽셀 해상도를 유지한 PNG를 DB binary로 보관한다. Asset UUID 이외 파일명을 보관하지 않고 공개 저장소가 없다.
세션은 scrypt 암호 해시·SHA256 토큰 해시·12시간 만료. 클라이언트 토큰은 탭 메모리이며 로그아웃/새로고침 후 재로그인한다.
모든 개인 데이터/이미지에서 소유권을 검사한다. 계정 삭제는 암호 확인 후 연관 행을 제거한다. 신고 검토 API는 별도 서버 관리자 키로 제한한다.
4단계 A 실제 메시/GLB와 5단계 시각적 근사 피팅을 제공한다. B 실제 고정밀 생성 엔진은 미구현이다. 현재 구현은 [PHASE4_DESIGN.md](PHASE4_DESIGN.md)를 따른다.

### 복원 정책 DB 변경

Garment에 reconstruction_mode(A 기본), source_type(other 기본), rights_status(unverified 기본), license_reference(nullable), original_image_retention(temporary 기본), generated_model_path(nullable), model_visibility(private 고정), rights_reviewed_at(nullable)를 추가한다.
등록 시 클라이언트는 출처·원본 보관 선택과 A 기본값만 제출한다. 증빙 참조 접수는 pending일 뿐 승인되지 않는다. 4단계 실제 문서의 관리자 검토에서 세 권한을 판단하고, 서버가 A/B를 자동 결정한다. B 엔진은 비활성화다. revision으로 편집·검토 신청 충돌을 차단한다.
마이그레이션 b34a9c12d701은 기존 의류를 A/미확인/비공개로 초기화하며 과거 저장 동의는 consented_storage로 보존한다. 신규 temporary 등록은 누끼 포함 픽셀 데이터를 DB에 남기지 않는다.
기존 DB는 API 시작 전 Alembic upgrade head가 필요하다. create_all은 기존 컬럼을 변경하지 않는다. model_3d_status/asset_id는 호환 유지하며 generated_model_path는 같은 모델 Asset을 가리키는 private: 내부 참조다.

### 4단계 영속 작업·권한·GLB

Garment에 photo_rights_status/detailed_rights_status/output_rights_status, rights_version, generation_status/job_id/error, model_format/version, updated_at을 추가한다. 생성 상태와 권한은 별도다. 이전 의류의 사진 권한은 unverified로 이전하며 새 등록은 기존 입력/처리 권한 확인 헤더로 confirmed(사용자 확인)를 기록한다.
GenerationJob은 garment FK cascade, snapshot(픽셀 없는 일반 명세), mode/status/stage, rights_version/garment_revision, claim_token/lease_until/attempts, 결과 메타데이터/오류/시각을 보관한다. user_id는 소유 Garment를 통해 결정하며 클라이언트가 주입하지 않는다.
RightsEvidence는 의류별 비공개 증빙 binary·MIME·SHA-256·시각, RightsReview는 증빙 ID·범위별 판단·근거·시각·권한 버전을 보관한다. 의류/계정 삭제 시 cascade 제거한다. Report.kind로 권리 신고/분석 오류를 구분한다.
API는 작업만 등록한다. 별도 generation_worker가 DB 큐를 소비하며 파라미터 삼각형 메시→자체 포함 GLB 검증→Asset(slot=model_3d)에 저장한다. 공개 static/외부 AI/임시 사진 파일은 없다. GLB API와 기존 Asset 경로 모두 인증·현재 권한을 검사한다.
관리자/소유자 변경과 워커 완료는 작업 토큰·권한 버전·의류 revision·현재 job ID 조건으로 결과 게시를 보호한다. 신규 마이그레이션 c41d8f03a902는 b34a9c12d701 다음이다. 자동 create_all로 기존 스키마가 갱신됐다고 가정하지 않는다.

## 2단계 브라우저 체형 경로

```text
전신 사진 File (기기 메모리) → 권리/처리 동의 + 키
 → 1600px 이하 ImageBitmap → 동일 출처 classic Worker
 → MediaPipe Pose Full v1 / CPU / IMAGE / numPoses=2
 → 관절 가시성·전신 여백·단일 인물 검사 → 2D 상대 길이 × 입력 키
 → 사진 체형 (추정/직접 입력 구분) ↔ 별도 수동 체형
 → React Three Fiber: 부위별 중립 3D 마네킹 + OrbitControls
 → 기본 탭 저장 / 명시 선택 시 Web Crypto 암호화 기기 저장
```

`features/body/`: 출처·추정·품질 검사, Worker 클라이언트, 관절도, 암호화 보관함, Face Landmarker 어댑터 경계.
`features/mannequin/`: meter/Y-up/Z-front 규격, 타원 단면 torso·capsule 팔다리, 부위 이름·garment_anchors, 지연 로드 뷰어.
`public/pose-worker.js`: 입력 Bitmap은 추론 후 닫고 요청 종료 때 Worker를 terminate한다. 원본 전송 API는 없다.
`scripts/prepare-vision.mjs`: 버전 고정 SDK/WASM 복사, 가중치 해시 확인. 자동 다운로드 산출물은 Git 제외.
`public/mediapipe/`: 재현 스크립트가 준비하는 정적 추론 에셋. 사용자 데이터가 아니다.

기본 얼굴은 직접 만든 중립 기하 형태다. FaceLandmarkProvider와 실제 FaceLandmarker를 주입할 어댑터만 제공하며 얼굴 가중치는 설치하지 않았다.
기기 보관함은 평문 개인 데이터를 저장하지 않지만 서버 사용자 인증을 구현한 것은 아니다.
2단계 당시 스튜디오는 마네킹만 표시했다. 현재는 위 5단계 경로로 실제 GLB 의류를 같은 씬에 장착한다.

## 1단계 당시 흐름 (현재 의류 경로는 위 3단계 참조)

```text
React/TS/Vite/Tailwind (127.0.0.1:5173)
  ├─ 세션 Context: 사진 File·직접 입력 치수·의류 초안 (메모리 전용)
  ├─ 객체 URL: 화면 미리보기 → 제거/언마운트 시 해제
  └─ 사용자 명시 선택 → 원시 이미지 body → FastAPI (127.0.0.1:8000)
       ├─ 로컬 클라이언트/Host/Origin 제한, no-store
       ├─ 요청 바이트/이미지 디코딩/형식/픽셀 제한
       └─ 크기 정보 응답. 파일·DB 저장/AI/외부 전송 없음
```

## 폴더

- `frontend/src/routes/`: 대시보드·체형·마네킹·의류·피팅·추천·옷장·설정 화면
- `frontend/src/components/`: 공용 입력·상태·직접 제작 SVG 컨셉 일러스트
- `frontend/src/types/domain.ts`: 치수·슬롯·직접 입력 초안·API 타입
- `frontend/src/stores/SessionContext.tsx`: 브라우저 메모리 상태
- `frontend/src/api/client.ts`: 서버 호출 경계, API 오류·타임아웃
- `frontend/src/lib/images.ts`: 로컬 이미지 선택 검증
- `frontend/e2e/`: 실제 브라우저 흐름 회귀 테스트
- `backend/app/core/`: 루트 .env 명시 로딩, 오류
- `backend/app/api/v1/`: health와 이미지 검증 라우터
- `backend/app/services/`: 이미지 형식/디코딩 검증
- `backend/app/schemas/`: Pydantic 응답
- `backend/tests/`: API 경계·유효성·접근 제한 테스트
- `docker-compose.yml`: 향후 개발용 PostgreSQL/Redis, 현재 API 미사용

## 향후 확장 경계

2단계 기기 내 MediaPipe → 결과 출처와 confidence/치수 정의가 있는 별도 스키마.
서버 AI는 작업 서비스/워커로 분리하고 라우터에서 모델을 로드하지 않는다.
3D는 Three.js/R3F 뷰어를 필요 시 지연 로드한다. 의류 복원/피팅 엔진은 포함하지 않는다.
DB 모델·Alembic 초기 마이그레이션은 3단계에 추가했다. Celery 앱·분산 Job·오브젝트 저장소는 아직 없다.

과거 모델 초안은 [archive/ARCHITECTURE.md](archive/ARCHITECTURE.md)이며 현재 DB 스키마가 아니다.

## 6단계 추천 경로와 파일 정리

`features/recommendations` → 인증 preferences/recommendations API → `services/recommendations.py`(소유권·현재 권리·영속 기록) → `services/recommendation_rules.py`(순수 점수·조합·다양성) → Recommendation/StylePreference → 권한 검증 미리보기·apply → 기존 StudioDraft/FittingViewport. 영속 추천과 기존 3D Outfit은 구분하고 옷장 코디 탭에서 함께 조회한다.

새 마이그레이션 `e61f3b8c1004`는 `d51e2a7b0903` 다음이다. 신규 style_preferences/recommendations의 user FK는 CASCADE, 선택 마네킹 참조는 SET NULL이다. 원시 체형 프로필/사진은 추천 테이블에 저장하지 않는다. 최소 비교 설명도 개인정보로 취급한다.

사용자가 요청한 파일 정리를 유지한다. SQLAlchemy 모델은 `app/models/`의 도메인별 모듈에서 정의하고 `models/__init__.py`로 기존 import를 보존한다. 의류 추론 구현은 `app/ai/garment_analysis.py`, 생성 워커 구현은 `app/workers/generation.py`다. 기존 `services/garment_ai.py` 및 `python -m app.generation_worker`는 호환 진입점이다. 프론트엔드 피팅 컴포넌트·알고리즘·캐시·CSS·코디 보관함은 `features/fitting/`으로 모았다. 파일 이동 자체로 기존 모델/추론/워커의 동작을 바꾸지 않는다.

## 4단계 GLB 런타임 복구

장애 당시 API/프론트엔드는 실행 중이었지만 별도 생성 워커가 없었고 동일 DB에 queued 작업 2건이 남았다. `app.local_dev`는 현재 DB의 Alembic head를 확인한 뒤 같은 Python/환경으로 API와 `app.generation_worker`를 함께 실행한다. 분리된 워커 구조는 유지하며 API 내부 스레드로 생성 성공을 모사하지 않는다. 자식 프로세스 장애는 함께 중지하고 재실행 시 영속 큐를 이어 처리한다.

`generation_workers`는 익명 프로세스 UUID·템플릿 엔진 버전·heartbeat 시각만 보관한다. 유효 기간은 15초이며 사진·사용자 ID·DB 접속 정보는 없다. GenerationJob에는 nullable failure_stage/exception_type을 추가했다. 새 migration f71a4c9d1105는 e61f3b8c1004 다음이다.

기존 make_meshes → build_glb → validate_glb → DB Asset/모델 참조 원자적 저장 경로를 재사용한다. 실제 내보내기 단계 관찰을 추가하고 빈 씬 GLB를 거부한다. 새 템플릿·가중치·3D 파일 포맷·공개 스토리지는 도입하지 않았다.

## 바지 photo silhouette → pants v2

의류 등록 또는 명시적 silhouette 재입력 → 서버 `pants_silhouette.py`: 알파/단색 배경, 연결 성분, 외부 flood-fill, 다리 분기와 49개 높이의 외/내측 경계 → 수치만 계정별 analysis에 보관 → generation snapshot의 수치 프로필 → `pants_mesh.py`: 허리/골반/밑위 분기를 연결하는 전후 패널과 두 바지통, 일반 밴드/주름 변위 → `pants_materials.py`: A 자체 체크 또는 검증된 B 앞면 투영 → VEC2 UV와 내장 PNG를 포함하는 실제 GLB → 기존 비공개 Asset/권한/lease 저장.

세 의미 부위 이름 waist/leg_left/leg_right는 유지한다. 5단계 로더는 stylefit.pants.v2 계약을 인식하고 사진 외곽을 옛 원통 중심으로 다시 압축하지 않는다. stylefit.parts.v1 구형 모델과 상의/겉옷 경로는 그대로 지원한다. 원본 보관·권리 검증·소유권·계정/의류 삭제·늦은 작업 게시 방지를 유지한다. 새로운 DB 컬럼/마이그레이션은 필요하지 않다.

B의 영속 snapshot에는 서버가 선택한 이미지 Asset UUID/좌표만 둔다. 작업 직전 해당 의류와의 대응 및 세 권한을 다시 확인해 메모리에서만 읽고, 후면은 원본과 별개로 추정한다. B를 일반 고정밀 엔진으로 표시하지 않는다.

## 바지 표면 품질 보완 (2026-11-03)

바지 엔진 stylefit-pants-2.1은 기존 49행 사진 외곽과 stylefit.pants.v2 계약을 유지한다. 표면 표본을 가로49/상부33+밴드행/다리65행으로 늘리고 납작한 초타원 단면, 세로 드레이프, 접힌 허리/밑단을 만든다. 공유 좌표의 법선을 평균해 부위 경계 음영을 연결한다. 재질은 자체 생성 미세 체크/짜임이며 검증된 B 앞면 atlas는 1536×1280으로 출력한다. 기존2.0 재질의 GLB 검증도 버전별로 유지한다. DB/API/권한 계약은 바뀌지 않는다.

A의 미세 원단 UV는 표면 단면의 호 길이에 따라 배치해 옆면에서 체크가 늘어나는 현상을 줄인다. B의 앞면 투영 좌표는 별도로 유지한다.

## 의류 생성 파이프라인 보완 (2026-11-04)

기존 상의 ring 몸판+독립 sleeve 조합을 티셔츠에 한해 연결 패널 엔진으로 교체했다. garment_templates 카탈로그→top_silhouette의 몸판 폭/소매 범위 추정→pattern_top의 오목한 목 구멍을 보존한 triangulation/공유 중점 subdivision→앞뒤 패널 및 어깨/옆선/소매 경계 봉합→mesh_quality의 개구부·연결·퇴화·비다양체·winding 검사→GLB→stylefit.panel.v3 연속 가중 피팅을 사용한다. 몸판과 소매가 한 메시이며 단순 겹침으로 연결하지 않는다. 기본/오버핏 티셔츠와 기존 와이드/슬림 바지부터 보완한다. 셔츠/재킷은 legacy_approximation, 후드티 연결 템플릿은 unavailable이다. 기존 기능을 지원 완료로 다시 분류하지 않는다. 피팅은 bottom→top→outer 순서로 하의가 상의의 내부 레이어가 되도록 보정한다. 외부 시뮬레이션은 앱 워커와 분리된 실험이다.
