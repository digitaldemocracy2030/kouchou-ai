import { localFileNoticeScript } from "./LocalFileNotice";

it.each(["file:", "http:", "https:"])("%s のときだけ非同期読込に依存しない案内を出す", (protocol) => {
  document.body.innerHTML = '<div id="report-app">loading</div><aside id="local-file-notice" hidden>help</aside>';
  const run = new Function("location", "document", localFileNoticeScript);
  run({ protocol }, document);
  expect(document.getElementById("local-file-notice")?.hidden).toBe(protocol !== "file:");
  expect(document.getElementById("report-app")?.hidden).toBe(protocol === "file:");
});
