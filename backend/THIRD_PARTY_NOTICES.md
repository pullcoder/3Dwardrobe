# 3단계 서버 모델·의존성 고지

## 4단계 신규 어댑터의 미설치 후보

TripoSR/TRELLIS.2와 신규 GPU 종속성은 현재 설치·배포하지 않는다. 본체/모델 MIT와 torchmcubes MPL-2.0, NVIDIA 비상업 조건은 [감사 문서](../AI_LICENSE_AUDIT.md) 및 [원문 사본·출처](../docs/licenses/generation-engines/sources.json)에 분리 보존했다. 이 고지는 설치나 상용 승인을 의미하지 않는다. 향후 배포 시 정확한 버전의 전체 MIT 고지, MPL covered source 제공, 기타 전이 종속성 의무를 별도 충족해야 하며 NVIDIA 비상업 경로는 상용 활성화하지 않는다.

- OpenCLIP 3.3.0: MIT, [코드](https://github.com/mlfoundations/open_clip), [라이선스 사본](../docs/licenses/OpenCLIP-MIT.txt).
- LAION CLIP-ViT-B-32-laion2B-s34B-b79K 가중치: 모델 카드 `license: mit`, [고정 카드 사본](../docs/licenses/OpenCLIP-LAION-model-card.md). 모델 카드의 사용/평가 한계도 함께 보존한다.
- OpenCLIP 파생 코드/토크나이저의 OpenAI 고지: [MIT](../docs/licenses/CLIP-MIT.txt). 원본 OpenAI CLIP 가중치는 사용하지 않는다.
- Meta SAM 코드/가중치: [Apache-2.0](../docs/licenses/SAM-Apache-2.0.txt).
- Tesseract.js/core 7.0.0: [JS Apache-2.0](../docs/licenses/Tesseract-js-Apache-2.0.txt), [core Apache-2.0](../docs/licenses/Tesseract-core-Apache-2.0.txt).
- tessdata_fast kor+eng: [Apache-2.0](../docs/licenses/tessdata-fast-Apache-2.0.txt).

다운로드 URL·버전·SHA-256은 [model_manifest.json](model_manifest.json), 종속성은 requirements.lock.txt와 ocr/package-lock.json에 고정한다.
실제 모델/SDK는 수정·재학습하지 않았다. StyleFit의 입력 검증·프롬프트·분류 채택 규칙·투명 PNG/OCR 구조화 코드를 별도로 작성했다.
서버 Python/Node 패키지를 Android에 묶지 않는다. 서버 바이너리 자체 재배포 시 각 설치 패키지의 LICENSE/NOTICE 및 포함 라이브러리 고지를 함께 배포하고 전체 바이너리 provenance를 재검토해야 한다.
라이선스는 사용자 사진·브랜드·의류 디자인의 권리를 부여하지 않는다. 상업 사용 가능성과 모델 품질/권리 분쟁 위험의 부재는 같은 의미가 아니다.
