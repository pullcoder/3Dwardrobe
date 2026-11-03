# StyleFit AI — 3~5단계 API

Base: `http://127.0.0.1:8000/api/v1`. loopback 개발 전용이며 production 설정을 거절한다. `/docs`에 요청 스키마가 있다.
신체 사진·관절·체형을 전송하는 API는 없다. 체형 분석과 암호화 기기 보관함은 기존 브라우저 경로를 유지한다.

## 인증

`POST /auth/register`, `POST /auth/login`: JSON `{username,password}`. 계정명 3~40자 영문/숫자/_/-, 암호 12~128자.
응답 `{token,user:{id,username}}`. 세션은 12시간, 클라이언트는 탭 메모리만 사용한다. DB에는 토큰 해시만 저장한다.
`POST /auth/logout`: Bearer 토큰 폐기, 204.
`DELETE /auth/account`: Bearer + JSON `{username,password}` 재확인 후 계정·세션·의류·이미지·신고 cascade 삭제, 204.
아래 개인 데이터 API는 `Authorization: Bearer TOKEN`이 필요하다. 요청 body의 user_id를 받지 않고 서버 인증에서 결정한다.
로그인/가입 제한은 로컬 단일 프로세스 메모리 기반이며 다중 서버 운영용 공유 제한기는 아니다.

## 상태와 기존 검증

- `GET /health`: `status:ok`, `mode:local_preview`, `features:{image_validation:true,ai:모델파일준비여부,storage:true,auth:true}`. DB 연결 점검·모델 정확도·출시 준비 판정이 아니다.
- `GET /garments/capabilities`: classification/segmentation/ocr 파일 준비 여부, `device:cpu`, `external_api:false`.
- `POST /uploads/validate`: 기존 익명 형식 검증. 원시 이미지 body + Content-Type + `X-Upload-Rights:confirmed`. `{content_type,size_bytes,width,height,retained:false,ai_processed:false}`. 파일 저장하지 않는다.

## 실제 로컬 AI

| 경로 | 요청·응답 |
|---|---|
| `POST /garments/analyze` | 원시 이미지 body. CLIP 구조화 JSON: 모델/방법/종류/category/주·보조색/패턴/소매/넥라인/핏/특징/소재/실제 유사도·후보차이/warnings |
| `POST /garments/segment?x=0.5&y=0.5` | 원시 이미지 body. 정규화 좌표 0~1(기본 중앙)의 SAM 마스크 → 투명 PNG base64 `png`, width/height/model/predicted_iou/warnings |
| `POST /garments/ocr?kind=size` 또는 `material` | 원시 이미지 body. 실제 OCR text/confidence/model/sizes/measurements/composition/warnings |

세 경로 모두 Bearer, `X-Upload-Rights:confirmed`, `X-Image-Processing-Consent:confirmed`, 이미지 MIME이 필요하다.
JPG/PNG/WebP 정지 이미지, 실제 형식 대조, 10MiB/20MP 이하. 이미지를 자동 DB 저장하지 않는다.
분류는 앞/뒤 개별 호출, 보조색·핏·세부 부자재·사진 기반 소재는 null/unknown. 유사도와 SAM predicted_iou는 원시 모델 점수이며 확률 정확도가 아니다. SAM 점수가 1을 넘을 수도 있어 임의 보정하지 않는다.
OCR은 명시된 단일 수치 행만 파싱하고 여러 사이즈 열의 대응은 미확인으로 남긴다. 단위/의미/대상이 불명확하면 unknown. OCR 원문은 수정 입력과 구분한다.
동시 CPU 추론은 한 건. 추가 요청 429, 모델 누락/무결성 실패/엔진 오류 503, 인식 실패 400. 외부 API는 없다. 사진을 추론 서비스에 업로드할 URL 입력은 지원하지 않는다.

## 의류 저장·조회·수정·삭제

`POST /garments`: Bearer + `X-Upload-Rights:confirmed`, `X-Image-Storage-Consent:confirmed`.

