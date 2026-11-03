"""모든 추론은 로컬 CPU. 모델 누락/실패를 가짜 분석으로 대체하지 않는다."""

import base64
import hashlib
import json
import subprocess
from io import BytesIO
from pathlib import Path
from threading import Lock

from PIL import Image, ImageOps

from app.core.errors import AppError

ROOT = Path(__file__).resolve().parents[2]
WEIGHTS = ROOT / "models/weights"
INFERENCE_LOCK = Lock()
TYPES = {
    "티셔츠": ("t-shirt", "top"),
    "셔츠": ("button-up shirt", "top"),
    "니트": ("knitted sweater", "top"),
    "후드티": ("hoodie", "top"),
    "맨투맨": ("sweatshirt", "top"),
    "카디건": ("cardigan", "outer"),
    "재킷": ("jacket", "outer"),
    "코트": ("coat", "outer"),
    "패딩": ("puffer jacket", "outer"),
    "청바지": ("jeans", "bottom"),
    "슬랙스": ("dress pants", "bottom"),
    "반바지": ("shorts", "bottom"),
    "스커트": ("skirt", "bottom"),
    "기타": ("other garment", None),
    "unknown": ("non-clothing object", None),
}


def image_from_bytes(data: bytes) -> Image.Image:
    with Image.open(BytesIO(data)) as source:
        return ImageOps.exif_transpose(source).convert("RGB")


