# 6종 입체 의류 템플릿과 기존 마네킹 연동

사용자의 2단계 템플릿 제작 요청에 따라 추가했다(2026-11-04). 기존 마네킹/배경 제거/서버 GLB 피팅/추천 경로를 유지하고 새 로컬 편집기를 분리했다. TRELLIS.2 실행 전환 작업이 아니며 신규 GPU·외부 의류 자산·패키지·모델 가중치는 필요하지 않다.

## 사용 위치와 완료 범위

`http://127.0.0.1:5173/#/studio` → **템플릿 만들기**. 로그인 없이 사용할 수 있다. 기존 계정 기반 기능은 **내 옷장 입어보기**에 그대로 있다. 기본은 반팔 티셔츠와 청바지를 동시에 착용한다. 의류 종류/템플릿 선택으로 교체하고 선택 의류 제거·전체 제거·형태 초기화·전체 초기화가 가능하다. 외투를 입히면 상의/하의와 같은 씬에 3벌이 표시된다. 드래그로 회전하고 정면/측면/후면·확대/축소/시점 초기화, 경량/표준 품질, 부위 색상 구분을 제공한다.

| 의류 | ID | 기본 정점 | 삼각형 | 원단을 두껍게 하기 전 개구부 테두리 |
|---|---|---:|---:|---:|
| 반팔 티셔츠 | short_tshirt | 2,768 | 5,320 | 4 |
| 긴팔 티셔츠 | long_tshirt | 2,768 | 5,320 | 4 |
| 청바지 | jeans | 3,190 | 6,384 | 3 |
| 슬랙스 | slacks | 3,190 | 6,384 | 3 |
| 후드집업 | zip_hoodie | 3,466 | 6,636 | 4 |
| 재킷 | jacket | 2,768 | 5,244 | 3 |

파일을 받은 듯 가장하지 않고 **재사용 가능한 Three.js BufferGeometry/Group**으로 직접 생성한다. GLB 파일 6개를 내려받거나 별도 저장한 구현은 아니다. 외부 의류 모델을 가져오지 않았으며 기존 Three.js/R3F 라이선스 고지를 유지한다.

## 메시 구조와 좌표

기존 `MannequinModel`, `bodyDimensions`, `ellipseRadius`, `CameraControls`를 재사용한다. 기존 마네킹의 미터 단위·Y-up/Z-front·팔과 다리 축을 사용하며 원래 마네킹 파일은 수정하지 않았다.

상의/외투는 타원형 몸통 링을 로프트하고 측면 암홀 면을 제거한 경계에 소매 로프트를 직접 연결한다. 목과 밑단, 소매 끝은 캡으로 막지 않는다. 바지는 허리/골반의 링에서 가랑이 공유 곡선을 통해 두 바지통으로 분기한다. 후드는 머리 뒤/옆을 감싸는 별도 곡면 부위로 목 위치에 배치하며 얼굴 앞은 연다. 외투 앞판은 열린 구조다. 후드와 몸판의 물리 봉제 시뮬레이션이나 지퍼 여닫기는 구현하지 않는다.

표면의 공유 간선을 따라 면 방향을 일관되게 정렬한다. 법선 방향으로 1.8mm 안쪽 표면을 만들고 목/소매/허리/밑단 가장자리를 연결해 **원단 두께만** 닫는다. 의복 내부 공간 자체를 채우지 않는다. 그래서 원단 셸의 간선은 각 2개 면을 가지면서 목·허리·바지통의 착용 공간은 비어 있다. 목 및 양쪽 바지통의 광선 통과 검사로 캡이 없음을 확인한다.

의미 부위는 geometry material groups와 `geometry.userData.semantic_parts`로 구분한다: body, collar, sleeve_left/right, waist, hips, leg_left/right, hood, edge_binding. 부위별 색상 옵션으로 확인할 수 있다. 위치·법선·UV·인덱스 버퍼를 제공한다. 기본 UV는 몸통/소매/바지통/후드의 로프트 좌표이며 원본 사진에 맞는 부위별 UV 보정·텍스처 전사는 다음 연결 작업이다.

