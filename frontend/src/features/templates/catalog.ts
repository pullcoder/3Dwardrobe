// 직접 제작한 의류 셸의 정규화 계약. 사진 분석기는 이 계약만 전달하면 된다.
export type TemplateCategory = "top" | "pants" | "outer";
export type TemplateId =
  "short_tshirt" | "long_tshirt" | "jeans" | "slacks" | "zip_hoodie" | "jacket";
export interface ParameterDefinition {
  key: string;
  label: string;
  min: number;
  max: number;
  initial: number;
}
export interface TemplateDefinition {
  id: TemplateId;
  category: TemplateCategory;
  name: string;
  color: string;
  parameters: ParameterDefinition[];
}
const parameter = (
  key: string,
  label: string,
  min: number,
  max: number,
  initial = 0.5,
): ParameterDefinition => ({ key, label, min, max, initial });
const top = (long: boolean, outer: boolean) => [
  parameter("length", "총장", outer ? 0.6 : 0.5, outer ? 0.86 : 0.82, 0.45),
  parameter("shoulderWidth", "어깨너비", 0.46, 0.58, 0.35),
  parameter(
    outer ? "bodyWidth" : "chestWidth",
    outer ? "몸통 폭" : "가슴 폭",
    0.32,
    0.54,
    0.4,
  ),
  parameter(
    "sleeveLength",
    "소매 길이",
    long ? 0.45 : 0.18,
    long ? 0.67 : 0.32,
    0.5,
  ),
];
const pants = (wide: boolean) => [
  parameter("waistWidth", "허리 폭", 0.27, 0.46, 0.3),
  parameter("hipWidth", "엉덩이 폭", 0.35, 0.56, 0.3),
  parameter("rise", "밑위", 0.22, 0.38, 0.45),
  parameter("thighWidth", "허벅지 폭", 0.15, 0.3, wide ? 0.55 : 0.3),
  parameter("legLength", "바지 길이", 0.76, 1.04, 0.65),
  parameter("hemWidth", "밑단 폭", 0.13, 0.3, wide ? 0.55 : 0.25),
];
export const templateCatalog: readonly TemplateDefinition[] = [
  {
    id: "short_tshirt",
    category: "top",
    name: "반팔 티셔츠",
    color: "#649fa9",
    parameters: top(false, false),
  },
  {
    id: "long_tshirt",
    category: "top",
    name: "긴팔 티셔츠",
    color: "#d2ad87",
    parameters: top(true, false),
  },
  {
    id: "jeans",
    category: "pants",
    name: "청바지",
    color: "#365773",
    parameters: pants(false),
  },
  {
    id: "slacks",
    category: "pants",
    name: "슬랙스",
    color: "#58616a",
    parameters: pants(true),
  },
  {
    id: "zip_hoodie",
    category: "outer",
    name: "후드집업",
    color: "#79846d",
    parameters: top(true, true),
  },
  {
    id: "jacket",
    category: "outer",
    name: "재킷",
    color: "#7f647e",
    parameters: top(true, true),
  },
];
export interface TemplateInput {
  category: TemplateCategory;
  template: TemplateId | "wide_pants";
  parameters: Record<string, number>;
}
export interface ResolvedTemplateInput extends Omit<TemplateInput, "template"> {
  template: TemplateId;
}
export function templateDefinition(id: TemplateId) {
  const result = templateCatalog.find((item) => item.id === id);
  if (!result) throw new Error("지원하지 않는 의류 템플릿입니다.");
  return result;
}
export function defaultTemplateInput(id: TemplateId): ResolvedTemplateInput {
  const definition = templateDefinition(id);
  return {
    category: definition.category,
    template: id,
    parameters: Object.fromEntries(
      definition.parameters.map((p) => [p.key, p.initial]),
    ),
  };
}
export function resolveTemplateInput(value: unknown): ResolvedTemplateInput {
  if (!value || typeof value !== "object")
    throw new Error("의류 파라미터가 필요합니다.");
  const input = value as Partial<TemplateInput>;
  const id = input.template === "wide_pants" ? "slacks" : input.template;
  if (!id || !templateCatalog.some((item) => item.id === id))
    throw new Error("지원하지 않는 의류 템플릿입니다.");
  const result = defaultTemplateInput(id);
  if (input.category !== result.category)
    throw new Error("의류 종류와 템플릿이 일치하지 않습니다.");
  if (
    !input.parameters ||
    typeof input.parameters !== "object" ||
    Array.isArray(input.parameters)
  )
    throw new Error("형태 조절 값이 필요합니다.");
  if (input.template === "wide_pants")
    Object.assign(result.parameters, { thighWidth: 0.75, hemWidth: 0.75 });
  for (const [key, v] of Object.entries(input.parameters)) {
    if (
      !Object.hasOwn(result.parameters, key) ||
      typeof v !== "number" ||
      !Number.isFinite(v) ||
      v < 0 ||
      v > 1
    )
      throw new Error("형태 조절 값은 지원 항목의 0~1 사이 숫자여야 합니다.");
    result.parameters[key] = v;
  }
  return result;
}
export function physicalParameters(input: ResolvedTemplateInput) {
  return Object.fromEntries(
    templateDefinition(input.template).parameters.map((p) => [
      p.key,
      p.min + (p.max - p.min) * input.parameters[p.key],
    ]),
  );
}
