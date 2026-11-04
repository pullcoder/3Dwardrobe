# AI 모델 라이선스 검토

## 로컬 6종 의류 템플릿

사용자 2단계 요청의 반팔/긴팔/청바지/슬랙스/후드집업/재킷은 직접 작성한 로프트·셸·변형 코드다. 외부 의류 모델·사진 자산·AI 가중치를 도입하지 않았다. 기존 Three.js/R3F와 프로젝트 원본 마네킹만 재사용하며 기존 MIT 고지를 유지한다. 신규 외부 라이선스 도입은 없으며 입력/브랜드 디자인 권리를 대신 판단하지 않는다. [구현 범위](docs/CLOTHING_TEMPLATE_WORKBENCH.md).

## 티셔츠·바지 앞뒤 사진 외형 확장

사용자 요청으로 기존 Pillow/NumPy와 자체 GLB 패널의 B 사진 투영을 확장했다. 신규 AI 모델·외부 자산·가중치·라이브러리·외부 API는 없다. 보관된 본인 소유 사진과 세 권한 verified가 필요하며 코드가 증빙 검토를 대신하지 않는다. 개발 검증 입력은 직접 그린 합성 색상 표식이고 실제 사용자 사진을 재사용하지 않았다. 기존 라이선스 사본을 유지한다. [사진 외형 구현](docs/PHOTO_APPEARANCE.md).

## 2026-11-04 TripoSR / TRELLIS.2 재검토

설치·추론 없이 공식 원문을 확인했다. 사본·URL·SHA-256은 `docs/licenses/generation-engines/sources.json`. main URL 문서 해시는 확인 시점 증거이며 배포 바이너리 커밋 고정을 대신하지 않는다. [도입 상태](docs/AI_GENERATION_ENGINES.md)를 함께 따른다.