```json
{
  "info": {"name":"내 옷","category":"top","material":"미확인","measurements":[],"composition":[]},
  "analysis": {},
  "images": {"front":{"content_type":"image/png","data":"BASE64"}}
}
```

이미지 slot: front 필수, back/size/material/cutout_front/cutout_back 선택. 한 요청에 한 벌. 누끼는 PNG만 허용한다.
추가 입력: `reconstruction_mode:A`(기본, B 거절), `source_type:self_photographed|licensed_image|other`(기본 other), `original_image_retention:temporary|consented_storage`(기본 temporary).
기존 저장 동의 헤더는 의류 정보 저장에 필요하다. 별도 consented_storage 선택 시만 사진·누끼를 보관한다. temporary는 형식 검증 후 모든 이미지를 폐기하고 assets는 빈 객체다.
등록/PATCH의 미정의 필드는 거절하며 클라이언트는 승인 상태·검토 시각·모델 경로·공개 범위를 부여할 수 없다.
이미지별 10MiB/20MP, 전체 HTTP body 85MB, 분석 JSON 200KB, 로컬 계정 의류 100벌 제한.
원본 보관 동의 시 EXIF·위치·파일명 제거, 디코딩된 원본 픽셀/해상도를 PNG로 보존한다. 저장 누끼는 추론 출력 최대 변 1600px다.
`info`는 이름/category/종류/색/패턴/소매/넥라인/핏/시각특징/사이즈/소재/구성/치수/설명이며 길이·범위 검증한다.
치수 `{label,size,value,unit:cm|mm|inch|unknown,kind:flat|circumference|length|unknown,target:garment|body|unknown,source:ocr|user_entered}`.
소재 `{name,percent:null|0..100,source:ocr|user_entered}`. 합계 불일치는 UI에서 원본 확인을 안내한다.

응답: id/user_id/info/analysis/created_at/revision/analysis_status/assets 및 model_3d_status/model_3d_asset_id. 4단계 생성 성공 후 completed와 비공개 모델 Asset UUID가 연결된다.
추가 응답: reconstruction_mode, source_type, rights_status(unverified/pending/approved/rejected), license_reference(null 또는 참조), original_image_retention, generated_model_path(null), model_visibility(private), rights_reviewed_at(null).
4단계 추가 응답에는 photo_rights_status, detailed_rights_status, output_rights_status, rights_version, generation_status, generation_job_id, model_format, model_version, generation_error, updated_at이 있다. source_type은 사용자 진술이며 승인 증명이 아니다. 신규 사진 권한은 헤더 확인으로 confirmed를 기록하며, 관리자의 문서 검증 verified와 구분한다.
분석 JSON은 클라이언트가 제출한 원본 제안의 스냅샷이며 서버 서명된 증명 자료가 아니다.

- `GET /garments`: 본인 목록. 이미지 내용 대신 slot별 Asset UUID/MIME.
- `GET /garments/{id}`: 본인 상세. 다른 계정/없는 의류는 모두 404.
- `PATCH /garments/{id}`: `{info,revision}`. 수정 정보만 변경하고 원본 분석 유지. 낙관적 잠금 충돌 409.
- `DELETE /garments/{id}`: 의류·관련 이미지·분석/수정 정보 트랜잭션 삭제. 204.
- `POST /garments/{id}/rights-review`: 본인 Bearer + `{license_reference,revision,evidence_id?:증빙UUID}`. 참조 공백 제거 후 5~1000자. pending, A 유지, 검토 시각 null, revision +1. 참조 접수 자체는 승인되지 않으며 기존 모델/진행 작업을 무효화한다. 타인/없는 의류·증빙 404, 중복 pending/오래된 revision 409. URL을 자동 조회하지 않는다.
- `GET /assets/{id}`: Bearer와 소유권 확인 후 이미지. 공개 정적 파일 없음. UUID 파일명/PNG/no-store/nosniff.

## 신고·관리

`POST /reports`에는 kind:rights|analysis(기본 rights)를 추가한다. 본인 의류의 권리 신고는 세 권한을 disputed로 변경하고 생성 작업 취소·모델 삭제·다운로드 차단을 수행한다. 분석 오류 신고는 권한을 변경하지 않는다.

