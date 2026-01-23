/**
 * 各カラムの文字数の平均と分散から、最適なコメントカラムのスコアを計算する
 * score = 平均文字数 + k * 文字数の分散
 */

/**
 * 配列の平均値を計算
 */
function calculateMean(values: number[]): number {
  if (values.length === 0) return 0;
  const sum = values.reduce((acc, val) => acc + val, 0);
  return sum / values.length;
}

/**
 * 配列の分散を計算
 */
function calculateVariance(values: number[]): number {
  if (values.length <= 1) return 0;
  const mean = calculateMean(values);
  const squaredDifferences = values.map((value) => (value - mean) ** 2);
  return calculateMean(squaredDifferences);
}

/**
 * 文字列の配列から、最適なコメントカラムを選択する、駄目だったらスコア計算からカラムを返す
 * 各カラムのスコアを計算し、スコアが最も高いカラムを返す
 * score = 平均文字数 + k * 文字数の分散
 * 自由入力文の場合、文字数が多くなり、また、分散も大きくなるため、スコアが高くなる
 * 選択肢やログ、IDなどの場合、文字数が少なく、分散も小さくなるため、スコアが低くなる
 * @param data パースされたCSVデータ
 * @param k 分散に掛ける係数（デフォルト: 2.0）
 * @returns スコアが最も高いカラム名
 */
export function getBestCommentColumn(data: Record<string, unknown>[], k = 2.0): string | null {
  if (data.length === 0) return null;

  const columns = Object.keys(data[0]);

  // コメントだと認識されるデフォルトカラム
  const defaultCommentColumns = [
    "comment",
    "コメント",
    "意見",
    "要望",
    "内容",
    "フィードバック",
    "feedback",
    "ポスト",
    "投稿",
    "post",
    "レビュー",
    "review",
    "感想",
  ];

  // デフォルトカラム名が部分一致するか確認
  const foundDefaultColumns = columns.filter((col) =>
    defaultCommentColumns.some((defaultCol) => col.toLowerCase().includes(defaultCol.toLowerCase())),
  );
  // デフォルトカラムが1つだけ見つかった場合はそれを返す
  if (foundDefaultColumns.length === 1) {
    return foundDefaultColumns[0];
  }

  // デフォルトカラムがない or 候補が2つ以上の場合は、文字数と分散に基づいてスコア計算
  let bestColumn = null;
  let highestScore = -1;

  for (const column of columns) {
    // 各行のこのカラムの値の文字数を取得
    const charLengths = data
      .map((row) => {
        const value = row[column];
        if (typeof value !== "string" || !value) return 0;
        return value.length;
      })
      .filter((length) => length > 0); // 空の値を除外

    if (charLengths.length === 0) continue;

    // 平均と分散を計算
    const mean = calculateMean(charLengths);
    const variance = calculateVariance(charLengths);

    // スコアを計算: 平均 + k * 分散
    const score = mean + k * variance;

    if (score > highestScore) {
      highestScore = score;
      bestColumn = column;
    }
  }

  return bestColumn;
}
