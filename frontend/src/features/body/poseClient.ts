import { checkImage } from "../../lib/images";
import { summarizePose } from "./measurements";
import type { Landmark, PoseAnalysis } from "./types";

export async function analyzePose(
  file: File,
  progress: (text: string) => void,
  signal: AbortSignal,
): Promise<PoseAnalysis> {
  await checkImage(file);
  if (
    typeof createImageBitmap === "undefined" ||
    typeof Worker === "undefined" ||
    typeof OffscreenCanvas === "undefined"
  )
    throw new Error(
      "이 브라우저는 기기 내 사진 분석을 지원하지 않습니다. 최신 Chrome 또는 Edge에서 다시 시도해 주세요.",
    );
  if (signal.aborted) throw new Error("분석을 취소했습니다.");
  const source = await createImageBitmap(file);
  const factor = Math.min(1, 1600 / Math.max(source.width, source.height));
  const width = Math.round(source.width * factor),
    height = Math.round(source.height * factor);
  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(source, {
      resizeWidth: width,
      resizeHeight: height,
    });
  } finally {
    source.close();
  }
  if (signal.aborted) {
    bitmap.close();
    throw new Error("분석을 취소했습니다.");
  }
  return new Promise((resolve, reject) => {
    let worker: Worker;
    try {
      worker = new Worker("/pose-worker.js");
    } catch {
      bitmap.close();
      reject(
        new Error(
          "분석 Worker를 시작하지 못했습니다. 브라우저 보안 설정을 확인해 주세요.",
        ),
      );
      return;
    }
    const finish = () => {
      worker.terminate();
      clearTimeout(timer);
      signal.removeEventListener("abort", abort);
    };
    const abort = () => {
      finish();
      reject(new Error("분석을 취소했습니다."));
    };
    const timer = setTimeout(() => {
      finish();
      reject(
        new Error(
          "분석 시간이 초과되었습니다. 사진 크기를 줄이거나 다시 시도해 주세요.",
        ),
      );
    }, 90000);
    signal.addEventListener("abort", abort, { once: true });
    worker.onerror = () => {
      finish();
      reject(
        new Error(
          "분석 엔진을 불러오지 못했습니다. 모델 파일 준비 상태와 브라우저 지원을 확인해 주세요.",
        ),
      );
    };
    worker.onmessage = (
      event: MessageEvent<{
        type: string;
        message: string;
        landmarks: Landmark[][];
      }>,
    ) => {
      if (event.data.type === "progress") {
        progress(event.data.message);
        return;
      }
      finish();
      if (event.data.type === "error") {
        reject(new Error(event.data.message));
        return;
      }
      try {
        resolve({
          landmarks: event.data.landmarks[0],
          summary: summarizePose(event.data.landmarks, width, height),
          width,
          height,
        });
      } catch (error) {
        reject(error);
      }
    };
    try {
      worker.postMessage({ bitmap }, [bitmap]);
    } catch {
      bitmap.close();
      finish();
      reject(
        new Error(
          "사진을 분석 Worker에 전달하지 못했습니다. 다시 시도해 주세요.",
        ),
      );
    }
  });
}