- `POST /reports`: 인증 후 `{reason,garment_id?:본인 의류 ID}`. 접수 `{id,status:received}`.
- `GET /reports`: 본인 신고 ID/상태만.
- `GET /admin/reports`, `PATCH /admin/reports/{id}`: 서버 비밀 `X-Admin-Review-Key` 필요. 설정이 비어 있으면 접근 불가. PATCH `{status:reviewing|resolved|rejected}`.
- 관리자 키는 프론트에 제공하지 않는다. 운영용 관리자 인증·감사/외부 권리자 공개 접수 웹은 후속 출시 준비 항목이다.

## 보안·오류

모든 응답 no-store/nosniff. Host/Origin/클라이언트 loopback 제한. 비밀·사진·OCR 원문 애플리케이션 로그 없음.
실행 시 `--no-access-log` 사용. 로컬 HTTP를 외부 서버 전송에 그대로 확장하지 않는다. 운영 HTTPS는 미검증이다.
기본 오류 `{error:{code,message}}`. 400 입력, 401 로그인, 403 접근, 404 리소스, 409 충돌, 413 크기, 415 형식, 429 동시 분석/인증 제한, 503 모델/추론 실패.

## 4단계 생성·비공개 GLB

기존 prefix `/api/v1`를 유지한다. 아래 경로는 본인 Bearer가 필요하며 다른 사람/없는 의류는 404다.

| 경로 | 요청·응답 |
|---|---|
| POST /garments/{id}/generate-3d | JSON `{}`만 허용. 권한·지원 종류·치수를 검사하고 영속 큐 등록 후 202 상태 응답. 중복 활성 작업 409, 권한 미확인/분쟁 403, 미지원/치수 422, B 선택이나 엔진 미준비 503 |
| GET /garments/{id}/generation-status | 생성 상태·실제 단계·오류 코드·모델 준비 여부·메타데이터 |
| GET /garments/{id}/rights-status | 같은 상태 응답에 세 권한·버전·자동 선택 모드·B 가용성 포함 |
| GET /garments/{id}/model | 현재 권한/소유권 재검사 후 model/gltf-binary, attachment UUID.glb, no-store. 생성 전/무효/삭제 모델 404 |
| DELETE /garments/{id}/model | 모델 제거 및 대기/진행 작업 취소, 204 |
| POST /garments/{id}/photo-rights-confirmation | JSON `{}` + X-Upload-Rights:confirmed. 과거 unverified 사진 권한을 사용자 확인 confirmed로 기록한다. verified를 직접 입력할 수 없다. 신고/거절/철회는 관리자 재검토 전 403 |
| POST /garments/{id}/rights-withdraw | JSON `{}`. 세 권한 disputed, 작업 취소·모델 제거, 204 |
| POST /garments/{id}/rights-evidence | 원시 PDF/JPG/PNG/WebP + MIME + X-Evidence-Storage-Consent:confirmed. 최대 5MiB, 의류당 10개. `{id,sha256}`. 비공개 DB 저장이며 URL 수집/진위 자동 판정 없음 |

상태 응답 필드: garment_id, selected_mode(A/B/null), b_available(false), photo_rights_status, detailed_rights_status, output_rights_status, rights_version, rights_reviewed_at, generation_status, job_id, stage, generation_error, model_ready, model_format, model_version, model_metadata, updated_at, supported_types.
권한은 unverified/confirmed(사진 사용자 확인)/pending/verified(관리자 증빙 검증)/rejected/disputed, 생성은 idle/queued/processing/completed/failed/cancelled다. 단계는 실제 mesh/validating/saving 등이며 백분율을 만들지 않는다. 워커가 없으면 queued를 유지한다.
사진 confirmed/verified + 나머지 미검증이면 A, 세 범위 verified면 B, 미확인 사진/분쟁/거절은 보류한다. B 엔진은 없으며 승인됐다는 이유만으로 가짜 생성하거나 A로 바꾸지 않는다.
모델 원본은 Asset binary이며 generated_model_path는 private:garment/... 내부 참조다. 공개 파일 경로가 아니다. 이미지 assets 응답에는 model_3d 슬롯을 넣지 않고 별도 모델 API로 조회한다. 기존 /assets/{id}로 모델 UUID를 접근해도 현재 권한·모델 상태를 검사한다.

