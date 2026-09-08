// Minimal Japanese line-breaking rules for plain text rendered inside Plotly SVG.
const opening = new Set(Array.from("（［｛〈《「『【〔([{“‘"));
const closing = new Set(
  Array.from("、。，．？！：；）］｝〉》」』】〕)]}!?.,:;ー々ぁぃぅぇぉっゃゅょァィゥェォッャュョヵヶ”’"),
);
const segmenter = new Intl.Segmenter("ja", { granularity: "grapheme" });

export function wrapJapaneseText(text: string, width = 30): string {
  const limit = Number.isFinite(width) ? Math.max(1, Math.floor(width)) : 30;
  return text
    .split(/\r?\n/)
    .map((paragraph) => {
      const chars = Array.from(segmenter.segment(paragraph), (part) => part.segment);
      const lines: string[] = [];
      let start = 0;
      while (start < chars.length) {
        let end = Math.min(start + limit, chars.length);
        if (end < chars.length) {
          while (end > start && (opening.has(chars[end - 1]) || closing.has(chars[end]))) end--;
          // A run of punctuation may exceed the target width; never split a grapheme.
          if (end === start) {
            end = Math.min(start + limit, chars.length);
            while (end < chars.length && (opening.has(chars[end - 1]) || closing.has(chars[end]))) end++;
          }
        }
        lines.push(chars.slice(start, end).join(""));
        start = end;
      }
      return lines.join("\n");
    })
    .join("\n")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\n", "<br />");
}
