/** 本体・serverlessで読み方を揃える。変更時は相互PRで文言を確認する (#696)。 */
export function ReadingGuide() {
  return (
    <aside
      aria-label="レポートの読み方"
      style={{
        border: "1px solid #cbd5e1",
        borderRadius: 8,
        padding: 16,
        margin: "16px 0",
        background: "#f8fafc",
        color: "#1e293b",
        lineHeight: 1.7,
      }}
    >
      <p style={{ margin: 0 }}>
        このレポートは、集めた意見から論点や課題を見つけるためのものです。表示される件数は、社会全体の支持率を示すものではありません。
      </p>
      <details style={{ marginTop: 8 }}>
        <summary style={{ cursor: "pointer", fontWeight: 600 }}>レポートの読み方</summary>
        <ul style={{ listStyleType: "disc", paddingLeft: 24, margin: "8px 0 0" }}>
          <li>
            収集方法・対象・期間によって、含まれる声には偏りがあります。ここにない意見や、声を届けていない人の存在にも目を向けてください。
          </li>
          <li>
            1つのコメントから複数の意見が抽出されることがあります。意見数・コメント数を人数や賛成票数として扱わないでください。
          </li>
          <li>
            図の配置やグループ分けは、意見の内容を探索するための手がかりです。位置・距離・面積だけで重要度や合意の強さを判断しないでください。
          </li>
          <li>
            AIによる要約や分類には誤りや抜けがあり得ます。個々の意見を読み、必要に応じて収集元のコメントと照らし合わせてください。
          </li>
          <li>
            見つけた論点は結論ではなく、対話や追加調査の出発点です。少数の意見も読み、関係者への聞き取りや別の資料で確かめてください。
          </li>
        </ul>
      </details>
    </aside>
  );
}
