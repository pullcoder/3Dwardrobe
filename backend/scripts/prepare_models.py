"""공식 배포처의 고정 버전만 준비한다. 사진·데이터셋은 다운로드하지 않는다."""

import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def download(url: str, path: Path, expected: str | None = None):
    path.parent.mkdir(parents=True, exist_ok=True)

    def digest(file):
        with file.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()

    if not path.exists() or (expected and digest(path) != expected):
        temp = path.with_suffix(".partial")
        urllib.request.urlretrieve(url, temp)
        if expected and digest(temp) != expected:
            raise ValueError(f"모델 해시 불일치: {path.name}")
        temp.replace(path)
    checksum = digest(path)
    if expected and checksum != expected:
        raise ValueError(f"모델 해시 불일치: {path.name}")
    return {"file": str(path.relative_to(ROOT)), "sha256": checksum, "url": url}


if __name__ == "__main__":
    records = []
    for spec in json.loads((ROOT / "model_manifest.json").read_text(encoding="utf-8")):
        records.append(download(spec["url"], ROOT / spec["file"], spec["sha256"]))
    target = ROOT / "models/weights/manifest.json"
    target.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(json.dumps(records, indent=2))
