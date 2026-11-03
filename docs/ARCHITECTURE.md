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
추론 엔진은 `services/garment_ai.py`, 모델 준비/해시는 `model_manifest.json`과 `scripts/prepare_models.py`다.
OCR은 `backend/ocr`의 Node 24 subprocess가 로컬 언어 데이터와 WASM만 사용하며 임시 이미지·OCR 캐시를 쓰지 않는다.
현재 서버 큐/Celery/Redis는 없다. CPU 경합은 429로 응답하며 UI에서 재시도한다. 로컬 개발용 선택이다.
SQLAlchemy/Alembic/PostgreSQL 드라이버를 도입했지만 현재 실행은 SQLite 개발 DB다. PostgreSQL 실접속·운영 마이그레이션은 미검증이다.
원본 이미지 메타데이터는 제거하되 픽셀 해상도를 유지한 PNG를 DB binary로 보관한다. Asset UUID 이외 파일명을 보관하지 않고 공개 저장소가 없다.
세션은 scrypt 암호 해시·SHA256 토큰 해시·12시간 만료. 클라이언트 토큰은 탭 메모리이며 로그아웃/새로고침 후 재로그인한다.
모든 개인 데이터/이미지에서 소유권을 검사한다. 계정 삭제는 암호 확인 후 연관 행을 제거한다. 신고 검토 API는 별도 서버 관리자 키로 제한한다.
4단계 A 실제 메시/GLB 생성을 추가했다. 가상 피팅과 B 실제 고정밀 엔진은 미구현이다. 현재 구현은 [PHASE4_DESIGN.md](PHASE4_DESIGN.md)를 따른다.

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
