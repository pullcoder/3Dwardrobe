# GIT_GUIDE — Git 사용법 · 협업 흐름

> 처음 팀에서 쓰던 Git 메모(`git.md`)를 바탕으로 정리한 개선판입니다. (`git.md`는 삭제하고 이 문서로 대체)
> 핵심 원칙은 그대로: **main은 항상 최신·안정 상태, 작업은 무조건 브랜치에서.**
> 바뀐 점: main에 직접 merge 대신 **PR(Pull Request)로 합치기**, 커밋 메시지 규칙, 충돌 해결, 자주 하는 실수 대처 추가.

---

## 0. 한 번만 하는 기본 세팅

```bash
# 저장소 받기 (처음 한 번)
git clone https://github.com/pullcoder/3Dwardrobe.git
cd 3Dwardrobe

# 내 정보 등록 (이 저장소에만 적용)
git config user.name "이름"
git config user.email "GitHub에 등록한 메일"

# 줄바꿈(LF/CRLF)은 저장소의 .gitattributes가 자동으로 맞춰줍니다. 따로 설정할 필요 없음.

# 기본 브랜치 확인 → main 이어야 함
git branch -a
```

> `git init`, `git remote add`는 **저장소를 처음 만드는 사람만** 한다. 팀원은 `git clone`이면 끝.

---

## 1. 브랜치 이름 규칙

`종류/짧은-설명` (영어 소문자, 단어는 `-`로 연결)

| 종류 | 언제 | 예시 |
|------|------|------|
| `feature/` | 새 기능 | `feature/closet-upload` |
| `fix/` | 버그 수정 | `fix/avatar-rotation` |
| `docs/` | 문서만 수정 | `docs/api-closet` |
| `refactor/` | 동작 변화 없는 코드 정리 | `refactor/body-service` |
| `chore/` | 설정·패키지·빌드 | `chore/add-ruff` |

- 한 브랜치 = 한 작업. 끝나면 지운다.
- `TASKS.md`의 할 일 ID를 붙여도 좋다: `feature/T1-3-closet-upload`

---

## 2. 매일 하는 작업 흐름 (가장 중요)

```bash
# ① main 최신화
git checkout main
git pull origin main

# ② 작업 브랜치 만들기 (무조건!)
git checkout -b feature/closet-upload

# ③ 작업 → 중간중간 커밋
git status                       # 무엇이 바뀌었는지 먼저 확인
git add backend/app/api/v1/closet.py frontend/src/features/closet/
git commit -m "feat(closet): 옷 사진 업로드 API 추가"

# ④ 원격에 올리기
git push -u origin feature/closet-upload   # 처음 한 번만 -u, 이후엔 git push

# ⑤ GitHub에서 Pull Request 만들기 → 리뷰 → Merge
```

### 왜 `git add .` 대신 파일을 지정하나요?
`git add .`는 `.env`, 테스트용 사진, 임시 파일까지 올릴 수 있습니다. 쓰더라도 **반드시 `git status`로 확인한 뒤** 사용하세요.

---

## 3. 커밋 메시지 규칙

```
<종류>(<범위>): <무엇을 했는지 한 줄, 한국어 OK>

(선택) 왜 바꿨는지, 참고 사항
```

| 종류 | 뜻 |
|------|----|
| `feat` | 새 기능 |
| `fix` | 버그 수정 |
| `docs` | 문서 |
| `style` | 포맷·세미콜론 등 (동작 변화 없음) |
| `refactor` | 리팩터링 |
| `test` | 테스트 |
| `chore` | 설정·패키지 |

범위 예시: `body`, `closet`, `fitting`, `recommend`, `partner`, `auth`, `worker`, `frontend`, `backend`, `db`, `docs`

```bash
# 좋은 예
git commit -m "feat(body): MediaPipe 랜드마크로 어깨너비 추정"
git commit -m "fix(fitting): 아바타 360° 회전 시 겉옷이 사라지는 문제 수정"
git commit -m "docs(api): match-score 응답 예시 추가"

# 나쁜 예
git commit -m ""          # 빈 메시지
git commit -m "수정"       # 무엇을?
git commit -m "asdf"
```

