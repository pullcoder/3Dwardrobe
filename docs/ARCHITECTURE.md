# 현재 아키텍처

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
`model_3d_status`/`model_3d_asset_id`만 확장 경계이며 의류 3D 생성/피팅을 구현하지 않았다.

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
3D 의류는 아직 적용하지 않는다. 스튜디오는 선택한 체형만 실제 3D로 표시한다.

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
