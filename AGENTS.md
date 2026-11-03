# StyleFit AI — 공통 개발 지시서

사용자의 통합 개발 프롬프트 v2.0이 이전 CLOSET-VERSE 계획보다 우선한다.
`PROJECT_PLAN.md`가 현재 범위 기준이며 과거 문서는 `docs/archive/`에 보존한다.
현재 허용 범위는 **5단계 개인화 시각적 3D 피팅·레이어링·코디 저장까지**다. 기존 1~4단계를 유지한다. 물리 시뮬레이션/실제 착용감으로 과장하지 않는다. B는 검증된 권한과 호환 모델 계약이 필요하며 실제 B 생성 엔진은 여전히 비활성화다. 보고 후 지시를 기다리고 6단계 추천에 착수하지 않는다.

## 작업 전에

- 기획·단계: `PROJECT_PLAN.md`, `docs/TASKS.md`
- 모델 도입: `AI_LICENSE_AUDIT.md`, `TECHNICAL_RISKS.md`
- 개인정보·출시: `PRIVACY_DESIGN.md`, `PLAY_STORE_CHECKLIST.md`
- 코드: `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/CONVENTIONS.md`
- 설치·협업: `docs/SETUP.md`, `docs/GIT_GUIDE.md`, `docs/DECISIONS.md`
- 문서와 실제 코드가 다르면 먼저 사용자에게 알린다. 구현 상태를 과장하지 않는다.

## 스택·범위

React + TypeScript strict + Vite + Tailwind, FastAPI + Pydantic, PostgreSQL.
현재 개발 환경은 Python 3.12 / Node 24. Three.js/R3F는 3D 단계, Android는 출시 준비 단계다.
기기 내 MediaPipe를 우선 검토하고 서버 AI는 향후 Celery/Redis 워커로 분리한다.
구체 라이브러리·모델의 임의 변경은 피한다. 사용자 요청이 이미 승인한 구성 작업은 진행하고 결정 기록을 남긴다.

## 필수 규칙

1. 크롤링·외부 쇼핑몰 수집 금지. 사용자가 직접 업로드한 의류만 사용한다.
2. 상업 이용이 허용된 코드·가중치·API만 도입. 버전과 라이선스·종속성·출력 조건을 감사한다.
3. 미확인 모델과 SMPL 계열은 계약·조건 확인 전 설치하지 않는다. 라이선스 문서를 갱신한다.
4. 사진·치수·3D는 기본 비공개, 학습 재사용 금지, 사진·신체 정보를 로그에 남기지 않는다.
5. 저장 전 사진은 메모리 전용. 의류의 명시적 처리/저장 동의를 구분한다. 신체 사진은 계속 브라우저에서 처리한다. 5단계 코디 복원용 최소 체형 수치/출처는 별도 동의 및 저장 동작 시만 계정의 비공개 DB에 저장한다. 원본 신체 사진·관절/얼굴은 서버로 보내지 않는다.
6. 추정치/직접 입력/확인된 값을 구분한다. 미연결 AI·3D·신고·저장은 준비 중으로 표시한다.
7. 영구 저장·계정 기능을 열기 전 소유권·삭제·비공개 객체 접근을 구현한다.
8. 비밀·사진·가중치·테스트 실행 산출물 커밋 금지. 새 설정은 `.env.example`에 설명한다.
9. 문서·주석은 한국어, 식별자는 영어. 기능 변경 시 API·아키텍처 문서를 함께 갱신한다.
10. main 직접 커밋·푸시 금지. 기능 브랜치에서 작업하고 PR로 통합한다.
11. 요청 밖 대규모 변경, 테스트 삭제/skip으로 통과시키기, 확인 없는 강제 푸시·hard reset 금지.

## 완료 전 확인

```text
backend: .venv/Scripts/python -m ruff check .
backend: .venv/Scripts/python -m ruff format --check .
backend: .venv/Scripts/python -m pytest
frontend: npm run lint
frontend: npm run typecheck
frontend: npm run build
frontend: npm test
frontend: npm run test:e2e
```

macOS/Linux의 Python은 `.venv/bin/python`을 사용한다.
미실행·실패·기술적 한계를 그대로 보고하며, 단계 종료 때 완료 기능·테스트·파일·모델/라이선스·미구현·개인정보·다음 계획을 보고한다.
