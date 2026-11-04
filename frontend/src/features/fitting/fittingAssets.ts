// 계정별 스튜디오 수명에만 존재하는 제한된 GLB 캐시. HTTP/로컬 저장 캐시는 사용하지 않는다.
import { Mesh, Texture } from "three";
import type { Group, Material } from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { getModel } from "../../api/garments";
import type { FittingResource } from "../../types/fitting";

export function disposeScene(group: Group, geometryOnly = false) {
  const materials = new Set<Material>(),
    textures = new Set<Texture>();
  group.traverse((object) => {
    if (!(object instanceof Mesh)) return;
    object.geometry.dispose();
    if (!geometryOnly)
      for (const m of Array.isArray(object.material)
        ? object.material
        : [object.material])
        materials.add(m);
  });
  for (const material of materials) {
    for (const value of Object.values(material))
      if (value instanceof Texture) textures.add(value);
    material.dispose();
  }
  for (const texture of textures) {
    const data = texture.source.data as { close?: () => void } | undefined;
    if (typeof data?.close === "function") data.close();
    texture.dispose();
  }
}

export class FittingModelCache {
  private entries = new Map<string, { scene: Group; bytes: number }>();
  private active = new Set<string>();
  hits = 0;
  setActive(ids: string[]) {
    this.active = new Set(ids);
  }
  get stats() {
    return {
      entries: this.entries.size,
      bytes: [...this.entries.values()].reduce((n, e) => n + e.bytes, 0),
      hits: this.hits,
    };
  }
  async load(token: string, resource: FittingResource, signal: AbortSignal) {
    if (
      resource.metadata.generation_kind === "ai" ||
      resource.metadata.engine === "triposr" ||
      resource.metadata.engine === "trellis2"
    )
      throw new Error(
        "AI 메시의 착용 구조가 미검증입니다. 기존 의류 템플릿으로 다시 생성해 주세요.",
      );
    const key = resource.model_asset_id;
    const cached = this.entries.get(key);
    if (cached) {
      this.hits++;
      this.entries.delete(key);
      this.entries.set(key, cached);
      return cached.scene;
    }
    const bytes = await getModel(token, resource.garment_id, signal);
    if (bytes.byteLength > 2 * 1024 * 1024)
      throw new Error(
        "모델 용량이 스튜디오 한도를 넘습니다. 경량 모델이 필요합니다.",
      );
    const view = new DataView(bytes);
    if (
      bytes.byteLength < 28 ||
      view.getUint32(0, true) !== 0x46546c67 ||
      view.getUint32(4, true) !== 2 ||
      view.getUint32(8, true) !== bytes.byteLength
    )
      throw new Error("잘못된 GLB 형식입니다.");
    const length = view.getUint32(12, true);
    const document = JSON.parse(
      new TextDecoder().decode(bytes.slice(20, 20 + length)),
    ) as { buffers?: { uri?: string }[]; images?: { uri?: string }[] };
    if (
      [...(document.buffers ?? []), ...(document.images ?? [])].some(
        (item) => item.uri && !item.uri.startsWith("data:"),
      )
    )
      throw new Error("비공개 모델은 외부 파일 없이 자체 포함 GLB여야 합니다.");
    const { scene } = await new GLTFLoader().parseAsync(bytes, "");
    if (signal.aborted) {
      disposeScene(scene);
      throw new DOMException("취소됨", "AbortError");
    }
    this.entries.set(key, { scene, bytes: bytes.byteLength });
    for (const [id, entry] of this.entries) {
      if (this.entries.size <= 6 && this.stats.bytes <= 8 * 1024 * 1024) break;
      if (!this.active.has(id)) {
        disposeScene(entry.scene);
        this.entries.delete(id);
      }
    }
    return scene;
  }
  clear() {
    for (const e of this.entries.values()) disposeScene(e.scene);
    this.entries.clear();
  }
}
