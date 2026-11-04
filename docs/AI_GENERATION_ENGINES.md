# 4단계 AI 생성 어댑터 도입 상태

검토일 2026-11-04. 범위는 4단계와 5단계 연결 경계다. 기존 기능을 삭제하거나 새 단계를 구현하지 않는다.

## 실제 상태

Windows / NVIDIA GeForce GT 1030 2048 MiB / Python 3.12 / PyTorch 2.15.0+cpu를 직접 확인했다. 기존 생성기는 사진 외곽을 반영하는 패널/바지 파라미터 메시이며 비공개 GLB·큐·권리 철회·피팅 계약을 유지한다.

두 독립 어댑터와 입력/GLB 검사 경계를 작성했지만 **두 AI 모델은 설치·추론·GPU 검증하지 않았다**. 전체 도입 완료가 아니다. 엔진 카탈로그는 두 AI 엔진을 모든 환경에서 비활성화한다. GPU 교체나 환경변수만으로 켜지지 않는다. 격리된 CUDA 환경, 고정 코드/가중치 해시와 전체 종속성 감사 후 별도 구현·검증이 필요하다. 기존 CPU 환경에 CUDA 패키지를 덮어쓰지 않았다.

## API·큐

`POST /garments/{id}/generate-3d`의 선택 필드 `engine: template | triposr | trellis2`와 A/B 권리 모드는 별개다. `{}`는 기존 template. 소유권·권한을 먼저 검사하고 사용 불가 엔진은 503 ENGINE_UNAVAILABLE로 거절한다. 이전 GLB/큐를 삭제하거나 다른 엔진으로 몰래 대체하지 않는다.

상태 응답의 `engines`는 가용성·요건·감사 상태·사유, `selected_engine`은 작업 스냅샷의 엔진을 제공한다. API는 가중치를 로딩하지 않으며 하드웨어 조회는 프로세스 수명 동안 캐시한다.

queued → processing(전처리 preprocessing / 생성 inference / 후처리 postprocessing / 검증 validating / 저장 saving) → completed 또는 failed. 템플릿의 기존 mesh/exporting도 유지한다. 큐 JSON에는 사진 대신 자산 ID만 기록한다. 워커가 권한·revision을 재검사하고 취소/철회/claim 토큰 검사를 유지한다. 30분 AI lease는 향후 경계일 뿐 GPU 운영 검증이 아니다. 자동 lease 갱신·GPU 강제 취소·격리 배포는 남은 작업이다.

## 전처리·출력·피팅

3단계 SAM의 저장된 `cutout_front`를 재사용한다. 없으면 CUTOUT_REQUIRED로 보류하고 rembg/보조 가중치를 자동 다운로드하지 않는다. MIME/실제 형식·20MP·알파 영역·최소 크기를 검사하고 종횡비를 보존해 896 정사각형에 배치한다. A는 단색 실루엣으로 RGB 세부 표현을 제거한다. B는 독립적인 세 권한 verified와 저장 이미지가 필요하다. 기존 사진 처리/보관 동의와 철회를 유지하며 외부 추론 API는 없다.

어댑터는 공식 TSR/Trellis2ImageTo3DPipeline API 및 GLB 내보내기 경로를 호출하도록 작성했다. 로컬 모델 경로는 `backend/models/engines/{engine}`이며 설치되지 않았다. 이 추론 코드는 실행 검증되지 않았고 CUDA 환경에서 조정이 필요할 수 있다. 모델 ID 자동 다운로드를 사용하지 않는다.

AI GLB 검사기는 바이너리를 재파싱해 자체 포함 여부, float 좌표·16/32비트 면 인덱스·stride/offset·유한 값·UV 수·재질·이미지 범위·면 수 예산·퇴화/비다양체를 확인한다. 미지원 압축/외부 URI는 거부한다. 의류의 정상 개구부를 자동으로 구멍 채우기 하지 않는다. 실루엣 정확도·목/팔/다리 공간·두께·신체 충돌은 미검증으로 기록한다. 전역 자기 교차·전체 재질 검증·Khronos 전체 validator를 대체하지 않는다. TRELLIS 감면 목표 외 품질 검증된 자동 최적화/복구는 없다.

AI는 `generation_kind=ai`, `wearable=false`, `unit=uncalibrated`, `coordinate_system=unverified`, `fitting_contract=null`. 템플릿은 procedural이다. 서버 피팅 조회와 클라이언트 로드/변형에서 AI 메시를 차단한다. 기존 템플릿으로 다시 생성하는 명시적 대체 경로를 제공하며 AI 성공으로 위장하지 않는다. 자동 재토폴로지·봉제/리깅/물리 피팅은 미구현이다.

## 비교 재현

backend에서 `.venv/Scripts/python scripts/compare_generation_engines.py`. 사용자 누끼는 `--tshirt 경로 --pants 경로`로 지정한다. 기본은 **합성 티셔츠·와이드 바지**이며 실사진 품질 비교가 아니다. 동일 입력 SHA-256을 엔진별 행에 기록한다. 미실행 AI의 시간/VRAM/크기/정확도는 null이다. 현재 비교기는 baseline만 실행하며 AI가 준비되면 실제 실행 루프 확장이 필요하다.

실제 산출물: Git 제외 `backend/storage/engine-comparison/tshirt-template.glb`, `wide-pants-template.glb`, `results.json`. 첫 측정은 티셔츠 229,980 bytes / 0.203초, 바지 886,204 bytes / 0.489초(CPU). 퇴화면·비다양체 0, 경계 루프 4/3. 자기 교차·실사진 정확도·착용감을 이 수치로 판정하지 않는다. AI GLB는 없다.

## 남은 조건

1. TripoSR용 지원 CUDA GPU·격리 환경, 코드/가중치/보조 모델/torchmcubes와 모든 전이 의존성 버전·해시·고지 감사.
2. TRELLIS.2용 Linux·NVIDIA 24GB+와 비상업 종속성의 별도 상업 허가 또는 실제 교체·검증된 허용 경로.
3. 동일 실사진 추론·텍스처/VRAM/시간/재로딩·의류 구조 실측. 미실행을 추정 점수로 채우지 않는다.
4. 의미 부위·개구부·두께·충돌을 검증한 변환기. 그 전까지 AI 자동 착용 불가.
