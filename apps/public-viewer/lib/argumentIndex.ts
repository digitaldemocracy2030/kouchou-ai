import type { Argument } from "@/type";

/**
 * フィルタ済み意見 ID の配列を、存在判定用の Set に変換する。
 * フィルタなし（undefined）はそのまま undefined を返し、「フィルタ未適用」と「0 件一致」を区別したまま扱う。
 * 配列の includes は 1 回 O(|F|) のため、全意見 N 件に対して呼ぶと O(N×|F|) になる。描画側はこの Set を使う。
 */
export function toIdSet(ids: readonly string[] | undefined): ReadonlySet<string> | undefined {
  return ids ? new Set(ids) : undefined;
}

/**
 * cluster_id → そのクラスタに属する意見の一覧、の索引を 1 回の走査で作る。
 * 各一覧の並びは argumentList の順序を保つ（`argumentList.filter((arg) => arg.cluster_ids.includes(id))` と同じ結果）。
 * cluster_ids に同じ ID が重複していても、同じ意見は 1 回だけ入る。
 */
export function groupArgumentsByCluster(argumentList: readonly Argument[]): Map<string, Argument[]> {
  const index = new Map<string, Argument[]>();
  for (const arg of argumentList) {
    for (const clusterId of arg.cluster_ids) {
      let list = index.get(clusterId);
      if (!list) {
        list = [];
        index.set(clusterId, list);
      }
      // 意見は argumentList の順に 1 件ずつ処理するので、重複 ID は末尾との比較で除ける
      if (list[list.length - 1] !== arg) list.push(arg);
    }
  }
  return index;
}

/**
 * 意見の一覧を、フィルタに合致するもの（matching）と合致しないもの（notMatching）に 1 回の走査で分ける。
 * フィルタなし（filteredIdSet が undefined）のときは、すべてを matching として返す。
 * どちらの一覧も入力の順序を保つ。
 */
export function splitArgumentsByFilter(
  argumentList: readonly Argument[],
  filteredIdSet: ReadonlySet<string> | undefined,
): { matching: Argument[]; notMatching: Argument[] } {
  if (!filteredIdSet) return { matching: [...argumentList], notMatching: [] };
  const matching: Argument[] = [];
  const notMatching: Argument[] = [];
  for (const arg of argumentList) {
    if (filteredIdSet.has(arg.arg_id)) matching.push(arg);
    else notMatching.push(arg);
  }
  return { matching, notMatching };
}
