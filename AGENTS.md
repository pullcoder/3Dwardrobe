# AGENTS.md — AI 코딩 도구 공통 지시서

이 파일은 Codex 등 AI 코딩 에이전트가 이 저장소에서 작업할 때 따르는 **공통 규칙**입니다.
Claude Code는 `CLAUDE.md`에서 이 파일을 그대로 불러오므로, 공통 규칙은 **여기 한 곳에서만** 고칩니다.

## 1. 프로젝트 한 줄 요약

CLOSET-VERSE: 사진으로 체형과 옷장을 디지털화하고, 새 옷과 내 옷을 3D 아바타에 함께
입혀 보며(크로스 피팅) AI가 매칭 점수·빈자리·사이즈를 추천하는 웹 서비스.

## 2. 작업 전에 읽을 문서

| 상황 | 먼저 읽을 문서 |
|------|---------------|
| 기능을 새로 만든다 | `docs/PLAN.md`, `docs/TASKS.md` |
| 파일 위치·구조를 정한다 | `docs/ARCHITECTURE.md` |
| API를 만들거나 호출한다 | `docs/API.md` |
| 코드를 쓴다 (항상) | `docs/CONVENTIONS.md` |
| 커밋·브랜치·PR | `docs/GIT_GUIDE.md` |
| 설치·실행 | `docs/SETUP.md` |
| "왜 이렇게 했지?" | `docs/DECISIONS.md` |

문서와 코드가 다르면 **코드를 문서에 맞추지 말고 먼저 사용자에게 알린다.**

## 3. 기술 스택 (임의로 바꾸지 않기)

- Frontend: React + TypeScript (Vite), Tailwind CSS, Three.js + React Three Fiber
- Backend: Python 3.11, FastAPI, SQLAlchemy 2.x, Pydantic v2, Alembic
- AI: MediaPipe Pose, SMPL 계열, RMBG/SAM + OpenCV, VLM, OCR
- DB: PostgreSQL

새 라이브러리 추가, 스택 변경, 폴더 구조 변경은 **사용자 확인 후** 진행하고 `docs/DECISIONS.md`에 기록한다.

## 4. 반드시 지킬 규칙

1. **작은 단위로 작업한다.** 한 번에 한 기능·한 버그. 요청과 관계없는 파일은 고치지 않는다.
2. **비밀 정보 금지.** API 키, 비밀번호, 토큰을 코드·문서·커밋에 넣지 않는다. `.env`만 사용하고, 새 변수는 `.env.example`에 빈 값으로 추가한다.
3. **개인정보.** 얼굴·전신 사진은 분석 후 원본 삭제가 기본값이다. 사진·체형 데이터를 로그에 남기지 않는다.
4. **데이터 수집.** 외부 사이트 크롤링 코드를 작성하지 않는다. 사용자가 올린 사진과 제휴몰 제공 데이터만 쓴다.
5. **AI 모델 라이선스.** 새 모델·가중치를 추가할 때 상업적 이용 가능 여부를 확인하고 `docs/DECISIONS.md`에 적는다. (SMPL은 상업 라이선스 별도)
6. **API를 바꾸면 `docs/API.md`도 같이 고친다.** DB 스키마를 바꾸면 Alembic 마이그레이션을 만들고 `docs/ARCHITECTURE.md`를 갱신한다.
7. **main 브랜치에 직접 커밋·푸시하지 않는다.** `feature/...` 등 브랜치에서 작업한다. (`docs/GIT_GUIDE.md`)
8. **주석과 문서는 한국어**, 코드 식별자(변수·함수·파일명)는 영어.

## 5. 완료 전 확인 (Definition of Done)

```bash
# backend/
ruff check . && ruff format --check . && pytest

# frontend/
npm run lint && npm run typecheck && npm run build
```

- 위 명령이 통과하지 못하면 "완료"라고 하지 말고 실패 내용을 그대로 보고한다.
- 아직 해당 명령이 설정되지 않았다면, 실행하지 못했다고 명시한다.
- 작업 끝에 **변경한 파일 목록과 이유**를 짧게 요약한다.

## 6. 하지 말 것

- `.env`, `storage/`, 모델 가중치(`*.pt`, `*.pkl`, `*.onnx`) 커밋
- 테스트를 지우거나 건너뛰게(skip) 만들어 통과시키기
- `git push --force`, `git reset --hard` 등 되돌리기 어려운 명령을 사용자 확인 없이 실행
- 사용자가 요청하지 않은 대규모 리팩터링·포맷 변경
