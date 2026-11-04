"""공식 Python API를 호출하는 독립 어댑터. 현재 미감사 GPU 환경에서는 실행 금지.

추후 라이선스·가중치·CUDA 버전 감사가 끝난 격리 워커에서만 사용한다.
라이브러리 자동 설치나 from_pretrained의 원격 모델 다운로드를 허용하지 않는다.
"""

from pathlib import Path

from app.services.generation_engines import require_engine


class TripoSRAdapter:
    engine = "triposr"

    def generate(self, image, weights: Path, output: Path):
        require_engine(self.engine)
        import torch
        from tsr.system import TSR

        model = TSR.from_pretrained(
            str(weights), config_name="config.yaml", weight_name="model.ckpt"
        )
        model.renderer.set_chunk_size(8192)
        model.to("cuda:0")
        rgb = image.convert("RGBA")
        from PIL import Image

        background = Image.new("RGBA", rgb.size, (128, 128, 128, 255))
        rgb = Image.alpha_composite(background, rgb).convert("RGB")
        torch.cuda.reset_peak_memory_stats()
        with torch.inference_mode():
            codes = model([rgb], device="cuda:0")
            mesh = model.extract_mesh(codes, True, resolution=256)[0]
        mesh.export(str(output), file_type="glb")
        torch.cuda.synchronize()
        return {"peak_gpu_bytes": torch.cuda.max_memory_allocated(), "appearance": "vertex_colors"}


class Trellis2Adapter:
    engine = "trellis2"

    def generate(self, image, weights: Path, output: Path):
        require_engine(self.engine)
        import o_voxel
        import torch
        from trellis2.pipelines import Trellis2ImageTo3DPipeline

        pipeline = Trellis2ImageTo3DPipeline.from_pretrained(str(weights))
        pipeline.cuda()
        torch.cuda.reset_peak_memory_stats()
        with torch.inference_mode():
            mesh = pipeline.run(image)[0]
            mesh.simplify(16777216)
            glb = o_voxel.postprocess.to_glb(
                vertices=mesh.vertices,
                faces=mesh.faces,
                attr_volume=mesh.attrs,
                coords=mesh.coords,
                attr_layout=mesh.layout,
                voxel_size=mesh.voxel_size,
                aabb=[[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]],
                decimation_target=100000,
                texture_size=2048,
                remesh=True,
                remesh_band=1,
                remesh_project=0,
                verbose=False,
            )
            glb.export(str(output), extension_webp=False)
        torch.cuda.synchronize()
        return {"peak_gpu_bytes": torch.cuda.max_memory_allocated(), "appearance": "pbr"}


ADAPTERS = {"triposr": TripoSRAdapter, "trellis2": Trellis2Adapter}
