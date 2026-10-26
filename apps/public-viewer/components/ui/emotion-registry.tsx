"use client";

import createCache from "@emotion/cache";
import { CacheProvider } from "@emotion/react";
import { useServerInsertedHTML } from "next/navigation";
import { useState } from "react";

type InsertedStyle = { name: string; isGlobal: boolean };

/**
 * Chakra UI（emotion）のサーバー描画のスタイルを、body の中ではなく head に出す（#1142）。
 *
 * キャッシュを渡さないと、emotion はサーバー描画で `<style data-emotion>` を要素の直前（body の中）に出し、
 * ブラウザでは `@emotion/react` を評価した時点でそれを head へ移す。Turbopack の本番ビルドではこの移動が
 * hydration の途中に起き、React が照合しようとしていた `<style>` が消えて hydration エラー #418 になる。
 *
 * `cache.compat = true` にすると emotion はスタイルを body に出さずキャッシュに貯めるので、
 * 描画のたびに新しく入ったものを useServerInsertedHTML で head に流す
 * （emotion の App Router 向けの方法。ブラウザの createCache は `data-emotion="css …"` を挿入済みとして扱う）。
 */
export function EmotionRegistry({ children }: { children: React.ReactNode }) {
  const [registry] = useState(() => {
    const cache = createCache({ key: "css" });
    cache.compat = true;
    let inserted: InsertedStyle[] = [];
    const insert = cache.insert;
    cache.insert = (...args) => {
      const [selector, serialized] = args;
      if (cache.inserted[serialized.name] === undefined) {
        // Global のスタイルは selector が空で渡される
        inserted.push({ name: serialized.name, isGlobal: !selector });
      }
      return insert(...args);
    };
    const flush = () => {
      const flushed = inserted;
      inserted = [];
      return flushed;
    };
    return { cache, flush };
  });

  useServerInsertedHTML(() => {
    const inserted = registry.flush();
    if (inserted.length === 0) return null;

    let styles = "";
    let dataEmotion = registry.cache.key;
    const globals: { name: string; style: string }[] = [];
    for (const { name, isGlobal } of inserted) {
      const style = registry.cache.inserted[name];
      if (typeof style !== "string") continue;
      if (isGlobal) {
        globals.push({ name, style });
      } else {
        styles += style;
        dataEmotion += ` ${name}`;
      }
    }

    return (
      <>
        {globals.map(({ name, style }) => (
          // ブラウザの Global は `data-emotion="css-global <name>"` の style を自分のものとして引き継ぐ
          <style
            key={name}
            data-emotion={`${registry.cache.key}-global ${name}`}
            // biome-ignore lint/security/noDangerouslySetInnerHtml: emotion が生成した CSS で、利用者の入力は含まない
            dangerouslySetInnerHTML={{ __html: style }}
          />
        ))}
        {styles && (
          // biome-ignore lint/security/noDangerouslySetInnerHtml: emotion が生成した CSS で、利用者の入力は含まない
          <style data-emotion={dataEmotion} dangerouslySetInnerHTML={{ __html: styles }} />
        )}
      </>
    );
  });

  return <CacheProvider value={registry.cache}>{children}</CacheProvider>;
}
