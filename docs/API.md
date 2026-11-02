# StyleFit AI — 3단계 API

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
이미지별 10MiB/20MP, 전체 HTTP body 85MB, 분석 JSON 200KB, 로컬 계정 의류 100벌 제한.
저장 시 EXIF·위치·파일명 제거, 디코딩된 원본 픽셀/해상도를 PNG로 보존한다. 저장 누끼는 추론 출력 최대 변 1600px다.
`info`는 이름/category/종류/색/패턴/소매/넥라인/핏/시각특징/사이즈/소재/구성/치수/설명이며 길이·범위 검증한다.
치수 `{label,size,value,unit:cm|mm|inch|unknown,kind:flat|circumference|length|unknown,target:garment|body|unknown,source:ocr|user_entered}`.
소재 `{name,percent:null|0..100,source:ocr|user_entered}`. 합계 불일치는 UI에서 원본 확인을 안내한다.

응답: id/user_id/info/analysis/created_at/revision/analysis_status/assets 및 미래 `model_3d_status:not_implemented`, `model_3d_asset_id:null`.
분석 JSON은 클라이언트가 제출한 원본 제안의 스냅샷이며 서버 서명된 증명 자료가 아니다.

- `GET /garments`: 본인 목록. 이미지 내용 대신 slot별 Asset UUID/MIME.
- `GET /garments/{id}`: 본인 상세. 다른 계정/없는 의류는 모두 404.
- `PATCH /garments/{id}`: `{info,revision}`. 수정 정보만 변경하고 원본 분석 유지. 낙관적 잠금 충돌 409.
- `DELETE /garments/{id}`: 의류·관련 이미지·분석/수정 정보 트랜잭션 삭제. 204.
- `GET /assets/{id}`: Bearer와 소유권 확인 후 이미지. 공개 정적 파일 없음. UUID 파일명/PNG/no-store/nosniff.

## 신고·관리

- `POST /reports`: 인증 후 `{reason,garment_id?:본인 의류 ID}`. 접수 `{id,status:received}`.
- `GET /reports`: 본인 신고 ID/상태만.
- `GET /admin/reports`, `PATCH /admin/reports/{id}`: 서버 비밀 `X-Admin-Review-Key` 필요. 설정이 비어 있으면 접근 불가. PATCH `{status:reviewing|resolved|rejected}`.
- 관리자 키는 프론트에 제공하지 않는다. 운영용 관리자 인증·감사/외부 권리자 공개 접수 웹은 후속 출시 준비 항목이다.

## 보안·오류

모든 응답 no-store/nosniff. Host/Origin/클라이언트 loopback 제한. 비밀·사진·OCR 원문 애플리케이션 로그 없음.
실행 시 `--no-access-log` 사용. 로컬 HTTP를 외부 서버 전송에 그대로 확장하지 않는다. 운영 HTTPS는 미검증이다.
기본 오류 `{error:{code,message}}`. 400 입력, 401 로그인, 403 접근, 404 리소스, 409 충돌, 413 크기, 415 형식, 429 동시 분석/인증 제한, 503 모델/추론 실패.