class GarmentAI:
    def __init__(self):
        self.clip_model = None
        self.preprocess = None
        self.text_cache = {}
        self.sam = None
        self.verified = set()

    def verify_models(self, prefix):
        if prefix in self.verified:
            return
        for spec in json.loads((ROOT / "model_manifest.json").read_text(encoding="utf-8")):
            if spec["file"].startswith(prefix):
                path = ROOT / spec["file"]
                checksum = None
                if path.is_file():
                    with path.open("rb") as stream:
                        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
                if checksum != spec["sha256"]:
                    raise AppError(
                        "MODEL_INTEGRITY",
                        "모델 파일을 검증하지 못했습니다. 준비 명령을 다시 실행해 주세요.",
                        503,
                    )
        self.verified.add(prefix)

    def status(self):
        return {
            "classification": (WEIGHTS / "open_clip_model.safetensors").is_file(),
            "segmentation": (WEIGHTS / "sam_vit_b_01ec64.pth").is_file(),
            "ocr": all(
                (ROOT / f"ocr/models/{lang}.traineddata").is_file() for lang in ("kor", "eng")
            )
            and (ROOT / "ocr/node_modules/tesseract.js").is_dir(),
            "device": "cpu",
            "external_api": False,
        }

    def classify(self, image: Image.Image):
        if not self.status()["classification"]:
            raise AppError(
                "MODEL_UNAVAILABLE", "분류 모델이 없습니다. 모델 준비 명령을 실행해 주세요.", 503
            )
        import open_clip
        import torch

        torch.set_num_threads(4)
        if self.clip_model is None:
            self.verify_models("models/weights/open_clip")
            self.clip_model, _, self.preprocess = open_clip.create_model_and_transforms(
                "ViT-B-32", pretrained=str(WEIGHTS / "open_clip_model.safetensors"), device="cpu"
            )
            self.clip_model.eval()
        with torch.inference_mode():
            feature = self.clip_model.encode_image(self.preprocess(image).unsqueeze(0))
            feature /= feature.norm(dim=-1, keepdim=True)

            def choose(labels, prompts):
                key = tuple(prompts)
                if key not in self.text_cache:
                    text = self.clip_model.encode_text(open_clip.get_tokenizer("ViT-B-32")(prompts))
                    self.text_cache[key] = text / text.norm(dim=-1, keepdim=True)
                scores = (feature @ self.text_cache[key].T)[0]
                ranked = scores.argsort(descending=True)
                first, second = int(ranked[0]), int(ranked[1])
                # 모델 cosine similarity를 그대로 보존한다. 보정된 확률/정확도가 아니다.
                score = float(scores[first])
                accepted = score >= 0.20 and float(scores[first] - scores[second]) >= 0.015
                return {
                    "value": labels[first] if accepted else "unknown",
                    "candidate": labels[first],
                    "similarity": round(score, 5),
                    "margin": round(float(scores[first] - scores[second]), 5),
                }

            kind = choose(list(TYPES), [f"a product photo of a {v[0]}" for v in TYPES.values()])
            color = choose(
                [
                    "검정",
                    "흰색",
                    "회색",
                    "빨강",
                    "주황",
                    "노랑",
                    "초록",
                    "파랑",
                    "보라",
                    "분홍",
                    "갈색",
                    "베이지",
                ],
                [
                    f"a {c} garment"
                    for c in [
                        "black",
                        "white",
                        "gray",
                        "red",
                        "orange",
                        "yellow",
                        "green",
                        "blue",
                        "purple",
                        "pink",
                        "brown",
                        "beige",
                    ]
                ],
            )
            pattern = choose(
                ["무지", "줄무늬", "체크", "꽃무늬", "도트", "그래픽"],
                [
                    f"a garment with {c}"
                    for c in [
                        "a solid color",
                        "stripes",
                        "a plaid pattern",
                        "a floral pattern",
                        "polka dots",
                        "a graphic print",
                    ]
                ],
            )
            sleeve = choose(
                ["민소매", "반소매", "긴소매"],
                [f"a {c} garment" for c in ["sleeveless", "short sleeve", "long sleeve"]],
            )
            neckline = choose(
                ["라운드넥", "브이넥", "카라", "후드", "터틀넥"],
                [
                    f"a garment with {c}"
                    for c in ["a round neck", "a V neck", "a collar", "a hood", "a turtleneck"]
                ],
            )
        return {
            "model": "OpenCLIP ViT-B-32 LAION-2B s34B b79K",
            "method": "zero_shot_cosine_similarity",
            "garment_type": kind["value"],
            "category": TYPES.get(kind["value"], (None, None))[1],
            "primary_color": color["value"],
            "secondary_color": None,
            "pattern": pattern["value"],
            "sleeve": sleeve["value"],
            "neckline": neckline["value"],
            "fit": "unknown",
            "visual_features": None,
            "material": None,
            "scores": {
                "garment_type": kind,
                "color": color,
                "pattern": pattern,
                "sleeve": sleeve,
                "neckline": neckline,
            },
            "warnings": [
                "유사도는 신뢰도나 정확도가 아닙니다. 결과를 확인해 주세요.",
                "핏·단추·지퍼·주머니·소재는 이 모델로 확정하지 않습니다.",
            ],
        }

    def segment(self, image: Image.Image, x: float = 0.5, y: float = 0.5):
        if not self.status()["segmentation"]:
            raise AppError("MODEL_UNAVAILABLE", "배경 제거 모델이 준비되지 않았습니다.", 503)
        import numpy as np
        import torch
        from segment_anything import SamPredictor, sam_model_registry

        torch.set_num_threads(4)
        if self.sam is None:
            self.verify_models("models/weights/sam")
            self.sam = sam_model_registry["vit_b"](checkpoint=str(WEIGHTS / "sam_vit_b_01ec64.pth"))
            self.sam.eval()
        # 이미지 임베딩은 요청 범위 predictor에만 보관한다. 사용자 간 공유 금지.
        image.thumbnail((1600, 1600))
        w, h = image.size
        predictor = SamPredictor(self.sam)
        with torch.inference_mode():
            predictor.set_image(np.asarray(image))
            masks, scores, _ = predictor.predict(
                point_coords=np.array([[x * w, y * h]]),
                point_labels=np.array([1]),
                multimask_output=True,
            )
        valid = [i for i, mask in enumerate(masks) if 0.01 < float(mask.mean()) < 0.98]
        if not valid:
            raise AppError(
                "SEGMENTATION_FAILED",
                "의류 영역을 분리하지 못했습니다. "
                "옷 중앙을 선택하거나 사진을 바꿔 재시도해 주세요.",
            )
        best = max(valid, key=lambda i: float(scores[i]))
        result = image.convert("RGBA")
        result.putalpha(Image.fromarray((masks[best] * 255).astype("uint8")))
        buffer = BytesIO()
        result.save(buffer, format="PNG")
        predictor.reset_image()
        return {
            "png": base64.b64encode(buffer.getvalue()).decode(),
            "model": "SAM ViT-B 01ec64",
            "predicted_iou": float(scores[best]),
            "width": w,
            "height": h,
            "warnings": [
                "선택 지점 중심의 일반 물체 분리 결과입니다. "
                "의류의 정확한 윤곽을 보장하지 않으며 착용 인물도 포함될 수 있습니다."
            ],
        }

    def ocr(self, data: bytes, kind: str):
        self.verify_models("ocr/models/")
        if not self.status()["ocr"]:
            raise AppError(
                "MODEL_UNAVAILABLE", "OCR 엔진과 한글·영문 학습 데이터를 준비해 주세요.", 503
            )
        try:
            output = subprocess.run(
                ["node", str(ROOT / "ocr/recognize.mjs")],
                input=data,
                capture_output=True,
                timeout=90,
                check=True,
            )
            result = json.loads(output.stdout)
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            raise AppError(
                "OCR_FAILED", "라벨을 읽지 못했습니다. 선명한 사진으로 다시 시도해 주세요.", 503
            ) from exc
        from app.services.ocr_parser import parse_ocr

        return {
            "model": "Tesseract.js 7 / tessdata_fast kor+eng",
            **result,
            **parse_ocr(result["text"], kind),
        }
