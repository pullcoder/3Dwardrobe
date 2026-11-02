import { Component, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { Minus, Plus, RotateCcw } from "lucide-react";
import type { BodyProfile } from "../body/types";
import { bodyDimensions } from "./geometry";
import { MannequinModel } from "./MannequinModel";

export interface ViewCommand {
  view: "front" | "side" | "back" | "reset" | "zoom_in" | "zoom_out";
  sequence: number;
}
function CameraControls({
  height,
  command,
}: {
  height: number;
  command: ViewCommand;
}) {
  const { camera, gl, invalidate } = useThree();
  const controls = useRef<OrbitControls | null>(null);
  useEffect(() => {
    const orbit = new OrbitControls(camera, gl.domElement);
    orbit.enablePan = false;
    orbit.minDistance = 0.8;
    orbit.maxDistance = 8;
    orbit.minPolarAngle = Math.PI * 0.16;
    orbit.maxPolarAngle = Math.PI * 0.85;
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
    orbit.target.set(0, height * 0.5, 0);
    if (command.view === "zoom_in" || command.view === "zoom_out") {
      camera.position
        .sub(orbit.target)
        .multiplyScalar(command.view === "zoom_in" ? 0.82 : 1.22)
        .add(orbit.target);
    } else {
      const distance = height * 1.9;
      camera.position.set(
        command.view === "side" ? distance : 0,
        height * 0.57,
        command.view === "side"
          ? 0
          : command.view === "back"
            ? -distance
            : distance,
      );
    }
    orbit.update();
    invalidate();
  }, [camera, height, command, invalidate]);
  return null;
}

class ViewportBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <p className="error" role="alert">
        이 브라우저에서 3D 화면을 실행할 수 없습니다. WebGL을 지원하는
        브라우저에서 다시 열어 주세요. 치수 입력·저장은 계속 사용할 수 있습니다.
      </p>
    ) : (
      this.props.children
    );
  }
}

export default function MannequinViewport({
  profile,
}: {
  profile: BodyProfile;
}) {
  const [command, setCommand] = useState<ViewCommand>({
    view: "front",
    sequence: 0,
  });
  const [ready, setReady] = useState(false);
  const d = bodyDimensions(profile);
  function send(view: ViewCommand["view"]) {
    setCommand((current) => ({ view, sequence: current.sequence + 1 }));
  }
  const revision = [
    d.values.height,
    d.values.shoulder,
    d.values.chest,
    d.values.waist,
    d.values.hip,
    d.values.arm,
    d.values.leg,
  ].join("/");
  return (
    <section
      className="mannequin-viewport"
      aria-label="개인화 3D 마네킹"
      data-body-revision={revision}
    >
      <div className="viewport-heading">
        <span className="eyebrow">MY PARAMETRIC MANNEQUIN</span>
        <span className="pill">중립 얼굴 · 추정 형태</span>
      </div>
      <ViewportBoundary>
        <div
          className="canvas-wrap"
          role="img"
          aria-label="드래그로 회전하고 휠 또는 두 손가락으로 확대하는 3D 마네킹"
        >
          <Canvas
            frameloop="demand"
            dpr={[1, 1.5]}
            camera={{ position: [0, 1, 3.2], fov: 38 }}
            gl={{ antialias: true, preserveDrawingBuffer: true }}
            onCreated={() => setReady(true)}
            fallback={<p role="alert">WebGL을 지원하지 않는 브라우저입니다.</p>}
          >
            <color attach="background" args={["#eee9f3"]} />
            <ambientLight intensity={1.4} />
            <directionalLight position={[3, 4, 5]} intensity={2.4} />
            <directionalLight position={[-3, 2, -3]} intensity={1.2} />
            <MannequinModel profile={profile} />
            <gridHelper
              args={[3, 20, "#c8bbd5", "#ded4e7"]}
              position={[0, -0.003, 0]}
            />
            <CameraControls height={d.h} command={command} />
          </Canvas>
        </div>
      </ViewportBoundary>
      <div className="view-controls" role="group" aria-label="마네킹 시점">
        <button
          className="button secondary"
          disabled={!ready}
          onClick={() => send("front")}
        >
          정면
        </button>
        <button
          className="button secondary"
          disabled={!ready}
          onClick={() => send("side")}
        >
          측면
        </button>
        <button
          className="button secondary"
          disabled={!ready}
          onClick={() => send("back")}
        >
          후면
        </button>
        <button
          className="icon-button"
          disabled={!ready}
          aria-label="마네킹 확대"
          onClick={() => send("zoom_in")}
        >
          <Plus size={18} />
        </button>
        <button
          className="icon-button"
          disabled={!ready}
          aria-label="마네킹 축소"
          onClick={() => send("zoom_out")}
        >
          <Minus size={18} />
        </button>
        <button
          className="icon-button"
          disabled={!ready}
          aria-label="카메라 초기화"
          onClick={() => send("reset")}
        >
          <RotateCcw size={17} />
        </button>
      </div>
      <p className="helper">
        드래그로 360° 회전 · 휠/핀치로 확대 · 빈 치수는 기본 비율 사용
      </p>
      <span className="sr-only" role="status">
        3D {ready ? "준비 완료" : "준비 중"} · 현재 명령 {command.view}{" "}
        {command.sequence}
      </span>
    </section>
  );
}
