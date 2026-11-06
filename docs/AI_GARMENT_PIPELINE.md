# AI_GARMENT_PIPELINE — 의류 누끼 학습 · 3D 변환

> AI Hub 'K-Fashion 이미지'(dataSetSn=51) 경량(샘플) 데이터로 의류 부위 세그멘테이션을 학습하고,
> 옷 사진 → 부위별 누끼 PNG → 3D 메시(.glb)까지 만드는 방법. 결정 배경은 `DECISIONS.md` D-014.

## 1. 전체 흐름

```
옷 사진 ─▶ 세그멘테이션 (배경/상의/하의/아우터/원피스)  app/ai/segmentation.py
       ─▶ 부위별 마스크 정리 + 누끼 RGBA PNG          app/ai/cutout.py
       ─▶ 부풀린 닫힌 메시 + 누끼 텍스처 → .glb/.obj   app/ai/garment_asset.py
```

**3D 범위(MVP 가정)**: 사진 한 장에서 옷의 실제 입체 형태를 복원하는 것이 아니라, 누끼 윤곽 안쪽을
부풀려 두께를 준 '입체 카드'다. 3D 뷰어에서 돌려 볼 수 있고 앞면 무늬는 정확하지만,
뒷면은 앞면 텍스처가 좌우 반전돼 보이고 소매·주름의 실제 입체감은 없다. 드레이핑·아바타 착장은 T2-4.

## 2. 데이터 받기 (사람이 직접)

쓸 수 있는 AI Hub 데이터 (둘 다 JPG + 폴리곤 JSON이고, 3D 메시 파일은 들어 있지 않다):

| 데이터 | 라벨 형식 | 맞는 용도 |
|--------|----------|----------|
| K-Fashion 이미지 (dataSetSn=51) | 부위별 `폴리곤좌표` | 사람이 입은 사진에서 상의·하의·아우터·원피스 분리. 경량 샘플이 있어 먼저 시작하기 좋다 |
| 의류 가상착용 3D 이미지 업사이클링 (dataSetSn=71940) | LabelMe (`shapes`/`label`/`points`) | '2D 상품' 이미지(옷만 찍은 사진)가 절반이라 옷장 등록 사진과 비슷하다. 경량 샘플은 없고 334만 건 규모라 일부 파일만 받는다 |

두 형식 모두 같은 스크립트가 자동으로 알아본다. LabelMe 라벨 이름이 `app/ai/config.py`의 `LABELME_LABEL_TO_SLOT`에
없으면 `check_kfashion.py`가 '의류로 안 쓴 라벨'로 보여 준다. 그때는 `{"라벨 이름": "top"}` 형식 JSON을 만들어
`--label-map`으로 넘긴다 (slot: `top` / `bottom` / `outer` / `onepiece`). 두 데이터를 한 상위 폴더에 같이 두면 함께 학습된다.

1. AI Hub 로그인 → 데이터셋 페이지에서 다운로드 신청 → 승인 (내국인만 신청 가능).
2. 샘플(경량) 데이터를 받는다. 분할 압축이면 합친 뒤 푼다.
   ```bash
   cat 파일명.zip.part* > 파일명.zip     # Windows: WSL 또는 Git Bash에서
   ```
3. 압축을 푼 폴더를 아무 곳에 둔다 (예: `D:/aihub/K-Fashion_sample`). 저장소 밖에 두는 게 가장 안전하다. 저장소 안이라면 `2D/`, `3D/`, `datasets/` 폴더만 `.gitignore`로 막혀 있다 (재배포 금지).
4. 이미지 파일 이름은 라벨 JSON 파일 이름과 같다 (`1016530.jpg` ↔ `1016530.json`). JSON 안의 `이미지 파일명`은 촬영 원본 이름이라 실제 파일과 다르다. 이름을 직접 바꾸면 짝이 끊기므로 `organize_kfashion`을 쓴다.

폴더 구조는 신경 쓰지 않아도 된다. 하위 폴더 전체에서 `.json` 라벨을 찾고, JSON 안의 이미지 파일명
(없으면 JSON 파일 이름)으로 이미지를 짝짓는다. 라벨이 다른 곳에 있으면 `--labels-dir`로 지정한다.

