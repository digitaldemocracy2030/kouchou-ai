/**
 * @jest-environment node
 */
import { Box } from "@chakra-ui/react";
import { ServerInsertedHTMLContext } from "next/dist/shared/lib/server-inserted-html.shared-runtime";
import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { Provider } from "./provider";

// Next のサーバー描画と同じく、useServerInsertedHTML に登録された内容を描画の後に集めて head 用の HTML にする
function renderLikeNextServer(ui: ReactNode) {
  const callbacks: Array<() => ReactNode> = [];
  const body = renderToString(
    <ServerInsertedHTMLContext.Provider value={(callback) => callbacks.push(callback)}>
      {ui}
    </ServerInsertedHTMLContext.Provider>,
  );
  const head = callbacks.map((callback) => renderToString(callback())).join("");
  return { body, head };
}

describe("Provider のサーバー描画（#1142）", () => {
  it("emotion のスタイルを body の中に出さず、useServerInsertedHTML で head に出す", () => {
    const { body, head } = renderLikeNextServer(
      <Provider>
        <Box color="red.500">hello</Box>
      </Provider>,
    );

    // body に <style> が混ざると、ブラウザの emotion がそれを head へ移すタイミング次第で hydration が食い違う（#418）
    expect(body).not.toContain("<style");
    expect(body).toMatch(/^<div class="css-[\w-]+">hello<\/div>$/);

    // Chakra のグローバルスタイルと、要素のクラスのスタイルは head 側に出る
    expect(head).toContain('data-emotion="css-global ');
    const className = body.match(/class="css-([\w-]+)"/)?.[1];
    expect(head).toMatch(
      new RegExp(`<style data-emotion="css [^"]*\\b${className}\\b[^"]*">[^<]*\\.css-${className}\\{`),
    );
  });

  it("同じスタイルは 2 回出さない", () => {
    const { head } = renderLikeNextServer(
      <Provider>
        <Box color="red.500">a</Box>
        <Box color="red.500">b</Box>
      </Provider>,
    );
    const className = head.match(/<style data-emotion="css ([\w-]+)/)?.[1];
    expect(className).toBeDefined();
    expect(head.split(`.css-${className}{`).length - 1).toBe(1);
  });
});
