# 4단계 실제 생성 구조

## 범위와 생성 기술

A는 프로젝트에서 직접 작성한 파라미터 표면 템플릿을 변형하는 CPU 생성기다. 신경망 Image-to-3D를 실행했다고 표시하지 않는다. 3단계의 앞/뒤 분석 제안과 사용자 수정 정보를 사용하되, 사진 픽셀·패턴·자유 서술·로고는 생성기에 전달하지 않는다.
티셔츠·셔츠·니트·재킷·코트·청바지·슬랙스·반바지·스커트를 지원한다. 후드티·카디건·패딩·기타·unknown은 미지원이다. 카테고리 불일치와 생성 범위 밖 치수는 오류로 처리한다.
현재 템플릿은 기본 몸판/소매/바지통/스커트 표면이다. 재킷/코트는 앞 트임을 둔다. 실제 봉제 패턴, 리깅, 충돌, 원단 물성 시뮬레이션이 아니다. 몸판과 소매/바지통은 겹치는 별도 표면이며 봉제 가능한 연속 토폴로지를 보장하지 않는다.

종류·색·소매·넥라인은 수정 정보 우선, 비어 있으면 앞면→뒷면 분석 순으로 채택한다. 길이·의류 단면 너비·소매 치수는 target=garment, kind 및 cm/mm/inch가 분명한 값만 사용한다. 직접 입력 치수 우선, OCR 제안 다음이며 나머지는 기본 비율/추정이다. 이름이 정확히 대응하지 않는 치수·신체 치수·단위 미확인은 임의 변환하지 않는다. 깊이와 후면 구조는 항상 추정이다. 앞/뒤 분석은 관측된 태그의 출처일 뿐 정확한 3D 형상을 입증하지 않는다.
색은 일반 팔레트/HEX에 대응하며 미지원 색명은 기본색 추정으로 표시한다. 재질은 원본 이미지 없는 단색 PBR roughness/metallic 값이다. 일반 색/형태만 생성하며 보호 그래픽은 텍스처·UV 입력 경로 자체가 없다. A도 적법한 입력·처리를 전제로 하며 모든 디자인의 법적 안전을 보장하지 않는다.

## 큐와 저장

API는 GenerationJob을 DB에 queued로 기록하고 202를 반환한다. 별도 `python -m app.generation_worker` 프로세스가 작업을 claim하여 생성한다. 기존 SQLAlchemy를 사용하는 영속 DB 큐이며 새 브로커/라이브러리를 추가하지 않았다. 대규모 신경망 GPU 생성용 큐를 구현했다고 주장하지 않는다. 향후 대규모 AI는 Celery/Redis 워커로 확장한다.
상태는 idle/queued/processing/completed/failed/cancelled, 실제 단계는 queued/mesh/validating/saving/completed다. 가짜 진행률은 없다. 작업 입력은 정규화된 일반 의류 명세이며 사진·원문·계정명을 포함하지 않는다.
조건부 claim·고유 claim_token·120초 lease로 이중 저장을 방지한다. API/워커 재시작 후 queued 작업은 유지되며, 만료된 processing은 최대 3회까지 회수한 뒤 실패한다. 유효 lease는 다른 워커가 회수하지 않는다. 이 워커는 짧은 CPU 템플릿 생성용이며 120초 이상 GPU 작업이나 heartbeat를 지원하지 않는다.
생성은 메모리에서 수행하고 GLB 검증 후 Asset(slot=model_3d, model/gltf-binary)에 같은 트랜잭션으로 저장한다. 서버에 임시 사진/메시 파일을 생성하지 않는다. GLB 자체 포함 JSON/BIN, positions/normals/indices/PBR 재질을 저장하고 재파싱해 유한 좌표·삼각형 인덱스·입체 범위·재질 연결을 확인한다. 출력은 공개 URL 대신 인증 API로 제공한다.

## 권한과 무효화

photo_rights_status의 confirmed는 사진 처리 권한에 대한 사용자 확인이다. 관리자 문서 검증인 verified와 구분한다. 사용자는 verified를 제출할 수 없다. 새 의류는 기존 X-Upload-Rights 확인으로 confirmed를 서버가 기록한다. 과거 데이터는 unverified로 이전해 재확인한다.
사진 unverified/pending는 보류. confirmed/verified이면서 나머지 복원 권한 미확인은 A. 세 권한 verified면 B를 자동 선택하되 B 엔진이 없어 503 B_UNAVAILABLE로 생성하지 않는다. disputed/rejected가 하나라도 있으면 생성/모델 접근을 중단한다. 기술 미준비를 숨기고 A로 자동 대체하지 않는다.
증빙은 5MiB 이하 PDF/이미지(최대 의류당 10개)를 명시 동의 후 DB 비공개 저장한다. 단순 참조 접수는 pending일 뿐 승인되지 않는다. 관리자 키가 설정된 로컬 검토 API로만 실제 문서를 내려받고, 세 범위별 판단·증빙 ID·구체적 근거·검토 시각·권한 버전을 기록한다. verified는 해당 의류의 실제 증빙이 있어야 가능하다. 형식 검사나 AI가 법적 진위를 판정하지 않는다. 운영용 담당자별 인증·감사·기간/지역/만료 조건은 미완성이다.
권리 신고·철회·관리자 판단 변경·검토 재신청·정보 수정·모델 삭제는 진행 작업을 취소하고 기존 GLB를 삭제한다. 저장 직전 job 토큰·권한 버전·의류 revision·현재 작업 ID를 확인하므로 늦은 결과가 삭제된 모델을 복원하지 못한다. 모델 다운로드는 소유권과 현재 권한을 재검사한다. 브라우저는 상태를 주기적으로 조회해 무효 모델을 화면에서 제거한다. 이미 내려받은 바이트를 원격 회수할 수 있다는 의미는 아니다.
분석 오류 신고는 권리 신고와 구분한다. 권리 신고는 생성을 중지하지만 분석 오류 신고는 자동으로 권리 상태를 바꾸지 않는다.

## 5단계 연결 계약

GLB garment_root.extras: category, garment_type, bounds, dimensions(단위 meter 및 출처), coordinate_system=y_up_z_front, handedness=right, pivot, attachment_anchor, mannequin_anchor, layer, mode, version, created_at, mesh_names/material_names, 추정 영역, physical_simulation=false.
모델 하단 y=0, X/Z 기준축은 원점이다. 마네킹과 동일한 미터/Y-up/Z-front이며 top→chest, bottom→waist, outer→shoulder에 모델 기준점을 대응시킨다. 단순 스케일/위치 조정의 입력 구조만 준비했으며 실제 체형 장착·리깅·천 피팅은 구현하지 않았다.
B는 동일한 결과/메타데이터 계약으로 연결할 경계만 있다. 검증되지 않은 외부 모델/가중치/API는 설치·호출하지 않았다.
