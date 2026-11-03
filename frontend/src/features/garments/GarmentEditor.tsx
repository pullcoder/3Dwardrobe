import { categories } from "../../types/domain";
import { garmentTypes } from "./types";
import type { GarmentInfo, Measurement } from "./types";

export function GarmentEditor({
  value,
  onChange,
  disabled = false,
}: {
  value: GarmentInfo;
  onChange: (info: GarmentInfo) => void;
  disabled?: boolean;
}) {
  function set<K extends keyof GarmentInfo>(key: K, next: GarmentInfo[K]) {
    onChange({ ...value, [key]: next });
  }
  const fields = [
    ["name", "의류 이름"],
    ["color", "색상"],
    ["secondary_color", "보조 색상"],
    ["pattern", "패턴"],
    ["sleeve", "소매 길이"],
    ["neckline", "넥라인"],
    ["fit", "핏"],
    ["size", "사이즈"],
    ["material", "소재 및 혼용률"],
    ["visual_features", "단추·지퍼·주머니 등 특징"],
    ["description", "설명"],
  ] as const;
  function measurement(index: number, patch: Partial<Measurement>) {
    set(
      "measurements",
      value.measurements.map((m, i) =>
        i === index ? { ...m, ...patch, source: "user_entered" } : m,
      ),
    );
  }
  const percentages = value.composition.map((c) => c.percent);
  const total = percentages.reduce<number>((sum, n) => sum + (n ?? 0), 0);
  return (
    <fieldset disabled={disabled} className="garment-editor">
      <legend className="sr-only">의류 정보 수정</legend>
      <div className="form-grid three-col">
        {fields.map(([key, label]) => (
          <label className="field" key={key}>
            <span>
              {label}
              {key === "name" ? <small> 필수</small> : null}
            </span>
            <input
              required={key === "name"}
              maxLength={
                key === "description"
                  ? 2000
                  : key === "visual_features"
                    ? 500
                    : key === "material"
                      ? 200
                      : key === "name"
                        ? 80
                        : 60
              }
              value={value[key] ?? ""}
              onChange={(e) => set(key, e.target.value)}
            />
          </label>
        ))}
        <label className="field">
          <span>분류</span>
          <select
            value={value.category}
            onChange={(e) =>
              set("category", e.target.value as GarmentInfo["category"])
            }
          >
            {Object.entries(categories).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>의류 종류</span>
          <select
            value={value.garment_type}
            onChange={(e) => set("garment_type", e.target.value)}
          >
            {garmentTypes.map((kind) => (
              <option key={kind} value={kind}>
                {kind === "unknown" ? "미확인" : kind}
              </option>
            ))}
          </select>
        </label>
      </div>
      <h3>의류 치수</h3>
      <p className="helper">
        이미지에 없는 치수는 추가하지 않습니다. 단위·단면/둘레·의류/신체 권장
        치수를 확인해 주세요.
      </p>
      {value.measurements.map((m, index) => (
        <div className="measurement-row" key={index}>
          <label className="field">
            항목
            <input
              aria-label={`치수 ${index + 1} 항목`}
              value={m.label}
              maxLength={80}
              onChange={(e) => measurement(index, { label: e.target.value })}
            />
          </label>
          <label className="field">
            사이즈
            <input
              aria-label={`치수 ${index + 1} 사이즈`}
              value={m.size ?? ""}
              maxLength={30}
              onChange={(e) =>
                measurement(index, { size: e.target.value || null })
              }
            />
          </label>
          <label className="field">
            값
            <input
              type="number"
              step="0.1"
              min={0}
              max={10000}
              aria-label={`치수 ${index + 1} 값`}
              value={m.value ?? ""}
              onChange={(e) =>
                measurement(index, {
                  value: e.target.value === "" ? null : Number(e.target.value),
                })
              }
            />
          </label>
          <label className="field">
            단위
            <select
              aria-label={`치수 ${index + 1} 단위`}
              value={m.unit}
              onChange={(e) =>
                measurement(index, {
                  unit: e.target.value as Measurement["unit"],
                })
              }
            >
              {["unknown", "cm", "mm", "inch"].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
          <label className="field">
            의미
            <select
              aria-label={`치수 ${index + 1} 의미`}
              value={m.kind}
              onChange={(e) =>
                measurement(index, {
                  kind: e.target.value as Measurement["kind"],
                })
              }
            >
              {Object.entries({
                unknown: "미확인",
                flat: "단면",
                circumference: "둘레",
                length: "길이",
              }).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            대상
            <select
              aria-label={`치수 ${index + 1} 대상`}
              value={m.target}
              onChange={(e) =>
                measurement(index, {
                  target: e.target.value as Measurement["target"],
                })
              }
            >
              {Object.entries({
                unknown: "미확인",
                garment: "의류 실측",
                body: "신체 권장",
              }).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="button secondary"
            aria-label={`치수 ${index + 1} 삭제`}
            onClick={() =>
              set(
                "measurements",
                value.measurements.filter((_, i) => i !== index),
              )
            }
          >
            삭제
          </button>
        </div>
      ))}
      <button
        type="button"
        className="button secondary"
        onClick={() =>
          set("measurements", [
            ...value.measurements,
            {
              label: "",
              size: null,
              value: null,
              unit: "unknown",
              kind: "unknown",
              target: "unknown",
              source: "user_entered",
            },
          ])
        }
      >
        치수 추가
      </button>
      <h3>소재 구성</h3>
      {value.composition.map((c, index) => (
        <div className="composition-row" key={index}>
          <label className="field">
            소재명
            <input
              aria-label={`소재 ${index + 1} 이름`}
              required
              value={c.name}
              maxLength={60}
              onChange={(e) =>
                set(
                  "composition",
                  value.composition.map((row, i) =>
                    i === index
                      ? { ...row, name: e.target.value, source: "user_entered" }
                      : row,
                  ),
                )
              }
            />
          </label>
          <label className="field">
            혼용률 (%)
            <input
              aria-label={`소재 ${index + 1} 혼용률`}
              type="number"
              min={0}
              max={100}
              step="0.1"
              value={c.percent ?? ""}
              onChange={(e) =>
                set(
                  "composition",
                  value.composition.map((row, i) =>
                    i === index
                      ? {
                          ...row,
                          percent:
                            e.target.value === ""
                              ? null
                              : Number(e.target.value),
                          source: "user_entered",
                        }
                      : row,
                  ),
                )
              }
            />
          </label>
          <button
            type="button"
            className="button secondary"
            aria-label={`소재 ${index + 1} 삭제`}
            onClick={() =>
              set(
                "composition",
                value.composition.filter((_, i) => i !== index),
              )
            }
          >
            삭제
          </button>
        </div>
      ))}
      {value.composition.length &&
      (percentages.some((n) => n === null) || Math.abs(total - 100) > 0.1) ? (
        <p className="helper">
          혼용률 합계 {total}% · 100%인지, 겉감/안감이 섞이지 않았는지 확인해
          주세요.
        </p>
      ) : null}
      <button
        type="button"
        className="button secondary"
        onClick={() =>
          set("composition", [
            ...value.composition,
            { name: "", percent: null, source: "user_entered" },
          ])
        }
      >
        소재 추가
      </button>
    </fieldset>
  );
}