## 실제 변형과 레이어

슬라이더는 object.scale을 바꾸지 않는다. 총장은 몸통 링의 Y 위치, 어깨너비는 어깨 링과 소매 시작/끝 위치, 가슴/몸통 폭은 단면 반경, 소매 길이는 소매 경로를 바꾼다. 하의는 허리/골반 반경, 가랑이 높이, 허벅지·밑단 단면, 바지통의 높이별 곡선을 독립적으로 다시 계산한다. 안쪽 의류 폭/깊이/어깨/소매보다 바깥층이 넓도록 여유를 둔다. 마네킹의 몸통 타원과 실제 팔다리 캡슐 반경으로 일부 정점을 바깥으로 보정한다. 이는 몸과 레이어의 관통을 줄이는 근사이며 모든 삼각형 충돌을 해결하는 물리 시뮬레이션은 아니다.

| 값 | 디자인 범위(미터) |
|---|---|
| 상의 총장 / 외투 총장 | 0.50~0.82 / 0.60~0.86 |
| 어깨너비 / 가슴·몸통 폭 | 0.46~0.58 / 0.32~0.54 |
| 반팔 / 긴팔·외투 소매 | 0.18~0.32 / 0.45~0.67 |
| 허리 / 엉덩이 폭 | 0.27~0.46 / 0.35~0.56 |
| 밑위 / 허벅지 폭 | 0.22~0.38 / 0.15~0.30 |
| 바지 길이 / 밑단 폭 | 0.76~1.04 / 0.13~0.30 |

모든 입력은 0~1이다. UI cm는 디자인 기준을 표시하며 체형/안쪽 옷/지면 높이 제한으로 실제 적용 치수는 보정될 수 있다. 실제 치수라고 과장하지 않는다.

## 사진 분석 연결 계약

`catalog.ts`의 `resolveTemplateInput(unknown)`이 종류·템플릿·항목·유한 0~1 범위를 검사한다. `physicalParameters`가 템플릿별 미터 범위에 매핑한다. `garmentGeometry.ts`의 `createTemplateGarment(input, profile, innerEnvelope?, showParts?)`가 실제 메시를 반환한다. `wide_pants`는 슬랙스의 와이드 기본값 별칭이다.

```json
{
  "category": "pants",
  "template": "wide_pants",
  "parameters": {
    "waistWidth": 0.5,
    "hipWidth": 0.6,
    "thighWidth": 0.7,
    "legLength": 0.8,
    "hemWidth": 0.75
  }
}
```

밑위는 생략 시 기본값이다. 상의는 length/shoulderWidth/chestWidth/sleeveLength, 외투는 length/shoulderWidth/bodyWidth/sleeveLength, 하의는 waistWidth/hipWidth/rise/thighWidth/legLength/hemWidth를 받는다. 사진 분석 자동 연결·사진 전송·영구 저장은 추가하지 않았다. 기존 누끼 API와 사진 보관/권리 검증은 별도 경로로 유지한다.

## 성능·수명

모델 파일 로딩이 없는 네이티브 메시이며 연결 인덱스는 템플릿별로 최대 6개 캐시한다. 부위/레이어 의존성이 바뀐 메시만 useMemo로 다시 생성하고 교체/제거 시 geometry/material을 해제한다. 기존 수동 프레임 갱신과 DPR 1의 경량 모드를 재사용한다. 기본 3겹 조합은 약 18,340 삼각형이며 인체 메시의 기존 복잡도는 유지한다. 의류별 위치/법선/UV/인덱스 버퍼는 약 120~151KB다. 이는 전체 JS/GPU 메모리 또는 실기기 FPS 측정값이 아니다.

## 검증·산출물

