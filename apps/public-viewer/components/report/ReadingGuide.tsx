"use client";

import { useMessages } from "@/lib/i18n/LanguageContext";

/**
 * 本体・serverlessで読み方を揃える。変更時は相互PRで文言を確認する (#696)。
 * 日本語の文言は lib/i18n/messages.ts の `ja` にあり、英語・韓国語はその訳。
 */
export function ReadingGuide() {
  const messages = useMessages();
  return (
    <aside
      aria-label={messages.readingGuideLabel}
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
      <p style={{ margin: 0 }}>{messages.readingGuideLead}</p>
      <details style={{ marginTop: 8 }}>
        <summary style={{ cursor: "pointer", fontWeight: 600 }}>{messages.readingGuideSummary}</summary>
        <ul style={{ listStyleType: "disc", paddingLeft: 24, margin: "8px 0 0" }}>
          {messages.readingGuideItems.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </details>
    </aside>
  );
}