## 관리자 권리 검토 (로컬 전용)

모든 경로는 서버의 X-Admin-Review-Key가 필요하며 빈 설정이면 거절한다. 이 키를 프런트엔드에 제공하지 않는다.

- GET /admin/garments/{id}/rights-evidence: 증빙 ID·해시·MIME·접수 시각 목록.
- GET /admin/rights-evidence/{id}: 실제 문서 attachment, application/octet-stream/no-store/nosniff. 문서를 앱에서 자동 실행/렌더링하지 않는다.
- PATCH /admin/garments/{id}/rights-review: `{photo_rights_status,detailed_rights_status,output_rights_status,evidence_id?,notes,rights_version}`. 각 범위 unverified/verified/rejected/disputed. notes 공백 제거 후 10~2000자. 하나라도 verified면 해당 의류의 실제 evidence_id 필수. 담당자가 실제 문서를 확인하고 범위별 근거를 기록해야 한다. 버전 충돌 409. 변경 시 이전 작업/모델 무효화, rights_version +1, 검토 시각·불변 판단 이력 기록.
- GET /admin/garments/{id}/rights-reviews: 범위별 판단·증빙 참조·근거·시각 이력.

증빙의 존재·형식은 법적 허락의 진위를 보증하지 않는다. 담당자 검토가 필요하며 운영용 담당자별 인증·자동 만료/지역/기간 조건 집행은 아직 없다.

## 5단계 비공개 피팅·코디

기존 `/api/v1` prefix와 Bearer 인증을 유지한다. user_id·모델 경로·권한 상태를 클라이언트에서 받지 않는다. 다른 계정/없는 데이터는 404다.

| 경로 | 실제 동작 |
|---|---|
| GET /fittings/resources/{garment_id} | 본인 의류·현재 모델 권한·좌표/단위/카테고리 검사. garment_id/name/category/info/model_asset_id/metadata/reconstruction_mode/rights_version/status:available. 모델이 없거나 철회된 경우 404, 메타데이터 불일치 422 |
| POST /fittings | 아래 입력을 저장하고 201. 새 불변 마네킹 스냅샷과 현재 모델 UUID를 고정 |
| GET /fittings/{id} | 본인 피팅 상태/마네킹/슬롯/조절값/누락 안내 |
| PATCH /fittings/{id} | 같은 입력 + revision. 새 마네킹 스냅샷·슬롯/조절값·revision +1. 충돌 409 |
| DELETE /fittings/{id} | 피팅 삭제, 어느 코디/피팅에서도 참조하지 않는 마네킹 정리. 204 |
| POST /outfits | `{fitting_id,name}`. 본인 피팅의 현재 유효 상태를 별도 코디로 복사, 201. 이름 1~80자, 빈 조합 400, 누락/무효 상태 409 |
| GET /outfits | 본인 코디 목록(최대 100개) |
| GET /outfits/{id} | 본인 코디·저장 당시 마네킹/모델 참조·조절값·누락 안내 |
| DELETE /outfits/{id} | 코디 삭제, 불필요 마네킹 정리. 204 |

피팅 입력 예시:
```json
{
  "body_storage_consent": true,
  "mannequin": {
    "mode": "manual",
    "values": {"height":175,"shoulder":42,"chest":94,"waist":78,"hip":98,"arm":56,"leg":81},
    "origins": {"height":"user_entered"}
  },
  "slots": {"top":"GARMENT_UUID","bottom":null,"outer":null},
  "adjustments": {"top":{"chest":1.04,"clearance":0.012,"hidden":false}}
}
```

