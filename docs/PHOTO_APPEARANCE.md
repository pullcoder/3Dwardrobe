# 티셔츠·바지 사진 외형 반영

2026-11-04. 사용자의 티셔츠·바지 모두 사진처럼 보이게 하는 요청에 따라 기존 바지 앞면 투영을 티셔츠와 앞뒤 사진으로 확장했다. 이전 바지 전용 범위보다 이 사용자 요청을 우선 적용하며 A/B 권리 검증은 유지한다.

## 구현

- B의 지원 종류는 티셔츠·청바지·슬랙스·반바지다. 기존 세 권한 verified와 보관 동의된 앞면 이미지가 필요하다. 원본/누끼를 임시 처리만 한 등록은 픽셀이 없으므로 사진 보관 동의로 다시 등록해야 한다. A는 기존 사진 외곽/일반 원단이며 원본 픽셀을 사용하지 않는다.
- 앞면은 `cutout_front` 우선, 없으면 단색 배경 `front`를 사용한다. 복잡한 배경은 누끼를 요구한다. 뒷면은 `cutout_back`/`back` 순으로 사용한다. 뒤 사진이 없으면 일반 원단으로 표시하며 앞면 그래픽을 복사하지 않는다.
- 티셔츠의 앞/뒤 패널 UV를 별도 아틀라스로 분리했다. 바지의 기존 사진 UV는 glTF 상단 원점에 맞춰 수정했고 뒤 사진은 뒷면 시점에 맞게 좌우를 정렬했다. 정상 개구부·의미 부위·미터 좌표·피팅 계약은 유지한다.
- 누끼 가장자리를 흰 배경에 합성하는 대신 주변 원단 색을 확장한다. 이는 UV/밉맵 가장자리의 흰 테두리를 줄이는 처리이며 새 원단 세부를 추론하는 모델이 아니다. 아틀라스는 기존 스튜디오 GLB 2MiB 한도를 위해 PNG 1MiB 예산으로 축소한다. 원본 사진 자체는 변경하지 않는다.
- 생성 메타데이터 버전 `stylefit-photo-projection-1.0`, `photo_appearance.front=verified_photo`, `back=verified_photo|estimated`, `uv_origin=top_left`. 기존 `texture_policy=verified_front_projection` 계약을 유지한다. 기존 GLB는 자동 변경하지 않으며 재생성 시 적용한다.
- 단독 의류 뷰어를 중립 배경/조명으로 조정하고 PNG 텍스처·ImageBitmap을 모델 제거 시 정리한다. 새 외부 모델·패키지·사진 전송 서비스는 없다.

## 사용

사진 보관에 동의하여 앞면과 가능한 뒷면/누끼를 등록 → 기존 권리 증빙 검토에서 세 권한 검증 → 3D 모델 생성 또는 재생성. 화면에서 사진 외형 반영 여부와 후면의 사진/추정 여부를 확인한다. 담당자 검증이나 원본 보관이 없으면 일반형 A를 제공하며 이를 원본 사진 복원으로 표시하지 않는다.

## 검증과 실제 산출물

직접 그린 색상 표식을 입력해 원본 색이 GLB PNG에 포함되는지, 앞뒤 분리·상하 방향·뒤 사진 누락·A 픽셀 비복제·기존 피팅 자원·철회를 검사한다. **실제 사용자 의류 사진의 사실성 품질 평가는 아니다.**

backend의 `scripts/verify_photo_appearance.py`는 Git 제외 `storage/photo-appearance/tshirt.glb`, `pants.glb`, 앞뒤 참조 PNG와 `results.json`을 만든다. 최종 티셔츠 239,020 bytes, 바지 918,496 bytes로 2MiB 한도 안이다. Three.js 실제 로더/이미지 디코딩/렌더링으로 데스크톱·모바일 앞뒤 픽셀을 확인하는 `frontend/e2e/photo-appearance.spec.ts` 4개가 통과했다. 검증용 색상 표식은 원본 사진이나 AI 생성 결과로 보고하지 않는다.

모델의 깊이·옆면·봉제·가려진 면은 기존 템플릿 추정이다. 사진의 주름/그림자는 색상에 포함되며 독립적인 조명/물리 주름으로 분리하지 않는다. 새로워진 것은 사진 외관 투영이고 GPU AI 입체 재구성이나 실측 스캔은 아니다. TRELLIS.2/TripoSR의 이전 하드웨어·라이선스 제한은 유지한다.

## 수정 파일

검사: backend ruff/format 통과, 전체 pytest 116개 통과. 이후 bbox 해상도 보정의 관련 17개 재실행 통과. frontend lint/typecheck/build 및 Vitest 14개 통과(기존 대형 청크 경고 유지). Playwright 전체 실행은 32개 통과/2개 실패였다. 실패는 삭제 완료 전에 GET을 호출한 테스트 순서 문제였고 DELETE 204를 기다리도록 수정했다. 이후 생성/삭제·사진 렌더링 6개를 재실행해 모두 통과했다. 최종 전체 34개가 한 번에 통과한 것으로 표시하지 않는다. 실패 실행의 전용 테스트 계정 2개는 정리했다. 새 사진 렌더 스크린샷도 직접 확인했다. 새 패키지·DB migration·외부 전송은 없다. API/워커를 재시작해 적용한다.

UV 원점 근거: [Khronos glTF 2.0 명세](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html).

- `backend/app/services/photo_materials.py`: 배경/누끼 가장자리 처리·앞뒤 아틀라스·용량 예산.
- `generation.py`, `pants_materials.py`: 저장 자산과 권리/큐 경계 연결.
- `pattern_top.py`, `pants_mesh.py`, `garment_mesh.py`: 티셔츠 사진 UV, 바지 방향, 사진 재질·메타데이터.
- `backend/tests/test_photo_appearance.py`, `backend/scripts/verify_photo_appearance.py`: 실제 GLB와 권리·피팅·참조 색 검증.
- `frontend/src/features/garments/GenerationPanel.tsx`, `GarmentDetail.tsx`, `types.ts`: 상태·사용 조건·현재 지원 범위.
- `GarmentModelViewer.tsx`: 중립 조명·사진 텍스처 자원 해제.
- `frontend/e2e/photo-appearance.spec.ts`: 실제 Three.js 렌더링과 앞뒤/상하 픽셀 검사.
- API/아키텍처/설치/결정/감사 문서: 현재 구현과 제약 기록.
