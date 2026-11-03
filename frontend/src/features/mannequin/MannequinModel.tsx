import { useEffect, useMemo } from "react";
import * as THREE from "three";
import type { BodyProfile } from "../body/types";
import { bodyDimensions, createTorsoGeometry, ellipseRadius } from "./geometry";
import type { MannequinPart } from "./geometry";

const material = { color: "#baa8ce", roughness: 0.58, metalness: 0.05 };
function Ellipsoid({
  name,
  position,
  scale,
}: {
  name: MannequinPart;
  position: [number, number, number];
  scale: [number, number, number];
}) {
  return (
    <mesh
      name={name}
      position={position}
      scale={scale}
      userData={{ body_part: name }}
    >
      <sphereGeometry args={[1, 32, 24]} />
      <meshStandardMaterial {...material} />
    </mesh>
  );
}
function Limb({
  name,
  start,
  end,
  radius,
}: {
  name: MannequinPart;
  start: [number, number, number];
  end: [number, number, number];
  radius: number;
}) {
  const a = new THREE.Vector3(...start),
    b = new THREE.Vector3(...end);
  const delta = b.clone().sub(a),
    midpoint = a.clone().add(b).multiplyScalar(0.5);
  const rotation = new THREE.Quaternion().setFromUnitVectors(
    new THREE.Vector3(0, 1, 0),
    delta.clone().normalize(),
  );
  return (
    <mesh
      name={name}
      position={midpoint}
      quaternion={rotation}
      userData={{ body_part: name }}
    >
      <capsuleGeometry
        args={[radius, Math.max(0.005, delta.length()), 8, 24]}
      />
      <meshStandardMaterial {...material} />
    </mesh>
  );
}

export function MannequinModel({ profile }: { profile: BodyProfile }) {
  const d = bodyDimensions(profile);
  const torso = useMemo(() => createTorsoGeometry(profile), [profile]);
  useEffect(() => () => torso.dispose(), [torso]);
  const hipRadius = ellipseRadius(d.values.hip);
  return (
    <group
      name="stylefit_mannequin"
      userData={{
        schema: "stylefit.parametric.v1",
        unit: "meter",
        face: "neutral",
        fitting: false,
      }}
    >
      <mesh name="torso" geometry={torso} userData={{ body_part: "torso" }}>
        <meshStandardMaterial {...material} side={THREE.DoubleSide} />
      </mesh>
      <Ellipsoid
        name="pelvis"
        position={[0, d.hip - d.h * 0.035, 0]}
        scale={[hipRadius * 0.9, d.h * 0.065, hipRadius * 0.65]}
      />
      <Limb
        name="neck"
        start={[0, d.shoulder, 0]}
        end={[0, d.h * 0.89, 0]}
        radius={d.h * 0.035}
      />
      <Ellipsoid
        name="head"
        position={[0, d.h * 0.935, 0]}
        scale={[d.h * 0.048, d.h * 0.065, d.h * 0.054]}
      />
      {/* 중립 얼굴의 방향을 읽기 위한 코 형태이며 사진에서 복원하지 않는다. */}
      <mesh
        name="neutral_nose"
        position={[0, d.h * 0.925, d.h * 0.053]}
        scale={[d.h * 0.012, d.h * 0.018, d.h * 0.014]}
      >
        <sphereGeometry args={[1, 16, 12]} />
        <meshStandardMaterial {...material} />
      </mesh>
      {([-1, 1] as const).map((sign) => {
        const side = sign < 0 ? "r" : "l";
        const shoulder: [number, number, number] = [
          (sign * d.width) / 2,
          d.shoulder,
          0,
        ];
        const elbow: [number, number, number] = [
          sign * (d.width / 2 + d.arm * 0.11),
          d.shoulder - d.arm * 0.5,
          0,
        ];
        const wrist: [number, number, number] = [
          sign * (d.width / 2 + d.arm * 0.19),
          d.shoulder - d.arm * 0.98,
          0.015,
        ];
        const hip: [number, number, number] = [
          sign * hipRadius * 0.47,
          d.hip,
          0,
        ];
        const knee: [number, number, number] = [
          sign * hipRadius * 0.49,
          (d.hip + d.ankle) * 0.5,
          0.007,
        ];
        const ankle: [number, number, number] = [
          sign * hipRadius * 0.5,
          d.ankle,
          0,
        ];
        return (
          <group key={side} name={`limbs_${side}`}>
            <Limb
              name={`upper_arm_${side}`}
              start={shoulder}
              end={elbow}
              radius={d.h * 0.023}
            />
            <Limb
              name={`forearm_${side}`}
              start={elbow}
              end={wrist}
              radius={d.h * 0.019}
            />
            <Ellipsoid
              name={`hand_${side}`}
              position={[wrist[0], wrist[1] - d.h * 0.035, wrist[2]]}
              scale={[d.h * 0.018, d.h * 0.04, d.h * 0.013]}
            />
            <Limb
              name={`thigh_${side}`}
              start={hip}
              end={knee}
              radius={hipRadius * 0.4}
            />
            <Limb
              name={`calf_${side}`}
              start={knee}
              end={ankle}
              radius={d.h * 0.03}
            />
            <Ellipsoid
              name={`foot_${side}`}
              position={[ankle[0], d.h * 0.026, d.h * 0.035]}
              scale={[d.h * 0.027, d.h * 0.026, d.h * 0.074]}
            />
          </group>
        );
      })}
      <group
        name="garment_anchors"
        userData={{
          top: [0, d.chest, 0],
          bottom: [0, d.waist, 0],
          outer: [0, d.shoulder, 0],
          coordinate: "y_up_z_front",
          unit: "meter",
        }}
      />
    </group>
  );
}
