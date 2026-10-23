const ATTRIBUTE_PREFIX = "attribute_";

/**
 * 選択された属性列名から、送信する属性キー（attribute_<列名>）を作る。
 *
 * スプレッドシート API（GET /admin/spreadsheet/data）とプラグインは、属性列を既に
 * attribute_<列名> の形で返す。そこへ重ねて付けると attribute_attribute_<列名> になり、
 * 公開レポートの属性名に attribute_ が残る。API 側（spreadsheet.py）と同じく、
 * 既に付いていれば付けない。
 */
export function toAttributeKey(column: string): string {
  return column.startsWith(ATTRIBUTE_PREFIX) ? column : `${ATTRIBUTE_PREFIX}${column}`;
}
