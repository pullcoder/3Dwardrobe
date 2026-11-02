# StyleFit AI

사용자가 업로드한 옷과 체형 정보에서 시작하는 개인화 AI 스타일링 플랫폼.
현재는 **3단계: 의류 자동 분류·배경 제거·한글/영문 OCR·비공개 옷장 등록**을 제공한다.
사진/수동 체형을 따로 편집하며 탭 저장과 선택적 암호화 기기 저장을 제공한다.
기존 MediaPipe 체형 분석과 3D 마네킹을 유지한다. 의류 3D 복원·가상 피팅은 미구현이다.

## 실행

Python 3.12, Node 24에서 검증한다. 저장소 루트에서:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -r backend/requirements.lock.txt
cd backend
cd ocr
npm ci
cd ..
.venv/Scripts/python scripts/prepare_models.py
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

새 터미널:

```powershell
cd frontend
npm ci
npm run dev
```

최초 `npm run dev`/`npm run build`는 고정 URL에서 Pose Full v1 가중치와 설치된 SDK의 WASM을 준비한다.
가중치 SHA-256을 검사하고 앱과 같은 출처에서 제공한다. 사진 분석 중 외부 CDN·AI 서버를 호출하지 않는다.
Worker의 외부 연결 차단 CSP는 Vite 개발/미리보기 서버에 적용되어 있다. 정적 배포 시에도 같은 헤더가 필요하다.
체형은 기본적으로 메모리만 사용한다. 보관함 이름과 12자 이상 암호로 명시적으로 선택한 경우만 이 기기에 암호화 저장한다.

웹: http://127.0.0.1:5173 / API 문서: http://127.0.0.1:8000/docs
환경변수 없이 로컬 SQLite 개발 DB로 실행한다. PostgreSQL은 `DATABASE_URL`로 선택하며 현재 머신에서 실접속 테스트는 하지 못했다. Redis는 미사용이다.
의류 등록 화면에서 로컬 계정을 만들고 권리·분석 안내에 동의한 뒤 AI 분석을 시작한다. 앞면 필수, 뒷면/표 사진 선택이다.
서버 분석 사진은 요청 메모리만 사용한다. 별도 저장 동의와 저장 버튼을 누르면 원본/누끼/분석/수정 정보를 본인 비공개 옷장에 보관한다. 계정/의류 삭제 기능이 있다.
첫 모델 다운로드는 약 1GB다. 추론은 로컬 CPU에서 하며 합성 의류·한글 라벨 테스트에서 오인식/미확인도 발생한다. 모든 결과를 확인하고 수정해야 한다.

## 문서

- [전체 개발 계획](PROJECT_PLAN.md)
- [AI 모델 라이선스 감사](AI_LICENSE_AUDIT.md)
- [개인정보 처리 설계](PRIVACY_DESIGN.md)
- [Google Play 체크리스트](PLAY_STORE_CHECKLIST.md)
- [기술 실현 가능성과 위험](TECHNICAL_RISKS.md)
- [설치·테스트](docs/SETUP.md), [API](docs/API.md), [아키텍처](docs/ARCHITECTURE.md)
- [단계 상태](docs/TASKS.md), [결정 기록](docs/DECISIONS.md), [코딩 규칙](docs/CONVENTIONS.md), [Git](docs/GIT_GUIDE.md)
- [2단계 검증·한계·파일 목록](docs/VERIFICATION_PHASE2.md)
- [3단계 검증·한계·파일 목록](docs/VERIFICATION_PHASE3.md)

과거 CLOSET-VERSE 문서는 [docs/archive](docs/archive)에 보존하며 현재 구현 기준으로 사용하지 않는다.
현재 버전은 loopback 전용 개발 미리보기이며 배포·Play 출시용 빌드가 아니다.
