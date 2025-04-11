import { NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";
import fs from "fs";
import path from "path";
import { createReadStream } from "fs";


const execAsync = promisify(exec);

/**
 * 静的エクスポートを実行し、結果をZIPファイルとして返すAPIエンドポイント
 */
export async function GET() {
  try {
    const appRoot = path.resolve(process.cwd());
    
    console.log("Starting static export process...");
    
    const { stdout, stderr } = await execAsync("npm run build:static", {
      cwd: appRoot,
    });
    
    console.log("Static export stdout:", stdout);
    
    if (stderr && !stderr.includes("npm")) {
      console.error("Static export stderr:", stderr);
      return NextResponse.json(
        { error: "Static export failed", details: stderr },
        { status: 500 }
      );
    }
    
    const outDir = path.join(appRoot, "out");
    
    if (!fs.existsSync(outDir)) {
      return NextResponse.json(
        { error: "Static export failed - output directory not found" },
        { status: 500 }
      );
    }
    
    const zipFilePath = path.join(appRoot, "static_export.zip");
    
    if (fs.existsSync(zipFilePath)) {
      fs.unlinkSync(zipFilePath);
    }
    
    await execAsync(`cd ${outDir} && zip -r ${zipFilePath} .`);
    
    if (!fs.existsSync(zipFilePath)) {
      return NextResponse.json(
        { error: "Failed to create ZIP file" },
        { status: 500 }
      );
    }
    
    const fileStream = createReadStream(zipFilePath);
    
    const response = new NextResponse(fileStream as any);
    
    response.headers.set("Content-Type", "application/zip");
    response.headers.set("Content-Disposition", "attachment; filename=static_export.zip");
    
    setTimeout(() => {
      if (fs.existsSync(zipFilePath)) {
        fs.unlinkSync(zipFilePath);
        console.log("Temporary ZIP file deleted");
      }
    }, 5000); // Give enough time for the file to be sent
    
    return response;
  } catch (error) {
    console.error("Static export error:", error);
    return NextResponse.json(
      { error: "Static export failed", details: String(error) },
      { status: 500 }
    );
  }
}
