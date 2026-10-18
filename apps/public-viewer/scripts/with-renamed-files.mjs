import { spawn } from "node:child_process";
import { renameFiles, restoreFiles } from "./rename-file.mjs";

// ビルド対象から外すファイルを改名してからコマンドを実行し、成否にかかわらず必ず元に戻す。
// pre/post スクリプトで改名・復元すると、ビルドが失敗したときに post が走らず、
// 改名されたファイルが作業ツリーに残ってしまうため。
// 使い方: node scripts/with-renamed-files.mjs <command> [...args]
const [command, ...args] = process.argv.slice(2);

if (!command) {
  console.error("Usage: node scripts/with-renamed-files.mjs <command> [...args]");
  process.exit(1);
}

function run() {
  return new Promise((resolvePromise) => {
    const child = spawn(command, args, { stdio: "inherit", shell: process.platform === "win32" });
    // Ctrl+C などのシグナルは子プロセスに任せ、こちらは復元まで生き残る
    const forward = (signal) => child.kill(signal);
    process.on("SIGINT", forward);
    process.on("SIGTERM", forward);
    child.on("error", (error) => {
      console.error(`Failed to run ${command}: ${error.message}`);
      resolvePromise(1);
    });
    child.on("exit", (code, signal) => {
      process.off("SIGINT", forward);
      process.off("SIGTERM", forward);
      resolvePromise(code ?? (signal ? 1 : 0));
    });
  });
}

let exitCode = 1;
try {
  await renameFiles();
  exitCode = await run();
} finally {
  await restoreFiles();
}
process.exit(exitCode);
