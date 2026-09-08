// This must run without Next.js hydration: file:// cannot load its module/data requests.
export const localFileNoticeScript = `if (location.protocol === "file:") {
  document.getElementById("local-file-notice").hidden = false;
  document.getElementById("report-app").hidden = true;
}`;

export function LocalFileNotice() {
  return (
    <>
      <aside id="local-file-notice" hidden style={{ maxWidth: 750, margin: "40px auto", padding: 24, lineHeight: 1.8 }}>
        <h1>この出力はWebサーバー経由で開いてください</h1>
        <p>HTMLファイルを直接開くと、ブラウザの制約でレポートのデータを読み込めません。</p>
        <p>
          展開した出力フォルダーで次のコマンドを実行し、表示されたサーバーをブラウザで開いてください（Pythonが必要です）。
        </p>
        <pre>python -m http.server 3000 --bind 127.0.0.1</pre>
        <p>
          <a href="http://localhost:3000/">http://localhost:3000/ を開く</a>
        </p>
        <p>または、出力フォルダー一式をWebサーバーへ配置してください。HTMLだけでなく付属ファイルも必要です。</p>
        <p>serverless版の「単一HTMLレポート」と、本体のWeb向け静的出力は異なる形式です。</p>
      </aside>
      {/* biome-ignore lint/security/noDangerouslySetInnerHtml: fixed source code, no user input; must run before hydration */}
      <script dangerouslySetInnerHTML={{ __html: localFileNoticeScript }} />
    </>
  );
}