최종 결과: backend ruff check/format 및 pytest **116개 통과**, frontend lint/typecheck/build 및 Vitest **24개 통과**, 전체 Playwright **36개 통과(5.6분)**. 기존 실제 배경 제거/OCR·마네킹·옷장·추천·GLB 생성/삭제·피팅/철회 흐름을 포함한다. 빌드의 기존 대형 Three.js 청크 경고는 남아 있다. 초기에 새 선택 컨트롤의 레이블 연결을 보완했고, 시각 검증에서 어깨/무릎의 노출과 면 방향을 수정한 뒤 최종 전체 검사를 통과했다. git diff --check도 통과했다. 프론트와 API는 HTTP 200이며 기존 서버/워커를 유지한다. 커밋·푸시·공개 배포는 하지 않았다.

- 단위 검사: 6종의 유한 좌표·UV·정점/면·공유 간선·면 방향·퇴화면·두께·목/바지통 공간, 모든 조절 항목의 국소 정점 이동, 최솟값/최댓값 조합, 레이어 여유, 캐시 재사용, JSON/잘못된 값/프로토타입 항목 거절.
- 브라우저 검사: 데스크톱·모바일의 6종 선택/실제 캔버스, 모든 슬라이더, 상하의·외투 동시 착용, 제거/초기화, 부위 색상, 카메라 시점/드래그, 기존 옷장 화면 복귀. 스크린샷을 직접 보고 어깨·무릎 보정을 반영했다.
- 메시 측정과 검증 그림은 Git 제외 `backend/storage/template-validation/metrics.json`, `short_tshirt.png`, `long_tshirt.png`, `jeans.png`, `slacks.png`, `zip_hoodie.png`, `jacket.png`, `side.png`, `semantic-parts.png`에 있다. 새 6종을 GLB로 내보냈다는 뜻은 아니다.
- 측정 재현: frontend에서 `$env:STYLEFIT_TEMPLATE_REPORT='1'; npx vitest run src/features/templates/garmentGeometry.test.ts`. 그림 재현: `npx playwright test e2e/templates.spec.ts`.

## 추가·수정 파일

| 파일 | 역할 |
|---|---|
| frontend/src/features/templates/catalog.ts | 6종·정규화 범위·입력 계약 |
| frontend/src/features/templates/garmentGeometry.ts | 연결 셸·두께·부위·UV·변형·근사 보정·캐시 |
| frontend/src/features/templates/TemplateWorkbench.tsx | 종류/템플릿/슬라이더/제거/초기화 |
| frontend/src/features/templates/TemplateViewport.tsx | 기존 마네킹·레이어·카메라 재사용과 리소스 수명 |
| frontend/src/features/templates/templates.css | 반응형 편집기 |
| frontend/src/features/templates/garmentGeometry.test.ts | 메시/변형/계약 회귀 검사와 측정 산출 |
| frontend/e2e/templates.spec.ts | 실제 브라우저 조작·렌더링·복귀 검사 |
| frontend/src/routes/StudioPage.tsx | 기존 기능과 새 편집기 선택 |
| frontend/src/features/fitting/studio.css | 작업 선택 버튼 배치 |
| docs/ARCHITECTURE.md, API.md, SETUP.md, DECISIONS.md, AI_LICENSE_AUDIT.md, 이 문서 | 계약·실행·원본 자산/라이선스·검증·한계 기록 |

## 미구현·한계

원단 물성/봉제 시뮬레이션, 전역 자체 교차/정밀 신체 충돌, 모든 체형에서 관통이 0이라는 보증, 지퍼 애니메이션·디테일 재단, 사진 전용 UV 최적화·자동 사진 파라미터 추론, 이 새 편집기의 서버 GLB 저장/코디 저장 및 실기기 Android FPS/발열 측정은 구현하지 않았다. 요청한 기본 6종의 입체 템플릿·부위별 변형·기존 마네킹 실시간 착용과 구분한다.