수치는 cm이며 미입력은 null이다. mode manual/photo, origins는 각 수치의 estimated/user_entered만 허용한다. 사진/랜드마크/얼굴/비율/임의 필드를 거절한다. 별도 body_storage_consent가 없으면 400이며 저장하지 않는다. 키·어깨·가슴/허리/골반·팔·다리 범위는 기존 화면과 같고 팔/다리와 키의 비율도 검증한다.
슬롯 키는 top/bottom/outer, 카테고리 불일치 422, 타인/없는 모델 404. 조절값: shoulder/chest/waist/hip 0.8~1.25, sleeve/length 0.75~1.25, offset_y ±0.12m, clearance 0~0.06m, hidden boolean. 유한 수치만 허용하고 미정의 필드는 400이다. 계정당 피팅/코디 각각 100개 제한.
응답: id, mannequin_id, mannequin(mode/values/origins), slots, adjustments, created_at, warnings, revision(피팅만), name(코디만).
슬롯은 null 또는 available 리소스다. 저장 후 의류 삭제/모델 재생성/권한 철회 시 `{garment_id,status:unavailable,reason}`과 warnings를 반환하며 나머지 슬롯은 정상 복원한다. 상태 확인을 생략하고 이전 파일을 반환하지 않는다. B 모델은 세 권한 검증이 필요하며 A 권한으로 우회하지 않는다.
API는 장착 설정/최소 체형을 저장한다. 실제 정점 변형과 3D 렌더링은 클라이언트에서 수행하며 물리 시뮬레이션 결과를 저장한 것으로 표시하지 않는다.

## 6단계 취향·추천 API (`/api/v1`)

모두 Bearer 인증 필수이며 서버가 사용자 ID를 결정한다. extra 필드/임의 사용자 ID·사진 입력은 거부한다.

| 메서드 | 경로 | 동작 |
|---|---|---|
| GET / PUT | `/style-preferences` | 본인 취향 조회/수정. PUT에 revision, 최초 0, 충돌 409 |
| POST | `/recommendations` | count 3~5(기본4), 실제 보유 조합만 생성. 부족하면 0~요청 개수. 선택 body 또는 본인 mannequin_id, 별도 body_processing_consent 필요 |
| GET | `/recommendations` | 본인 목록. saved_only=false, limit=30(최대100), offset=0 |
| GET / DELETE | `/recommendations/{id}` | 본인 상세/기록·피드백·저장 상태 삭제 |
| POST | `/recommendations/{id}/feedback` | feedback: like/dislike/exclude/none |
| POST | `/recommendations/{id}/save` | 추천 코디 저장. 멱등, 유효하지 않은 의류 409 |
| GET | `/recommendations/{id}/preview/{part}` | 본인 실제 cutout_front 또는 front PNG. 미보관/권리 제한/삭제/정보 변경 404 |
| POST | `/recommendations/{id}/apply` | 선택 본인 mannequin_id. 현재 권리·카테고리·GLB·고정 모델 UUID 재검사 후 slots/pins/recommendation_id/mannequin 반환. 미준비 409 |

추천 상세는 실제 의류 정보·이유·치수 참고·engine·body_used·available·fitting_available·warnings·feedback·saved_at을 반환한다. 내부 점수/구성 요소는 서버에만 보관하며 사용자 만족도/신뢰도로 노출하지 않는다. 타인 ID는 404, 미인증 401, 잘못된 입력 400, 저장 한도 300개 초과 413. 모든 응답 no-store. `/apply`는 기존 피팅을 서버에서 덮어쓰지 않고 검증된 초안을 반환한다. 클라이언트 교체 확인 후 기존 스튜디오가 이를 표시하고 별도 동의/저장 API로 영속화한다.

## GLB 복구 진단 필드

기존 generate-3d 202는 작업 등록을 뜻하며 GLB 완료가 아니다. generation-status/rights-status의 응답에 `runtime: {engine, worker_online}`와 선택적 `failure: {stage, exception_type}`를 추가했다. worker_online은 같은 DB에서 같은 템플릿 엔진의 15초 이내 heartbeat가 있다는 뜻이며 모델 품질 보장이 아니다. 실패 단계는 mesh/exporting/validating/database_update/asset_storage/database_commit이다. 기존 `generation_error` 코드는 호환 유지한다.

