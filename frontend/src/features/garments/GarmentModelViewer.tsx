import { Component, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { Box3, Mesh, Texture, Vector3 } from "three";
import type { Group, Material } from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

type View = "front" | "side" | "back" | "reset" | "zoom_in" | "zoom_out";
interface Command {
  view: View;
  sequence: number;
}

function disposeModel(group: Group) {
  const textures = new Set<Texture>();
  group.traverse((object) => {
    if (object instanceof Mesh) {
      object.geometry.dispose();
      const materials: Material[] = Array.isArray(object.material)
        ? object.material
        : [object.material];
      for (const material of materials) {
        for (const value of Object.values(material))
          if (value instanceof Texture) textures.add(value);
        material.dispose();
      }
    }
  });
  for (const texture of textures) {
    const source = texture.source.data as { close?: () => void } | undefined;
    source?.close?.();
    texture.dispose();
  }
}

function Controls({ scene, command }: { scene: Group; command: Command }) {
  const { camera, gl, invalidate } = useThree();
  const controls = useRef<OrbitControls | null>(null);
  useEffect(() => {
    const orbit = new OrbitControls(camera, gl.domElement);
    orbit.enablePan = false;
    orbit.minDistance = 0.3;
    orbit.maxDistance = 10;
    orbit.minPolarAngle = 0.1;
    orbit.maxPolarAngle = Math.PI - 0.1;
    const refresh = () => invalidate();
    orbit.addEventListener("change", refresh);
    controls.current = orbit;
    return () => {
      orbit.removeEventListener("change", refresh);
      orbit.dispose();
      controls.current = null;
    };
  }, [camera, gl, invalidate]);
  useEffect(() => {
    const orbit = controls.current;
    if (!orbit) return;
    const box = new Box3().setFromObject(scene);
    const center = box.getCenter(new Vector3());
    const size = box.getSize(new Vector3());
    // 세로·가로 화각 중 좁은 쪽에 맞춰 모델을 크게 배치한다.
    const aspect = gl.domElement.clientWidth / gl.domElement.clientHeight;
    const distance = Math.max(size.y, size.x / Math.max(0.4, aspect)) * 1.75;
    orbit.target.copy(center);
    if (command.view === "zoom_in" || command.view === "zoom_out") {
      camera.position
        .sub(center)
        .multiplyScalar(command.view === "zoom_in" ? 0.8 : 1.25)
        .add(center);
    } else {
      camera.position
        .copy(center)
        .add(
          new Vector3(
            command.view === "side" ? distance : 0,
            size.y * 0.08,
            command.view === "side"
              ? 0
              : command.view === "back"
                ? -distance
                : distance,
          ),
        );
    }
    orbit.update();
    invalidate();
  }, [camera, command, gl, invalidate, scene]);
  return null;
}

class Boundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <p role="alert">
        3D를 표시하지 못했습니다. WebGL 지원 브라우저에서 다시 열어 주세요.
      </p>
    ) : (
      this.props.children
    );
  }
}

export default function GarmentModelViewer({ bytes }: { bytes: ArrayBuffer }) {
  const [scene, setScene] = useState<Group>();
  const [error, setError] = useState("");
  const [command, setCommand] = useState<Command>({
    view: "front",
    sequence: 0,
  });
  useEffect(() => {
    let cancelled = false;
    let loaded: Group | undefined;
    void new GLTFLoader()
      .parseAsync(bytes, "")
      .then((gltf) => {
        loaded = gltf.scene;
        if (cancelled) disposeModel(loaded);
        else setScene(loaded);
      })
      .catch(() => {
        if (!cancelled)
          setError("GLB 모델을 읽지 못했습니다. 다시 생성해 주세요.");
      });
    return () => {
      cancelled = true;
      if (loaded) disposeModel(loaded);
    };
  }, [bytes]);
  function send(view: View) {
    setCommand((current) => ({ view, sequence: current.sequence + 1 }));
  }
  return (
    <section className="mannequin-viewport" aria-label="3D 의류 뷰어">
      {error ? (
        <p role="alert">{error}</p>
      ) : !scene ? (
        <p role="status">GLB 불러오는 중…</p>
      ) : (
        <Boundary>
          <div
            className="canvas-wrap"
            role="img"
            aria-label="드래그로 360도 회전하고 핀치로 확대하는 실제 3D 의류"
          >
            <Canvas
              frameloop="demand"
              dpr={[1, 1.5]}
              camera={{ position: [0, 1, 3], fov: 40 }}
              gl={{ antialias: true, preserveDrawingBuffer: true }}
              fallback={<p role="alert">WebGL이 필요합니다.</p>}
            >
              <color attach="background" args={["#eceff2"]} />
              <ambientLight intensity={0.3} />
              <hemisphereLight args={["#ffffff", "#858585", 0.6]} />
              <directionalLight position={[-3, 4, 4]} intensity={1.7} />
              <directionalLight position={[3, 2, -3]} intensity={0.7} />
              <primitive object={scene} />
              <Controls scene={scene} command={command} />
            </Canvas>
          </div>
        </Boundary>
      )}
      <div className="view-controls" role="group" aria-label="의류 시점">
        {(
          [
            ["front", "정면"],
            ["side", "측면"],
            ["back", "후면"],
            ["zoom_in", "확대"],
            ["zoom_out", "축소"],
            ["reset", "초기화"],
          ] as const
        ).map(([view, label]) => (
          <button
            key={view}
            type="button"
            className="button secondary"
            disabled={!scene || !!error}
            onClick={() => send(view)}
          >
            {label}
          </button>
        ))}
      </div>
      <p role="status">
        {scene && !error ? "3D 의류 준비 완료" : "3D 의류 준비 중"}
      </p>
      <p className="helper">
        드래그로 360° 회전 · 휠/두 손가락으로 확대. 후면과 깊이는 추정이며 원단
        움직임을 재현하지 않습니다.
      </p>
    </section>
  );
}
