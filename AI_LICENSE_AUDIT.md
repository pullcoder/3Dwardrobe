# AI 모델 라이선스 검토

검토일: 2026-11-03. **도입: MediaPipe Pose Full v1, OpenCLIP ViT-B-32 LAION-2B, SAM ViT-B, Tesseract kor+eng.** 이 감사는 라이선스 근거와 개발 검증 기록이며 서비스의 상업 출시 승인이 아니다. 나머지 항목은 후보 조사다.
코드와 가중치, 보조 모델·렌더러, 배포 지역, API 약관은 각각 검토한다.
미확인 항목은 도입 전에 해소하며 버전/커밋/다운로드 URL/SHA-256과 LICENSE/NOTICE 사본을 보관한다.

## 후보별 감사

| 용도·후보 | 공식 근거 | 코드 / 가중치 | 상업 이용·의무 | 미확인·판정 |
|---|---|---|---|---|
| 포즈: MediaPipe Pose Landmarker Full float16 v1 | [가이드](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker), [모델 카드](https://storage.googleapis.com/mediapipe-assets/Model%20Card%20BlazePose%20GHUM%203D.pdf), [Google 담당자 명시](https://github.com/google-ai-edge/mediapipe/issues/6306) | SDK 0.10.35·모델 Apache-2.0 | 상업 이용 허용, 라이선스·저작권·변경 고지 유지 | 2단계 기기 내 분석 도입. 버전·가중치 해시는 아래 기록. 의류/얼굴 복원 모델로 사용하지 않음 |
| 누끼: SAM ViT-B (`sam_vit_b_01ec64.pth`) | [공식 저장소와 체크포인트](https://github.com/facebookresearch/segment-anything) | 코드·모델 Apache-2.0 | 상업 이용 가능, 고지·변경 사항 표시 의무 준수 | 3단계 실제 도입. 중앙 포인트, CPU. 일반 물체 모델이므로 의류 정밀 윤곽 보장 없음 |
| 누끼: BRIA RMBG-2.0 | [모델 카드](https://huggingface.co/briaai/RMBG-2.0) | 공개 가중치 CC BY-NC 4.0 / 사용할 코드 경로 미선정 | 공개 가중치 상업 이용에는 별도 계약 필요 | 기본 모델에서 제외. BRIA API는 별도 유료 약관·보관·출력 조건 검토 전 보류 |
| VLM: Qwen2.5-VL-7B-Instruct | [모델 카드·라이선스](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct) | 모델 Apache-2.0 / 실행 코드·종속성은 선정 시 고정 | 명시 라이선스상 상업 후보, 고지 의무 | 실제 한국어 의류 태깅·GPU·양자화 품질 미측정. API 제공자의 약관은 모델 라이선스와 별도 |
| OCR: PaddleOCR PP-OCRv5 계열 | [공식 저장소](https://github.com/PaddlePaddle/PaddleOCR) | 저장소 Apache-2.0 / 개별 검출·인식 가중치 버전·조건 미확인 | 코드상 상업 후보 | 한국어 사이즈표·혼용률 정확도와 선택 가중치 고지 확인 전 보류 |
| 인체: MakeHuman/MPFB 핵심 에셋 | [공식 라이선스](https://static.makehumancommunity.org/about/license.html) | 핵심 에셋 CC0 / MakeHuman AGPL, MPFB GPL | 핵심 에셋과 프로그램 코드를 구분. 상업 이용 자체와 소스 공개 의무는 별개 | 에셋 ID·내보내기 경로·서드파티 에셋 조건 미확인. 라이선스 없는 커뮤니티 에셋 사용 금지 |
| 인체: SMPL/SMPL-X | [SMPL-X 공식 사이트](https://smpl-x.is.tue.mpg.de/) | 사용할 코드·가중치 계약 미확인 | 상업 계약 확보 전 사용 금지 | 기존 저장소의 금지 유지. 다운로드·설치하지 않음 |
| Image-to-3D: TRELLIS-image-large | [공식 코드](https://github.com/microsoft/TRELLIS), [가중치](https://huggingface.co/microsoft/TRELLIS-image-large) | 주 코드·모델 MIT / 일부 하위 모듈 별도 조건 | MIT 고지 유지. 전체 추론 경로의 서브모듈 감사 필요 | 비상업 조건이 있을 수 있는 렌더러를 포함한 전체 종속성 미확인. 통째로 상업 승인하지 않음 |
| Image-to-3D: TRELLIS.2-4B | [공식 코드](https://github.com/microsoft/TRELLIS.2), [가중치](https://huggingface.co/microsoft/TRELLIS.2-4B) | 본체 MIT / 렌더링 종속성 별도 조건 | 고지 유지·모든 포함 종속성 감사 필요 | 다중 이미지 경로·의류 품질·실제 배포 GPU 미확인. 성능 검증 후보 |
| Image-to-3D: Hunyuan3D-2.1 | [공식 라이선스 원문](https://huggingface.co/tencent/Hunyuan3D-2.1/blob/main/LICENSE) | Tencent Hunyuan 3D 2.1 Community License | 한국·영국·EU가 해당 라이선스 적용 지역에서 제외됨 | 한국 서비스에 이 공개 라이선스로 도입하지 않음. 별도 허가 없이 API 우회도 허용된다고 가정하지 않음 |

## 3D 기술 비교

| 후보 | 품질·디자인 보존 | 다중 사진 | 파일 출력 | 공식 GPU 요구 | API | 상업 판단 |
|---|---|---|---|---|---|---|
| TRELLIS-image-large | 일반 물체 생성. 의류 로고·앞뒤 정합성 실측 없음 | 공식 예제 있음. 모든 입력의 일관성 보장 아님 | 메시·GLB 내보내기 경로 | NVIDIA VRAM 16GB 이상, Linux 검증 | 자체 서버 가능, 상용 관리형 약관 미확인 | 본체 MIT, 종속성 감사 후 판단 |
| TRELLIS.2-4B | PBR 지원 일반 물체 생성. 의류 복원 정확도 미측정 | 통합 앞/뒤 조건 지원 미확인 | 텍스처 메시·GLB 경로 | NVIDIA VRAM 24GB 이상, Linux 검증 | 자체 서버 가능, 관리형 약관 미확인 | 본체 MIT, 종속성 감사 후 판단 |
| Hunyuan3D-2.1 | 의류 비교 실험 안 함 | 적용할 경로 미확인 | 메시 생성, 실제 통합 미검증 | 미확인 | 제공자별 별도 약관 | 한국 공개 라이선스 경로 제외 |

표는 공식 설명과 미검증 영역을 구분한 사전 비교다. 후보를 실행하거나 벤치마크하지 않았다.
공식 모델에 API를 씌웠다고 출력물 권리·개인정보·지역 제한이 해결되지는 않는다.
사진에 있는 로고와 디자인의 권리는 사용자 업로드 권리와 함께 별도 검토해야 한다.

## 3단계 실제 도입 기록

| 구성 | 고정 버전·공식 근거 | 코드 / 가중치 | 적용·조건 |
|---|---|---|---|
| OpenCLIP ViT-B-32 LAION-2B s34B b79K | `open_clip_torch==3.3.0`, [공식 코드 LICENSE](https://github.com/mlfoundations/open_clip/blob/main/LICENSE), [모델 소유자 카드](https://huggingface.co/laion/CLIP-ViT-B-32-laion2B-s34B-b79K/blob/1a25a446712ba5ee05982a381eed697ef9b435cf/README.md) | 코드 MIT, 가중치 카드 YAML에 `license: mit` 명시 | MIT 저작권·라이선스 유지. 모델 카드의 연구 목적·미평가 배포 범위 밖 안내를 기록한다. 상업권 허용과 제품 품질/안전 배포 적합성은 별개이며 출시 전 실제 의류 데이터셋 평가 필요 |
| Meta SAM ViT-B 01ec64 | 코드 `dca509fe793f601edb92606367a655c15ac00fdf`, [공식 모델 라이선스 명시](https://github.com/facebookresearch/segment-anything#license) | 코드·모델 Apache-2.0 | 라이선스 사본 유지, 자체 프롬프트/투명 PNG 변환 코드는 별도 작성. 원본 모델 수정·학습 없음. SA-1B 데이터셋은 다운로드/사용하지 않음 |
| Tesseract.js / core | 7.0.0 / 7.0.0, npm lock integrity, [JS](https://github.com/naptha/tesseract.js/blob/master/LICENSE.md), [core](https://github.com/naptha/tesseract.js-core/blob/master/LICENSE) | Apache-2.0 | Node worker의 WASM OCR. 이미지 stdin, 임시 파일·언어 캐시 쓰기 없음. Node 24는 OCR 실행 의존성이므로 서버 설치에 포함 |
| tessdata_fast kor+eng | `87416418657359cb625c412a48b6e1d6d41c29bd`, [공식 학습 데이터 라이선스](https://github.com/tesseract-ocr/tessdata_fast/blob/87416418657359cb625c412a48b6e1d6d41c29bd/LICENSE) | Apache-2.0 | 한글·영문 LSTM 학습 데이터. 모델 버전·SHA-256 고정, 모델 첫 사용 때 무결성 확인 |

- 정확한 URL·SHA-256은 [backend/model_manifest.json](backend/model_manifest.json). 준비 스크립트와 런타임이 같은 기록으로 검증한다. 가중치는 Git 제외다.
- OpenCLIP SHA-256: `ac4f8c4b88af6d963118cbf40ad93176d092abbedfcb752601ae1866352656e6`, 모델 커밋 `1a25a446712ba5ee05982a381eed697ef9b435cf`, `open_clip_model.safetensors`.
- 원본 OpenAI CLIP는 코드 MIT만으로 외부 가중치 조건을 확정하지 않는다. [미해결 공식 저장소 질의](https://github.com/openai/CLIP/issues/203)를 추가 확인해 최종 파이프라인에서 제외했다. 준비 스크립트도 원본 체크포인트를 받지 않는다. OpenAI MIT 사본은 OpenCLIP의 파생 코드/토크나이저 고지를 위해 유지한다.
- SAM SHA-256: `ec2df62732614e57411cdcf32a23ffdf28910380d03139ee0f4fcbe91eb8c912`.
- OCR kor/eng 해시와 공식 고정 커밋 URL도 manifest에 기록했다. 공식 패키지 LICENSE와 모델 라이선스 사본은 `docs/licenses/`에 보관한다.
- 외부 추론 API·API 키·API 출력물 약관은 해당 없음. 모델 준비 단계에서만 공식 배포처에 연결하며 사용자 사진은 전송하지 않는다.
- 모든 모델은 로컬 CPU 추론만 수행하며 학습·가중치 갱신을 하지 않는다. 생성형 의류/이미지 모델은 아직 없다.
- 기반 종속성: PyTorch 2.15.0+cpu·torchvision 0.29.2+cpu (BSD 계열), NumPy (BSD), ftfy (MIT), SQLAlchemy/Alembic (MIT), psycopg (LGPL, 동적 사용). 고정 버전은 `backend/requirements.lock.txt`에 기록한다. psycopg 상업 사용과 바이너리 재배포의 고지/소스 제공 의무는 구분하고, Android에 서버 Python 바이너리를 포함하지 않는다.
- 공개 가중치가 입력 사진·로고·의류 디자인의 권리를 부여하지 않는다. 모델 정확도, 학습 데이터/출력 관련 분쟁 위험, 전체 바이너리 포함 고지 최종 검토는 출시 전 항목으로 남긴다.

## 2단계 실제 도입 기록

- SDK: `@mediapipe/tasks-vision@0.10.35`, npm lock integrity로 고정. 공식 패키지 메타데이터 Apache-2.0.
- 가중치: `pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task`.
- 공식 URL: `https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task`.
- SHA-256: `5134a3aad27a58b93da0088d431f366da362b44e3ccfbe3462b3827a839011b1`, 크기 9,398,198바이트.
- [Google 담당자의 버전 지정 번들 Apache-2.0 설명](https://github.com/google-ai-edge/mediapipe/issues/6306)과 모델 카드의 Apache-2.0 표시를 확인했다.
- SDK와 모델을 수정하지 않고 직접 작성한 Worker·품질 검사·길이 추정 코드를 연결했다. 모델 재학습 없음.
- 코드 라이선스 사본은 `docs/licenses/mediapipe-Apache-2.0.txt`, 배포 고지는 `frontend/public/third-party-notices.txt`에 포함했다.
- 모델은 SDK 추론용 관절 추정에만 사용한다. 별도 GHUM/SMPL 인체 메시나 가중치는 내려받거나 사용하지 않는다.
- 실행 API 계약: 외부 추론 서비스 없음. 브라우저가 같은 출처에서 모델/WASM을 내려받아 CPU Worker로 실행한다.
- 출력: 관절·상대 길이. 결과만으로 입력 사진이나 의류 디자인 권리가 확보되는 것은 아니다. 의류 생성 출력은 없다.
- SDK 사전 컴파일 WASM의 모든 내장 서드파티 고지/소스 빌드 provenance는 출시 전 추가 재검토 항목이다. 로컬 개발 검증과 Play 배포 허가를 동일시하지 않는다.
- Face Landmarker는 타입 기반 주입 어댑터만 마련했다. 얼굴 가중치 버전·라이선스 확인이 아직 없어 실제 얼굴 추론은 도입하지 않았다.
- 3D 렌더링은 Three.js `0.187.0`·React Three Fiber `9.8.2`, MIT. R3F는 [해당 태그의 LICENSE](https://github.com/pmndrs/react-three-fiber/blob/v9.8.2/LICENSE) 사본을 `docs/licenses/react-three-fiber-MIT.txt`에 보존했다.
- 인체는 직접 작성한 파라미터 기하 구조다. 외부 인체 생성 모델/메시 자산은 사용하지 않았다.

## 향후 모델 도입 체크

- [ ] 정확한 코드 커밋·모델 ID·가중치 해시·변환/양자화 출처 고정
- [ ] 코드/가중치/보조 모델/렌더러의 라이선스와 NOTICE 수집
- [ ] 상업·지역·사용량·재배포·출력 제한 및 귀속 표시 확인
- [ ] API를 쓴다면 이용약관 버전, 학습 재사용 여부, 보관 기간, 처리 국가·삭제 계약 확인
- [ ] 실제 의류 테스트, GPU·지연·실패율·비용 측정
- [ ] 미확인 해소와 사용자 보고 후 도입 기록