실제 GLB는 기존 비공개 garment_assets binary에 저장한다. generated_model_path의 `private:garment/{garment_id}/{asset_id}.glb`는 공개 디스크 경로가 아니다. 인증된 `/garments/{id}/model` 또는 소유권을 확인하는 Asset API로만 읽는다. 모델 생성·취소·의류/계정 삭제와 권한 철회 경계를 유지한다.

## 바지 사진 외곽 분석 및 제한 B

`POST /api/v1/garments/{id}/silhouette`: Bearer, X-Upload-Rights=confirmed, X-Image-Processing-Consent=confirmed, 실제 JPEG/PNG/WebP Content-Type과 원시 이미지. 10MiB/20MP 및 실제 콘텐츠를 검사한다. 청바지/슬랙스/반바지만 지원한다. 본인 소유/현재 사진 권한/분석 전후 revision과 rights_version을 검사한다. 사진은 저장하지 않고 `{silhouette, generation, revision}`을 반환한다. 타인404, 동의누락400, 부적절 외곽422, 동시변경409. 정보 갱신은 이전 생성 작업/모델을 취소한다.

기존 POST garments에도 메모리 사진의 외곽 수치 분석을 추가했다. 분석 불가 시 등록은 허용하고 추정/오류 사유를 보관한다. 클라이언트 입력 analysis.silhouette은 무시한다. 사진 보관 선택과는 독립이다.

기존 generate-3d는 바지의 서버 분석 수치 또는 저장된 누끼/앞면을 사용한다. shape_source=photo_silhouette_estimate 또는 estimated, texture_policy=procedural_generic_check/solid_color/verified_front_projection, fitting_contract=stylefit.pants.v2, pants.outline/rise_ratio/observed/fit_inference 등을 모델 메타데이터에 제공한다. 뒤/깊이는 계속 추정이다.

b_available은 이제 해당 의류에 **제한적 바지 앞면 투영**이 기술적으로 가능한지 나타낸다. selected_mode는 여전히 기존 세 권한 정책을 따른다. b_high_fidelity_available=false이며 전체 B 고정밀 엔진은 없다. 세 권한 verified여도 지원 종류/보관 이미지/분석 가능한 윤곽이 없으면 B 요청을 거부한다. 클라이언트가 mode/권한을 주입할 수 없다. 원본 텍스처는 B에서만 비공개 GLB에 포함한다.

## 바지 표면 품질 보완 (2026-11-03)

바지 생성 응답의 model_version은 stylefit-pants-2.1이다. fitting_contract는 stylefit.pants.v2로 유지한다. 메타데이터 surface_detail=flattened_cloth_section_drape_folded_edges, detail_source=procedural_estimate는 세로 주름/접힌 단/단면을 절차적으로 추정했다는 뜻이다. 실제 원단 시뮬레이션이나 사진의 주름 복원이 아니다. 기존 A/B 소유권·증빙 검증·삭제 규칙을 유지한다.

## 의류 생성 파이프라인 보완 (2026-11-04)

`POST /garments/{id}/silhouette`는 티셔츠도 지원한다. 인증/소유권/X-Upload-Rights/X-Image-Processing-Consent 및 사진 미보관 규칙을 유지한다. top 결과는 kind=top, body_width_ratio, sleeve_extent_ratio, 일부 외곽 landmarks와 unknown 목 구조다. 명시 치수 우선, 사진의 절대 치수/뒷면은 확정하지 않는다. model_version=stylefit-panel-3.0, fitting_contract=stylefit.panel.v3, top_panel/mesh_quality/material_profile 메타데이터를 추가한다. 바지는2.2로 갱신하며 parts.v1/pants.v2 구형 계약도 유지한다. 런타임 자체 교차 검사는 not_evaluated_in_runtime으로 표시한다. Blender BVH 검사는 별도 실험 산출물이다.
