import pptxgen from "pptxgenjs";
import type { DeckData } from "./deckData";

const colors = { ink: "172C3D", accent: "086C72", muted: "415A71" };

function shorten(text: string, limit: number) {
  const characters = Array.from(text);
  return characters.length <= limit ? text : `${characters.slice(0, limit - 1).join("")}…`;
}

export function makeReportUrl(viewer: string, origin: string, slug: string): URL | undefined {
  try {
    const base = origin ? new URL(viewer || "/", origin) : new URL(viewer);
    if (base.protocol !== "https:" && base.protocol !== "http:") return;
    return new URL(`${base.pathname.replace(/\/+$/, "")}/${encodeURIComponent(slug)}`, base.origin);
  } catch {
    return;
  }
}

export type CoverImage = { data: string; width: number; height: number };

export function createPowerPoint(data: DeckData, reportUrl?: URL, cover?: CoverImage) {
  const deck = new pptxgen();
  deck.layout = "LAYOUT_WIDE";
  deck.author = "広聴AI";
  deck.title = data.title;
  deck.theme = { headFontFace: "Yu Gothic", bodyFontFace: "Yu Gothic" };

  const opening = deck.addSlide();
  opening.addText(shorten(data.title, 100), {
    x: 0.7,
    y: 0.85,
    w: cover ? 5.1 : 11.9,
    h: 2.4,
    fontSize: 31,
    bold: true,
    color: colors.ink,
  });
  const counts = [`抽出意見 ${data.opinionCount.toLocaleString("ja-JP")}件`];
  if (data.inputCount !== undefined) counts.unshift(`入力コメント ${data.inputCount.toLocaleString("ja-JP")}件`);
  opening.addText(counts.join("\n"), { x: 0.7, y: 3.55, w: 5.2, h: 1.3, fontSize: 19, color: colors.muted });
  if (cover) {
    const scale = Math.min(6.55 / cover.width, 5.9 / cover.height);
    const w = cover.width * scale;
    const h = cover.height * scale;
    opening.addImage({
      data: cover.data,
      x: 6.1 + (6.55 - w) / 2,
      y: 0.8 + (5.9 - h) / 2,
      w,
      h,
      altText: "論点の概念図",
    });
  }
  if (reportUrl) addLink(opening, reportUrl, "元レポートを開く");

  if (data.question || data.overview) {
    const overview = deck.addSlide();
    heading(overview, "分析の概要");
    if (data.question) {
      overview.addText(shorten(data.question, 160), { x: 0.8, y: 1.35, w: 11.75, h: 1.1, fontSize: 19, bold: true });
    }
    if (data.overview) {
      overview.addText(shorten(data.overview, 500), {
        x: 0.8,
        y: data.question ? 2.55 : 1.45,
        w: 11.75,
        h: data.question ? 3.8 : 4.9,
        fontSize: 18,
        valign: "top",
        color: colors.ink,
      });
    }
    if (reportUrl) addLink(overview, reportUrl, "元レポートを開く");
  }

  for (const topic of data.topics) {
    const slide = deck.addSlide();
    heading(slide, shorten(topic.label, 88));
    slide.addText(`抽出意見 ${topic.count.toLocaleString("ja-JP")}件`, {
      x: 0.8,
      y: 1.25,
      w: 11.75,
      h: 0.48,
      bold: true,
      fontSize: 19,
      color: colors.accent,
    });
    if (topic.takeaway) {
      slide.addText(shorten(topic.takeaway, 215), {
        x: 0.8,
        y: 1.88,
        w: 11.75,
        h: 1.75,
        fontSize: 18,
        valign: "top",
        color: colors.ink,
      });
    }
    if (topic.examples.length) {
      slide.addText("抽出意見の例", { x: 0.8, y: 3.7, w: 11.75, h: 0.42, fontSize: 17, bold: true, color: colors.ink });
      topic.examples.forEach((example, index) => {
        slide.addText(shorten(example, 100), {
          x: 0.95,
          y: 4.15 + index * 0.68,
          w: 11.55,
          h: 0.64,
          fontSize: 16,
          valign: "top",
          color: colors.muted,
        });
      });
    }
    if (reportUrl) {
      const topicUrl = new URL(reportUrl);
      topicUrl.searchParams.set("topic", topic.id);
      topicUrl.hash = "report-topic";
      addLink(slide, topicUrl, "元レポートでこの論点を読む");
    }
  }
  return deck;
}

const HEADING_BOX = { w: 11.9, h: 0.82 };
const HEADING_FONT_SIZES = [26, 24, 22, 20, 18, 16];

// 半角文字は全角の約半分の幅として、行数を多めに見積もる
function textWidthInEm(text: string) {
  return Array.from(text).reduce((width, character) => width + (/[\u0020-\u007e]/.test(character) ? 0.55 : 1), 0);
}

// PowerPoint は開いた時点で文字を自動縮小しないため、枠に収まる文字サイズを先に決める
export function fitHeading(text: string) {
  const normalized = text.replace(/\s+/g, " ").trim();
  const innerWidth = (HEADING_BOX.w - 0.2) * 72;
  const innerHeight = (HEADING_BOX.h - 0.1) * 72;
  for (const fontSize of HEADING_FONT_SIZES) {
    const maxLines = Math.floor(innerHeight / (fontSize * 1.2));
    const lines = Math.ceil((textWidthInEm(normalized) * fontSize) / innerWidth);
    if (maxLines >= 1 && lines <= maxLines) return { text: normalized, fontSize };
  }
  const fontSize = HEADING_FONT_SIZES[HEADING_FONT_SIZES.length - 1];
  const maxWidth = (innerWidth / fontSize) * Math.floor(innerHeight / (fontSize * 1.2)) - 1;
  const characters = Array.from(normalized);
  let width = 0;
  let end = 0;
  while (end < characters.length && width + textWidthInEm(characters[end]) <= maxWidth) {
    width += textWidthInEm(characters[end]);
    end++;
  }
  return { text: `${characters.slice(0, end).join("")}…`, fontSize };
}

function heading(slide: pptxgen.Slide, text: string) {
  const fitted = fitHeading(text);
  slide.addText(fitted.text, {
    x: 0.7,
    y: 0.35,
    ...HEADING_BOX,
    fontSize: fitted.fontSize,
    bold: true,
    color: colors.ink,
  });
}

function addLink(slide: pptxgen.Slide, url: URL, text: string) {
  slide.addText(text, {
    x: 0.8,
    y: 6.75,
    w: 11.7,
    h: 0.38,
    fontSize: 13,
    color: colors.accent,
    hyperlink: { url: url.href },
  });
}
