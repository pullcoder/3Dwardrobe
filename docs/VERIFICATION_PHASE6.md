# 6단계 구현·검증 보고

## 구현 상태

- 기존 1~5단계 기능 및 사용자가 요청한 비커밋 소스 정리를 유지했다. 작업 브랜치는 `feature/stylefit-recommendations`이며 이번 변경을 원격에 커밋/푸시하거나 main에 통합하지 않았다.
- 취향 다중 스타일·핏·선호/회피 색상·선호 종류·목적·계절·분위기의 계정별 조회/저장/수정·revision 충돌 검사를 구현했다.
- 본인 실제 옷장으로 상의+하의+(선택 겉옷) 조합 생성, 설명 가능한 가설 점수, 다양성, 실제 명시 피드백 반영, 3~5개 요청/부족 시 가능한 개수만 반환한다. 고정 코디/가짜 의류를 만들지 않는다.
- 실제 보관 원본/누끼 이미지 조합 카드, 한국어 근거·치수 참고, 3D 미준비 비활성화·복원 안내, 저장·좋아요/별로예요/제외 및 해제·기록 삭제·목록 페이지를 구현했다. 생성형 이미지가 아니다.
- 현재 권리·등록 정보 revision·GLB 버전/카테고리/소유권을 재검증한 뒤 기존 스튜디오에 의류 ID·모델 UUID·추천 ID·선택 마네킹을 전달한다. 기존 코디 유지/교체 확인을 제공한다. 시각적 근사 피팅이며 물리 시뮬레이션이 아니다.
- 저장 추천을 옷장 코디 탭에서 다시 보고 불러올 수 있다. 기존 3D Outfit 저장을 삭제/대체하지 않는다. 별도 동의 없는 체형 전송, 원본 신체 사진 전송, 외부 AI 전송, 학습 재사용을 추가하지 않았다.

## 알고리즘·모델/라이선스

`stylefit-rules-1.0`: 스타일 .20, 색상 .18, 목적 .16, 계절 .12, 핏 .08, 치수 .12, 피드백 .08, 분위기 .04, 선호 종류 .02. 가중 합과 순차 Jaccard 다양성 페널티(.18), 동일 상하의 추가 페널티(.12)를 사용한다. 미확인은 중립값, 제외 피드백/권리 제한은 후보에서 제거한다. 점수는 내부 값이며 만족도·신뢰도·패션 품질이 아니다. 상세 공식과 초기 가설 구간은 [PHASE6_DESIGN.md](PHASE6_DESIGN.md)에 기록했다.

**이번 단계 실제 사용한 신규 AI 모델: 없음.** 자체 규칙 코드이며 새 코드/가중치 라이선스·API 약관 대상이 없다. 기존 상업 이용 감사 모델/라이브러리를 교체하지 않았다. [AI_LICENSE_AUDIT.md](../AI_LICENSE_AUDIT.md)에 반영했다. 외부 AI 오류 테스트는 해당 없음이며 로컬 추천 API 503 오류/재시도는 브라우저로 검증했다.

## API·DB

`/api/v1/style-preferences` GET/PUT, `/recommendations` POST/GET, `/{id}` GET/DELETE, `/{id}/feedback` POST, `/{id}/save` POST, `/{id}/preview/{part}` GET, `/{id}/apply` POST. 모두 Bearer 인증·본인 소유권, 목록 페이징, no-store. 사용자 ID는 서버 인증 정보에서 결정한다. [API 상세](API.md).

신규 StylePreference/Recommendation, Alembic e61f3b8c1004. 계정 삭제 시 CASCADE, 선택 마네킹 참조 SET NULL. 사용자 기존 DB는 변경하지 않았고 검증 DB에서만 마이그레이션했다. 기존 DB 사용 시 백업 후 [설치 문서](SETUP.md)의 upgrade head가 필요하다.

## 실제 실행 결과

| 검사 | 결과 |
|---|---|
| backend ruff check / format --check | 통과 |
| backend pytest | 74 통과 (추천 13개 포함) |
| frontend lint / typecheck | 통과 |
| frontend Vitest | 13 통과 |
| frontend production build | 통과. 기존 3D 공통 청크 약939KB 경고 유지 |
| Playwright 전체 | 데스크톱/모바일 26 통과 (5.4분). 최종 화면 수정 후 추천 시나리오 2개도 재통과 (33.9초) |
| 분리 SQLite Alembic | upgrade → check → downgrade(5단계) → upgrade → check 통과 |
| PostgreSQL | 전체 모델 DDL 컴파일만 통과, 실접속 미실행 |
| 합성 규칙 성능 | 99벌/37,026조합, 9,257후보 평가, 5결과, 0.463초. 로컬 1회·피드백 없음 |

초기 브라우저 실행에서 선택 항목의 접근성 이름 문제와 테스트 status 선택자 중복을 발견했다. 명시적 select 이름과 대상 status 선택자를 수정하고 재실행했다. 기존 테스트를 삭제하거나 skip 처리하지 않았다.

추천 백엔드 검증은 취향 수정/충돌·3~5개와 부족 조합·실제 의류/중복·점수 공식/다양성·like/dislike 순위·exclude 및 해제·인증/타인 차단·권리 철회/삭제/정보 변경·이미지 no-store·실제 GLB/버전 고정·본인 마네킹·치수 동의/단위/출처/잘못된 사이즈·추천 삭제/계정 cascade를 포함한다.
최종 데스크톱·모바일 스크린샷도 확인했다. 신규 카드·동의 영역·실행 버튼·세로 배치에서 가로 넘침이 없었다. 테스트 스크린샷/DB/가중치는 Git 제외 상태다.