## 3. 설치

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate     # macOS/Linux: source .venv/bin/activate
# NVIDIA GPU가 있으면 먼저 pytorch.org의 CUDA용 torch 설치 명령을 실행
pip install -r requirements-ai.txt
```

## 4. 데이터 확인 → 학습 → 실행 (backend/ 폴더에서)

```bash
# (선택) 원천+라벨링을 한 폴더로 합치고 이름에 특징 붙이기. 원본은 그대로, 복사만 함
#  → 1016530_레트로_상의-탑-화이트_하의-청바지-스카이블루.jpg/.json + index.csv
python -m scripts.organize_kfashion --data-dir "C:/Temp/3Dwardrobe/2D/New_sample" --out-dir "C:/Temp/kfashion_merged"

# ① 데이터가 제대로 읽히는지 + 마스크 미리보기 5장 (out/kfashion_preview/)
python -m scripts.check_kfashion --data-dir "D:/aihub/K-Fashion_sample" --preview 5

# ② 학습 (체크포인트: AI_WEIGHTS_DIR/cloth_seg/kfashion_deeplabv3_mbv3.pth)
python -m scripts.train_cloth_seg --data-dir "D:/aihub/K-Fashion_sample" --epochs 30 --batch-size 8

# ③ 누끼 + 3D 변환 (파일 또는 폴더)
python -m scripts.run_garment_pipeline --image "D:/photos/look01.jpg" --out-dir out/

# (모델 없이) 정답 폴리곤으로 누끼·3D만 먼저 확인
python -m scripts.run_garment_pipeline --image 1000.jpg --label 1000.json --out-dir out/
```

결과 폴더 `out/<이미지이름>/`:

| 파일 | 내용 |
|------|------|
| `overlay.jpg` | 원본 위에 부위별 색 (빨강 상의, 파랑 하의, 초록 아우터, 노랑 원피스) |
| `{slot}_cutout.png` | 부위별 누끼 (투명 배경) |
| `{slot}.glb` | 3D 메시 (Three.js/R3F에서 바로 로드). https://gltf-viewer.donmccurdy.com 에 끌어다 놓아 확인 |
| `{slot}.obj/.mtl/.png` | 같은 메시의 OBJ 버전 (`--no-obj`로 끔) |
| `result.json` | 부위, bbox, 면적 비율, 정점·면 수 |

## 5. 학습 팁

| 상황 | 방법 |
|------|------|
| GPU 없음 | CPU도 된다. `--image-size 384 --batch-size 4`로 줄이고 `--max-samples 200`으로 먼저 돌려 본다 |
| GPU 메모리 부족 | `--batch-size`를 절반으로 |
| 인터넷 없는 PC | `--no-pretrained` (ImageNet 백본 없이 → 정확도 낮아지므로 epoch를 늘린다) |
| Windows에서 DataLoader 멈춤 | `--workers 0` |
| 경량 데이터라 과적합 | 검증 mIoU가 떨어지기 시작하면 멈춘다. 체크포인트는 검증 mIoU 최고일 때만 저장된다 |

학습 기록은 체크포인트 옆 `.json`에 epoch별 손실·클래스별 IoU로 남는다.
경량 샘플은 수백 장 규모라 성능이 제한적이다. 실서비스 수준은 원본 데이터(약 120만 건) 일부를 추가로 받아 학습한다.

## 6. 3D 메시 옵션

| 옵션 | 기본 | 설명 |
|------|------|------|
| `--grid-max` | 160 | 긴 변 기준 격자 수. 크면 매끈하지만 파일이 커진다 (160 ≈ 정점 2만) |
| `--depth-ratio` | 0.12 | 가장 두꺼운 곳의 두께 = 옷 너비 × 비율 |
| `--height-m` | 없음 | 옷 실제 길이(m). OCR 사이즈표와 연결하면 실제 크기 메시가 된다 |

## 7. 워커 연동 (다음 작업)

- Celery 작업 `closet.process_item`에서 워커 시작 시 `ClothSegmenter()`를 1회 만들고,
  `extract_cutouts()` → `build_garment_mesh()` → `write_glb()` 결과를 storage에 올려 `cutout_url`, `mesh_url`에 저장한다.
- 원본 이미지·누끼는 로그에 남기지 않는다 (ID만).
