// 管理画面が 1 回の Server Action で受け取る本文の上限（大きな CSV からのレポート作成、#804）。
// next.config.ts の serverActions.bodySizeLimit と proxyClientMaxBodySize（少し大きくする）をこの値から決める。
// middleware（Basic 認証）は全パスで走り、Next はそのために本文を複製してメモリに持つので、
// 1 リクエストあたり上限の 2 倍程度のメモリを使いうる。上限を上げるときはコンテナのメモリと合わせて決める。
export const SERVER_ACTION_BODY_SIZE_LIMIT_MB = 100;
export const SERVER_ACTION_BODY_SIZE_LIMIT = `${SERVER_ACTION_BODY_SIZE_LIMIT_MB}mb` as const;
// Next（bytes パッケージ）は 1mb = 1024 * 1024 バイトとして解釈する
export const SERVER_ACTION_BODY_SIZE_LIMIT_BYTES = SERVER_ACTION_BODY_SIZE_LIMIT_MB * 1024 * 1024;
// middleware に渡すための本文の複製の上限（proxyClientMaxBodySize）。Server Action の上限と同じ値だと、
// 上限を超えた本文がちょうど上限の長さに切り詰められて Server Action の検査を通り、原因の分からない
// JSON の解析エラーになる。1mb だけ大きくして、超えた本文は Server Action 側の上限検査
// （ログに「Body exceeded 100mb limit」）で弾かせる。
export const PROXY_CLIENT_MAX_BODY_SIZE = `${SERVER_ACTION_BODY_SIZE_LIMIT_MB + 1}mb` as const;

/** 文字列を UTF-8 にしたときのバイト数（巨大な文字列でもコピーを作らずに数える）。 */
export function utf8ByteLength(text: string): number {
  let bytes = 0;
  for (let i = 0; i < text.length; i++) {
    const code = text.charCodeAt(i);
    if (code < 0x80) {
      bytes += 1;
    } else if (code < 0x800) {
      bytes += 2;
    } else if (code >= 0xd800 && code <= 0xdbff && i + 1 < text.length) {
      const next = text.charCodeAt(i + 1);
      if (next >= 0xdc00 && next <= 0xdfff) {
        bytes += 4;
        i++;
      } else {
        bytes += 3;
      }
    } else {
      bytes += 3;
    }
  }
  return bytes;
}

/** Server Action に引数 1 つを渡すときの本文のおおよそのバイト数（ブラウザは JSON.stringify([args]) を送る）。 */
export function estimateServerActionBodyBytes(arg: unknown): number {
  return utf8ByteLength(JSON.stringify([arg]));
}