---

## 4. 작업 중에 main이 바뀌었을 때 (내 브랜치 최신화)

다른 사람 PR이 먼저 합쳐졌다면, PR 올리기 전에 내 브랜치에 main을 반영합니다.

```bash
git checkout main
git pull origin main
git checkout feature/closet-upload
git merge main            # 충돌 나면 아래 5번
git push
```

---

## 5. 충돌(Conflict) 해결

```text
  <<<<<<< HEAD
  내 브랜치 코드
  =======
  main 쪽 코드
  >>>>>>> main
```
(실제 파일에서는 표시가 줄 맨 앞에 붙어 나옵니다. 이 문서에서는 에디터가 진짜 충돌로 착각하지 않도록 두 칸 들여 썼어요.)

1. VS Code에서 파일 열기 → "Accept Current / Incoming / Both" 중 선택하거나 직접 수정
2. `<<<<<<<`, `=======`, `>>>>>>>` 표시를 모두 지운다
3. 저장 후:
```bash
git add 충돌난파일
git commit                 # 메시지는 기본값 그대로 OK
git push
```

헷갈리면 **멈추고 되돌린 뒤** 팀에 물어보세요:
```bash
git merge --abort
```

---

## 6. Pull Request(PR) 규칙

- **main에 직접 push 금지.** 모든 변경은 PR로 합친다. (GitHub 설정 → Branches → main 보호 규칙 권장)
- PR 제목은 커밋 메시지 형식과 같게: `feat(closet): 옷 사진 업로드`
- PR 본문에 적을 것:
  - 무엇을 / 왜 바꿨는지
  - 확인 방법 (스크린샷, 실행 명령)
  - 관련 할 일: `TASKS.md`의 ID
- 리뷰어 **1명 이상 승인** 후 Merge. Merge 방식은 **Squash and merge** 권장 (main 기록이 깔끔해짐).
- Merge 후 브랜치 삭제:
```bash
git checkout main
git pull origin main
git branch -d feature/closet-upload
```

> 급하게 로컬에서 직접 merge해야 할 때(예전 git.md 방식)는 팀에 먼저 알리고 진행합니다.
> ```bash
> git checkout main && git pull origin main
> git merge feature/브랜치이름
> git push origin main
> ```

---

## 7. 자주 하는 실수와 해결

| 상황 | 해결 |
|------|------|
| 커밋 메시지 오타 (아직 push 전) | `git commit --amend -m "새 메시지"` |
| 파일을 빼먹고 커밋 (push 전) | `git add 파일 && git commit --amend --no-edit` |
| `add`를 취소하고 싶다 | `git restore --staged 파일` |
| 수정한 내용을 버리고 싶다 | `git restore 파일` (⚠️ 복구 불가) |
| main에서 작업해버렸다 (커밋 전) | `git switch -c feature/새브랜치` → 변경 내용이 그대로 따라옴 |
| 작업 중인데 급히 브랜치를 바꿔야 한다 | `git stash` → 브랜치 이동 → 돌아와서 `git stash pop` |
| `.env`를 커밋해버렸다 | `git rm --cached .env` 후 커밋, **키는 즉시 재발급** (기록에 남아 있음) |
| pull 했더니 에디터(vim) 화면이 뜬다 | `:wq` 입력 후 Enter (merge 메시지 저장) |
| push가 거절됨 (rejected) | 원격이 더 최신 → `git pull origin 브랜치` 후 다시 push |

**하지 말 것**: `git push --force` (특히 main), 남의 브랜치에 push, 확인 없이 `git reset --hard`

---

## 8. 명령어 요약표

| 하고 싶은 것 | 명령 |
|-------------|------|
| 상태 보기 | `git status` |
| 변경 내용 보기 | `git diff` |
| 기록 보기 | `git log --oneline --graph -10` |
| 브랜치 목록 | `git branch -a` |
| 브랜치 이동 | `git checkout 이름` (또는 `git switch 이름`) |
| 새 브랜치 | `git checkout -b 이름` |
| 최신 받기 | `git pull origin main` |
| 올리기 | `git push` |
| merge 취소 | `git merge --abort` |
