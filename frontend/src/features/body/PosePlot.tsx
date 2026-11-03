import { poseConnections } from "./measurements";
import type { PoseAnalysis } from "./types";

export function PosePlot({ analysis }: { analysis: PoseAnalysis }) {
  return (
    <figure className="pose-plot">
      <svg
        viewBox={`0 0 ${analysis.width} ${analysis.height}`}
        role="img"
        aria-label="MediaPipe가 추출한 33개 관절 특징점. 원본 사진은 포함하지 않음"
      >
        {poseConnections.map(([a, b]) => (
          <line
            key={`${a}-${b}`}
            x1={analysis.landmarks[a].x * analysis.width}
            y1={analysis.landmarks[a].y * analysis.height}
            x2={analysis.landmarks[b].x * analysis.width}
            y2={analysis.landmarks[b].y * analysis.height}
            stroke="#7255b6"
            strokeWidth={analysis.width * 0.004}
          />
        ))}
        {analysis.landmarks.map((point, i) => (
          <circle
            key={i}
            cx={point.x * analysis.width}
            cy={point.y * analysis.height}
            r={analysis.width * 0.006}
            fill={point.visibility >= 0.55 ? "#8464b3" : "#cbbdd7"}
          />
        ))}
      </svg>
      <figcaption>
        33개 특징점 · 원본 사진 없는 관절도 · 관절 신뢰도는 치수 정확도가
        아닙니다.
      </figcaption>
    </figure>
  );
}