| 구성 | 근거·조건 | 결정 |
|---|---|---|
| TripoSR 본체/가중치 | [공식 코드](https://github.com/VAST-AI-Research/TripoSR), [모델 카드](https://huggingface.co/stabilityai/TripoSR): MIT, 저작권·허가문 유지. 카드의 Objaverse CC-BY 선별 학습 자료 설명은 개별 출력물의 권리를 보증하지 않음 | 본체는 상업 후보, 전체 경로 보류 |
| torchmcubes | [공식 LICENSE](https://github.com/tatsy/torchmcubes/blob/master/LICENSE): MPL-2.0. 상업 사용과 배포 시 covered source/고지 의무 구분 | requirements가 Git HEAD라 버전·바이너리·내장 코드 감사 필요 |
| TripoSR 기타 | upstream requirements의 OmegaConf/Pillow/einops/transformers/trimesh/rembg/HF hub/imageio·ffmpeg/gradio/xatlas/moderngl. 직접 어댑터는 기존 SAM 누끼·정점 색으로 rembg와 baking을 호출하지 않음 | 고정 설치환경이 없어 전이 버전·내장 코드·보조 가중치·FFmpeg 조건 미확인. 본체 MIT만으로 승인하지 않음 |
| TRELLIS.2 본체/가중치 | [코드](https://github.com/microsoft/TRELLIS.2/blob/main/LICENSE), [모델 카드](https://huggingface.co/microsoft/TRELLIS.2-4B): MIT. 연구 재현을 돕기 위한 공개 고지를 MIT의 비상업 제한으로 오해하지 않음 | 본체와 NVIDIA 조건을 분리 |
| nvdiffrast v0.4.0 | [setup 지정 버전 LICENSE](https://github.com/NVlabs/nvdiffrast/blob/v0.4.0/LICENSE.txt) 3.3: NVIDIA 외에는 연구/평가 및 직접·간접 금전 이득 없는 용도. 배포 시 전체 라이선스·고지 유지 | 공개 조건으로 상용 활성화 금지 |
| nvdiffrec | [공식 LICENSE](https://github.com/NVlabs/nvdiffrec/blob/main/LICENSE.txt) 3.3: 비상업 연구/평가, NVIDIA 예외. 사본/고지·파생물 조건 | 상용 비활성화. 영상 생략만으로 전체 GLB 경로에서 제거됐다고 가정하지 않음 |
| TRELLIS 기타 | CUDA/PyTorch/FlashAttention/CuMesh/O-Voxel/FlexGEMM/utils3d/transformers·보조 비전 모델 등 | 정확한 배포 묶음의 전체 감사 미완료, 설치/자동 다운로드 없음 |

현재 두 AI 엔진은 모든 환경에서 비활성화한다. 환경변수 우회는 없다. 상업 허가 또는 종속 경로 변경 후 재감사와 실행 검증이 필요하다. 모델 라이선스는 의류 사진/로고/디자인 권리를 대신하지 않는다.

## 5단계 실제 사용

5단계는 기존 프로젝트의 직접 제작 마네킹·A 의류 메시, 기존 Three.js/R3F(MIT)·GLTFLoader·OrbitControls·Raycaster를 재사용한다. 새 학습 모델·가중치·외부 의류 자산·시뮬레이션 엔진·외부 API를 도입하지 않았다. 부위별 정점 변형, 신체 타원/캡슐 근사, 레이어 여유와 코디 저장 코드는 직접 작성했다. 기존 고지/라이선스 사본을 유지한다.
원본 사진 텍스처/보호 그래픽 재현 경로를 추가하지 않으며 A의 입력 권한 및 법적 안전성 한계는 그대로다. B는 서버의 세 권한 verified와 공통 부위 계약을 모두 요구한다. 실제 B 생성 엔진/고정밀 상업 모델은 여전히 미도입이다. B 호환 검사는 실제 B 생성의 라이선스/품질 승인으로 해석하지 않는다.

검토일: 2026-11-03. **도입: MediaPipe Pose Full v1, OpenCLIP ViT-B-32 LAION-2B, SAM ViT-B, Tesseract kor+eng.** 이 감사는 라이선스 근거와 개발 검증 기록이며 서비스의 상업 출시 승인이 아니다. 나머지 항목은 후보 조사다.

## 4단계 실제 사용 및 B 보류

- A의 9종 의류 표면·단색 재질은 `backend/app/services/garment_mesh.py`에서 직접 작성한 파라미터 기하다. 외부 의류 메시/사진 텍스처/학습 가중치/생성 API를 사용하지 않는다. 별도 외부 에셋의 비상업·귀속·재배포 제한을 가져오지 않으며 저장소 권리자의 배포 조건을 유지한다. 프로젝트 직접 제작 자산이라는 사실이 입력 사진·의류 디자인의 권리를 대신하지 않는다.
- Python 표준 라이브러리 struct/json/math로 GLB를 작성한다. [Khronos glTF 2.0 명세](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html)의 형식에 맞춘 자체 구현이며 Khronos 샘플 메시·텍스처를 복사하지 않았다.
- 뷰어는 이미 도입한 Three.js/R3F(MIT)와 Three.js의 [GLTFLoader](https://threejs.org/docs/pages/GLTFLoader)를 재사용한다. 새 런타임 라이브러리/신규 신경망 모델/가중치는 없다. 기존 MIT 고지 사본을 유지한다.
- A의 학습 데이터·가중치 라이선스·외부 API 약관은 신규 해당 없음. 입력은 기존 3단계 분석/사용자 수정이며 사진은 생성기에 전달하지 않는다. 결과물의 상업적 이용 권한은 사진/보호 디자인/결과 이용 범위별로 별도 검토한다.

B는 다음 후보를 공식 문서로 재검토했지만 설치·추론·상업 도입하지 않았다.

| 후보 | 코드/가중치·다중 입력·출력 | GPU/속도/비용·미확인 |
|---|---|---|
| [TRELLIS](https://github.com/microsoft/TRELLIS) | 주 코드/모델 MIT, 일부 렌더러/Flexicubes는 별도 라이선스. 다중 이미지 예제가 있으나 모든 입력에 최적이라는 보장 없음. GLB 내보내기 예제 존재 | 공식 최소 NVIDIA 16GB, Linux 중심. 의류 전후면 일관성·로고·봉제/출력 권리/전체 종속성 경로 미검증. 로컬 실제 생성 속도·VRAM·건당 비용 미측정, 외부 API 계약 없음 |
| [TRELLIS.2](https://github.com/microsoft/TRELLIS.2) | 본체 코드/모델 MIT, nvdiffrast/nvdiffrec 별도 조건. GLB 지원, 다중 이미지 의류 복원 경로는 확인 전 | 공식 최소 NVIDIA 24GB/Linux. README 속도는 H100 결과이며 이 PC의 측정값이 아니다. 의류 품질·전체 의존성·학습 데이터/출력 관련 제한·배포 비용 미검증 |

본체 MIT 표시만으로 전체 실행 경로가 상업 승인됐다고 판정하지 않는다. 적합한 GPU/종속성 경로·의류 품질·권리 검증 운영이 확인되지 않아 B_ENGINE_AVAILABLE은 false이며 환경변수로 임의 활성화하는 기능도 없다.
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

## 6단계 추천 반영

- 새 AI 모델·가중치·외부 API·라이브러리를 도입하지 않았다. `stylefit-rules-1.0`은 프로젝트에서 작성한 순수 Python 조합·점수·다양성 규칙이다. 모델 학습·이미지 생성·외부 전송이 없다.
- 화면에 규칙 기반이라고 표시하며 기존 의류 원본/누끼만 미리보기에 사용한다. 기존 OpenCLIP/SAM/MediaPipe/Tesseract와 A 템플릿의 감사 조건을 변경하지 않는다. B 엔진은 비활성화 상태다.
- 향후 외부 추천 모델/API 도입은 코드·가중치·출력·전송·비용 조건을 별도 감사한다. 이번 단계는 새로운 외부 모델 라이선스 확인 대상이 없다.

## 4단계 GLB 긴급 복구

기존 프로젝트 직접 제작 파라미터 템플릿/표준 라이브러리 GLB writer를 그대로 사용한다. 신규 모델·가중치·상용 자산·외부 API·런타임 의존성을 도입하지 않았다. 원본 사진 픽셀/로고를 복제하지 않는 A 모드와 B 비활성 조건을 유지한다. 변경은 워커 실행·상태/실패 진단·빈 GLB 검증이다.

## 4단계 바지 품질 개선 · stylefit-pants-2.0

- 신규 AI 모델/가중치/API/외부 3D 자산/런타임 패키지 없음. 이미 감사한 Pillow/NumPy와 직접 작성한 윤곽·패널 메시·일반 체크 생성 코드를 사용한다. SAM 누끼가 저장되어 있으면 그 알파 마스크를 소비하며 새로운 SAM 모델을 도입하지 않는다.
- A: 외곽 수치만 기하에 사용한다. 체크 PNG는 원본 픽셀·로고·색상 빈도/패턴 간격을 샘플링하지 않고 등록 색상과 고정된 자체 도안으로 만든다. GLB 검증에서 자체 체크 이미지와 일치하는 경우만 A 텍스처를 허용한다. A가 모든 디자인의 권리 문제를 면제한다는 의미는 아니다.
- B 고정밀/신경망 엔진은 계속 미지원이다. 제한적으로 `청바지/슬랙스/반바지` + 저장 원본/누끼 + 사진/보호 디자인 복원/결과 이용의 세 권한 모두 verified일 때만 앞면 투영 근사를 제공한다. 사진이 있다는 사실/직접 촬영/체크박스만으로 B를 켜지 않는다. 이용 조건은 기존 증빙 검토 결과가 해당 의류·이미지·출력 범위를 허용하는 경우에만 유효하다.
- B 결과는 앞면의 허용된 픽셀을 포함할 수 있으므로 동일하게 비공개/소유권/삭제/철회 통제를 적용한다. 원본 체크/주머니 등은 단일 사진의 투영이며 고유 3D 형상 복원·뒷면 복원을 검증했다는 뜻이 아니다. 후면은 일반 생성 무늬/색상으로 추정한다. 현재 실제 사용자 원본에는 A만 사용하며 B 권한을 임의 변경하지 않는다.

## 바지 표면 품질 보완 (2026-11-03)

stylefit-pants-2.1: 프로젝트 직접 작성한 천 단면/드레이프/접힌 단 알고리즘과 일반 체크/실 교차 패턴만 보완했다. 새 패키지·AI 모델·가중치·외부 API·외부 자산을 추가하지 않았다. A는 원본 텍스처 픽셀을 복사하지 않고 B는 기존 세 권한 verified 경계를 유지한다.

## 연결 패널 템플릿·Blender 오프라인 실험 (2026-11-04)

- 티셔츠 앞뒤 패널/목/소매 경계 및 템플릿 카탈로그/원단 프리셋은 프로젝트 직접 제작이다. 외부 의류 자산·새 AI 모델/가중치/API를 도입하지 않았다. 기존 Pillow/NumPy/Three.js/R3F 감사와 A/B 증빙 경계를 유지한다.
- Blender4.5.9 LTS 공식 Windows x64 portable, GPL-3.0-or-later. 공식 배포 https://download.blender.org/release/Blender4.5/ 및 blender-4.5.9.sha256 대조. ZIP SHA256 `41da973b9bf95bb312cbeff4d1982feb13259b43c821686b9bafea4dfe5477cf`. 바이너리/부속 도구는 Git 제외 storage/quality-engine/tools에만 보관하고 앱 의존성/배포물에 추가하지 않았다.
- 공식 라이선스/상업적 사용/산출물 안내: https://www.blender.org/about/license/ , https://www.blender.org/support/faq/ . GPL에 따른 소프트웨어 재배포/수정 소스 의무와 작품/데이터 산출물의 권리는 구분한다. 기존 사진/브랜드/모델 자산의 권리가 사라지는 것은 아니다.
- Blender API를 사용하는 별도 `backend/scripts/cloth_quality_experiment.py`는 GPL-3.0-or-later 헤더를 명시했다. 앱 서버와 분리된 실험용 스크립트이며 앱 라이브러리로 bpy를 설치하지 않았다. Blender를 재배포할 경우 GPL 및 포함된 종속 라이선스 자료를 함께 검토해야 한다.
- Cycles CPU 렌더와 Cloth modifier만 사용한다. Blender에 포함된 외부 AI 기능/학습 가중치를 이번 파이프라인에 도입하지 않았다. 공식 cloth 설명: https://docs.blender.org/manual/en/4.5/physics/cloth/index.html .
