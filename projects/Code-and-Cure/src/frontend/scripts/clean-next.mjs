import fs from "node:fs/promises";
import path from "node:path";

const cwd = process.cwd();
const entriesToRemove = [".next"];

async function removeIfPresent(targetPath) {
  try {
    await fs.rm(targetPath, {
      force: true,
      recursive: true,
      maxRetries: 3,
      retryDelay: 150,
    });
  } catch (error) {
    if (error && error.code === "ENOENT") {
      return;
    }

    throw error;
  }
}

async function removeStaleBuildDirs() {
  const entries = await fs.readdir(cwd, { withFileTypes: true });

  for (const entry of entries) {
    if (!entry.isDirectory() || !entry.name.startsWith(".next.stale-")) {
      continue;
    }

    entriesToRemove.push(entry.name);
  }
}

await removeStaleBuildDirs();

for (const entry of entriesToRemove) {
  await removeIfPresent(path.join(cwd, entry));
}
