import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
const python =
  process.env.STYLEFIT_TEST_PYTHON ||
  fileURLToPath(
    new URL(
      process.platform === "win32"
        ? "../../backend/.venv/Scripts/python.exe"
        : "../../backend/.venv/bin/python",
      import.meta.url,
    ),
  );
const script = fileURLToPath(
  new URL("../../backend/scripts/verify_garment_ai.py", import.meta.url),
);
const result = spawnSync(python, [script, "--fixtures-only"], {
  stdio: "inherit",
});
process.exit(result.status ?? 1);