브라우저 신규 시나리오는 실제 API 취향 저장 → 일시적 추천 503/재시도 → 카드/이미지 → 3D 없음 → 저장·좋아요 → 실제 워커 GLB 생성 → 추천 재실행 → 기존 스튜디오 자동 장착 → 유지/교체 확인 → 옷장 저장 추천 조회/삭제를 데스크톱 및 모바일 Chromium에서 수행한다. 기존 MediaPipe/의류 AI·OCR/GLB·피팅 흐름도 전체 회귀 대상이다.

## 개인정보·권리 보호

인증/사용자 소유권/현재 권리/의류 revision·모델 UUID 검증, 추천/취향/피드백 비공개 저장, 개별·계정 연관 삭제를 적용했다. 원시 체형 프로필/사진은 추천 기록에 저장하지 않는다. 명시 동의한 비교 설명도 신체 정보를 유추할 수 있으므로 동일한 비공개/삭제 대상이다. 외부 쇼핑몰 수집·브랜드 공식 제휴 표현·공개 공유·모델 판매를 추가하지 않았다. 운영 HTTPS/암호화/보관 기간/신고 운영을 완성했다고 주장하지 않는다.

## 미구현·기술적 한계·7단계 준비

- 학습형 추천·생성형 코디 이미지·외부 추천 AI는 연결하지 않았다. 규칙 기반이라는 사실을 표시한다.
- 스타일/계절/목적 집합, 색상/여유량 규칙은 초기 가설이다. 실제 사용자 만족도·패션 품질 평가와 A/B 실험은 미실행이다.
- 현재 신뢰할 수 있는 비교는 단면 의미가 명확한 가슴/허리/엉덩이와 겉옷 관계다. 키·어깨·팔·다리로 사이즈/체형 미적 적합성을 임의 추정하지 않는다. 총장은 참고값만 안내한다. 소재 물성/정밀 착용감 예측은 없다.
- 모델 없음/변경/권리 제한 시 3D 적용 차단. B 실제 고정밀 생성 엔진과 물리 피팅은 기존대로 미구현이다.
- PostgreSQL 실접속·운영 부하·실제 Android 기기·Play 제출/정책 최신 재심사는 미실행이다. 기존 Three.Clock 폐기 예정 경고와 큰 3D 공통 청크는 남아 있다.
- 7단계에 사용할 인증된 추천·옷장 ID·저장/피드백·삭제 API와 기존 피팅 경계는 준비했다. 7단계 개발에는 착수하지 않았으며 이 보고 후 지시를 기다린다.

## 변경 파일 전체

아래에는 이번 6단계와 이전 요청의 미커밋 파일 정리를 함께 포함한다. `backend/app/models.py`는 도메인별 패키지로 분리했고 기존 import 호환을 유지한다. 피팅 관련 파일은 features/fitting으로 이동했다.

- `AGENTS.md`
- `AI_LICENSE_AUDIT.md`
- `PLAY_STORE_CHECKLIST.md`
- `PRIVACY_DESIGN.md`
- `PROJECT_PLAN.md`
- `README.md`
- `TECHNICAL_RISKS.md`
- `backend/app/ai/__init__.py`
- `backend/app/ai/garment_analysis.py`
- `backend/app/api/v1/recommendations.py`
- `backend/app/generation_worker.py`
- `backend/app/main.py`
- `backend/app/models.py`
- `backend/app/models/__init__.py`
- `backend/app/models/base.py`
- `backend/app/models/fittings.py`
- `backend/app/models/garments.py`
- `backend/app/models/generation.py`
- `backend/app/models/recommendations.py`
- `backend/app/models/reports.py`
- `backend/app/models/users.py`
- `backend/app/schemas/recommendations.py`
- `backend/app/services/garment_ai.py`
- `backend/app/services/recommendation_rules.py`
- `backend/app/services/recommendations.py`
- `backend/app/workers/__init__.py`
- `backend/app/workers/generation.py`
- `backend/migrations/versions/e61f3b8c1004_recommendations.py`
- `backend/tests/test_recommendations.py`
- `docs/API.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `docs/PHASE6_DESIGN.md`
- `docs/SETUP.md`
- `docs/TASKS.md`
- `docs/VERIFICATION_PHASE6.md`
- `frontend/e2e/recommendations.spec.ts`
- `frontend/src/api/recommendations.ts`
- `frontend/src/features/fitting/FittingViewport.tsx`
- `frontend/src/features/fitting/OutfitLibrary.tsx`
- `frontend/src/features/fitting/fitting.test.ts`
- `frontend/src/features/fitting/fitting.ts`
- `frontend/src/features/fitting/fittingAssets.ts`
- `frontend/src/features/fitting/studio.css`
- `frontend/src/features/garments/OutfitLibrary.tsx`
- `frontend/src/features/mannequin/FittingViewport.tsx`
- `frontend/src/features/mannequin/fitting.test.ts`
- `frontend/src/features/mannequin/fitting.ts`
- `frontend/src/features/mannequin/fittingAssets.ts`
- `frontend/src/features/recommendations/RecommendationCards.tsx`
- `frontend/src/features/recommendations/RecommendationWorkspace.tsx`
- `frontend/src/features/recommendations/recommendations.css`
- `frontend/src/features/recommendations/types.ts`
- `frontend/src/routes/ClosetPage.tsx`
- `frontend/src/routes/Dashboard.tsx`
- `frontend/src/routes/RecommendPage.tsx`
- `frontend/src/routes/SettingsPage.tsx`
- `frontend/src/routes/StudioPage.tsx`
- `frontend/src/routes/studio.css`
- `frontend/src/types/fitting.ts`
