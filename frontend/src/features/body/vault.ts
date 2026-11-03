import { measurementFields } from "../../types/domain";
import type { Measurements } from "../../types/domain";
import { validateMeasurements } from "./measurements";
import type { BodyProfiles, BodyProfile, PoseSummary } from "./types";

const prefix = "stylefit.body.v1.";
const iterations = 310_000;
const encoder = new TextEncoder();
const asBase64 = (bytes: Uint8Array) => btoa(String.fromCharCode(...bytes));
const fromBase64 = (text: string) =>
  Uint8Array.from(atob(text), (char) => char.charCodeAt(0));

function parseProfile(input: unknown): BodyProfile {
  if (!input || typeof input !== "object")
    throw new Error("체형 데이터 형식이 올바르지 않습니다.");
  const profile = input as BodyProfile;
  if (!profile.values || !profile.origins)
    throw new Error("체형 데이터 형식이 올바르지 않습니다.");
  const values = {} as Measurements;
  const origins: BodyProfile["origins"] = {};
  for (const { key } of measurementFields) {
    if (
      typeof profile.values[key] !== "string" ||
      profile.values[key].length > 12
    )
      throw new Error("치수 형식이 올바르지 않습니다.");
    values[key] = profile.values[key];
    const origin = profile.origins[key];
    if (
      origin !== undefined &&
      origin !== "estimated" &&
      origin !== "user_entered"
    )
      throw new Error("치수 출처가 올바르지 않습니다.");
    if (origin) origins[key] = origin;
  }
  const error = validateMeasurements(values);
  if (error) throw new Error(error);
  let ratios: PoseSummary | undefined;
  if (profile.ratios) {
    const candidate = profile.ratios;
    if (
      candidate.method !== "projected_2d_v1" ||
      ["shoulder", "arm", "leg", "torso", "mean_visibility"].some(
        (key) =>
          !Number.isFinite(candidate[key as keyof PoseSummary]) ||
          Number(candidate[key as keyof PoseSummary]) <= 0 ||
          Number(candidate[key as keyof PoseSummary]) > 1,
      )
    )
      throw new Error("분석 비율 형식이 올바르지 않습니다.");
    ratios = {
      shoulder: candidate.shoulder,
      arm: candidate.arm,
      leg: candidate.leg,
      torso: candidate.torso,
      mean_visibility: candidate.mean_visibility,
      method: candidate.method,
    };
  }
  return {
    values,
    origins,
    ratios,
    saved_at:
      typeof profile.saved_at === "string" &&
      Number.isFinite(Date.parse(profile.saved_at))
        ? profile.saved_at
        : undefined,
  };
}

export function cleanProfiles(input: unknown): BodyProfiles {
  if (!input || typeof input !== "object")
    throw new Error("저장 데이터 형식이 올바르지 않습니다.");
  const profiles = input as BodyProfiles;
  return {
    photo: parseProfile(profiles.photo),
    manual: parseProfile(profiles.manual),
  };
}

async function vaultKey(alias: string) {
  if (!globalThis.crypto?.subtle)
    throw new Error(
      "기기 암호화 저장은 HTTPS 또는 localhost에서 Web Crypto를 지원하는 브라우저가 필요합니다.",
    );
  if (!alias.trim() || alias.trim().length > 80)
    throw new Error("보관함 이름을 1~80자로 입력해 주세요.");
  const hash = await crypto.subtle.digest(
    "SHA-256",
    encoder.encode(alias.trim()),
  );
  return (
    prefix +
    Array.from(new Uint8Array(hash), (byte) =>
      byte.toString(16).padStart(2, "0"),
    ).join("")
  );
}

async function deriveKey(password: string, salt: Uint8Array<ArrayBuffer>) {
  if (password.length < 12)
    throw new Error(
      "암호는 12자 이상 입력해 주세요. 암호를 잊으면 복구할 수 없습니다.",
    );
  const material = await crypto.subtle.importKey(
    "raw",
    encoder.encode(password),
    "PBKDF2",
    false,
    ["deriveKey"],
  );
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", salt, iterations, hash: "SHA-256" },
    material,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  );
}

async function decode(raw: string, password: string): Promise<BodyProfiles> {
  try {
    if (raw.length > 30000) throw new Error();
    const data = JSON.parse(raw);
    if (data.version !== 1 || data.iterations !== iterations) throw new Error();
    const salt = fromBase64(data.salt),
      iv = fromBase64(data.iv);
    if (salt.length !== 16 || iv.length !== 12) throw new Error();
    const key = await deriveKey(password, salt);
    const plain = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv },
      key,
      fromBase64(data.ciphertext),
    );
    return cleanProfiles(JSON.parse(new TextDecoder().decode(plain)));
  } catch {
    throw new Error(
      "보관함 이름·암호가 다르거나 저장 데이터가 손상되었습니다.",
    );
  }
}

export async function saveBodyVault(
  alias: string,
  password: string,
  profiles: BodyProfiles,
) {
  const storageKey = await vaultKey(alias);
  const existing = localStorage.getItem(storageKey);
  if (existing) await decode(existing, password);
  const salt = crypto.getRandomValues(new Uint8Array(16)),
    iv = crypto.getRandomValues(new Uint8Array(12));
  const key = await deriveKey(password, salt);
  const encrypted = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    key,
    encoder.encode(JSON.stringify(cleanProfiles(profiles))),
  );
  localStorage.setItem(
    storageKey,
    JSON.stringify({
      version: 1,
      iterations,
      salt: asBase64(salt),
      iv: asBase64(iv),
      ciphertext: asBase64(new Uint8Array(encrypted)),
    }),
  );
}

export async function loadBodyVault(alias: string, password: string) {
  const raw = localStorage.getItem(await vaultKey(alias));
  if (!raw) throw new Error("해당 이름의 체형 보관함이 없습니다.");
  return decode(raw, password);
}

export async function deleteBodyVault(alias: string, password: string) {
  const key = await vaultKey(alias);
  const raw = localStorage.getItem(key);
  if (!raw) throw new Error("해당 이름의 체형 보관함이 없습니다.");
  await decode(raw, password);
  localStorage.removeItem(key);
}
