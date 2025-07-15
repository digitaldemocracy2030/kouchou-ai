import { exec } from "node:child_process";
import { dirname, join } from "node:path";
import { PassThrough } from "node:stream";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import archiver from "archiver";
import express from "express";

const execAsync = promisify(exec);
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const clientDir = join(__dirname, "../../client");
const outDir = join(clientDir, "out");

const ZIP_FILE_NAME = "kouchou-ai.zip";

const app = express();

app.use(express.json());

app.post("/build", async (req, res) => {
  try {
    console.log("Build request received");
    const { stdout, stderr } = await execAsync("npm run build:static", {
      cwd: clientDir,
      env: {
        ...process.env,
        PATH: process.env.PATH ?? "",
        NODE_ENV: "production",
        BUILD_SLUGS: req.body.slugs || ""
      },
    });

    console.log("Build stdout:", stdout);
    if (stderr) console.warn("Build stderr:", stderr);

    const archive = archiver("zip", { zlib: { level: 9 } });
    const zipStream = new PassThrough();

    res.setHeader("Content-Type", "application/zip");
    res.setHeader("Content-Disposition", `attachment; filename=${ZIP_FILE_NAME}`);

    archive.pipe(zipStream).pipe(res);

    archive.directory(outDir, false);
    await archive.finalize();
  } catch (err) {
    console.error("Build or Zip error:", err);
    res.status(500).json({
      status: "error",
      message: err instanceof Error ? err.message : String(err),
    });
  }
});

app.get("/healthcheck", (req, res) => {
  res.status(200).json({ status: "ok" });
});

const PORT = 3200;
app.listen(PORT, () => {
  console.log(`✅ Server is running on http://localhost:${PORT}`);
});
