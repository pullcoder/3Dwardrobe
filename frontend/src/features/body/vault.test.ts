import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { createBodyProfiles } from "./measurements";
import {
  cleanProfiles,
  deleteBodyVault,
  loadBodyVault,
  saveBodyVault,
} from "./vault";

let memory: Map<string, string>;
beforeEach(() => {
  memory = new Map();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => memory.get(key) ?? null,
    setItem: (key: string, value: string) => memory.set(key, value),
    removeItem: (key: string) => memory.delete(key),
  });
});
afterEach(() => vi.unstubAllGlobals());

test("이름과 암호가 다른 보관함을 복호화하거나 덮어쓰지 못한다", async () => {
  const profiles = createBodyProfiles();
  profiles.manual.values.height = "171";
  profiles.photo.values.height = "183";
  await saveBodyVault("person-a", "long-password-for-a", profiles);
  const raw = [...memory.values()][0];
  expect(raw).not.toContain("height");
  expect(raw).not.toContain("long-password-for-a");
  await expect(
    loadBodyVault("person-b", "long-password-for-a"),
  ).rejects.toThrow(/없습니다/);
  await expect(
    saveBodyVault("person-a", "another-password", createBodyProfiles()),
  ).rejects.toThrow(/암호/);
  expect([...memory.values()][0]).toBe(raw);
  const restored = await loadBodyVault("person-a", "long-password-for-a");
  expect(restored.manual.values.height).toBe("171");
  expect(restored.photo.values.height).toBe("183");
  await deleteBodyVault("person-a", "long-password-for-a");
  expect(memory.size).toBe(0);
});

test("원본 사진·좌표 등 허용하지 않은 필드는 저장하지 않는다", () => {
  const data = createBodyProfiles();
  const extra = {
    ...data,
    photo: {
      ...data.photo,
      original_photo: "private",
      landmarks: [{ x: 0.5, y: 0.5, z: 0 }],
    },
  };
  const cleaned = JSON.stringify(cleanProfiles(extra));
  expect(cleaned).not.toContain("private");
  expect(cleaned).not.toContain("landmarks");
});

test("변조된 암호문을 복원하지 않는다", async () => {
  await saveBodyVault("owner", "private-password-12", createBodyProfiles());
  const key = [...memory.keys()][0],
    raw = JSON.parse(memory.get(key)!);
  raw.ciphertext = "A" + raw.ciphertext.slice(1);
  // 첫 문자가 우연히 같아지는 경우를 피한다.
  if (raw.ciphertext === JSON.parse(memory.get(key)!).ciphertext)
    raw.ciphertext = "B" + raw.ciphertext.slice(1);
  memory.set(key, JSON.stringify(raw));
  await expect(loadBodyVault("owner", "private-password-12")).rejects.toThrow(
    /손상/,
  );
});
