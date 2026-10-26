import type { Config } from "@/type";
import { chatModelDisplayName, embeddingModelDisplayName } from "./modelDisplay";

const config = (overrides: Partial<Config> & { provider?: string }): Config =>
  ({
    model: "gpt-4o-mini",
    is_embedded_at_local: false,
    embedding: { model: "text-embedding-3-small", source_code: "" },
    ...overrides,
  }) as Config;

describe("chatModelDisplayName", () => {
  it("Azure では管理画面の固定値 azure-server ではなく、サーバー設定のモデルであることを示す", () => {
    expect(chatModelDisplayName(config({ provider: "azure", model: "azure-server" }), "azure-server")).toBe(
      "Azure OpenAI のサーバー設定",
    );
  });

  it("古い Azure のレポート（画面で選んだモデル名が残っている）でも、使われなかったモデル名を出さない", () => {
    expect(chatModelDisplayName(config({ provider: "azure", model: "gpt-4o" }), "gpt-4o")).toBe(
      "Azure OpenAI のサーバー設定",
    );
  });

  it.each(["openai", "gemini", "openrouter", "local", undefined])(
    "%s ではステップのモデル名をそのまま出す",
    (provider) => {
      expect(chatModelDisplayName(config({ provider }), "gpt-4o-mini")).toBe("gpt-4o-mini");
    },
  );
});

describe("embeddingModelDisplayName", () => {
  it("サーバ内埋め込みではプロバイダにかかわらずローカルモデル名を出す", () => {
    expect(embeddingModelDisplayName(config({ provider: "azure", is_embedded_at_local: true }))).toBe(
      "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    );
  });

  it("Azure では spec の既定値 text-embedding-3-small ではなく、サーバー設定であることを示す", () => {
    expect(embeddingModelDisplayName(config({ provider: "azure" }))).toBe("Azure OpenAI のサーバー設定");
  });

  it.each(["text-embedding-3-small", "text-embedding-3-large", ""])(
    "Gemini で OpenAI の名前（%s）が入っていれば、実際に使う gemini-embedding-001 を出す",
    (model) => {
      expect(embeddingModelDisplayName(config({ provider: "gemini", embedding: { model, source_code: "" } }))).toBe(
        "gemini-embedding-001",
      );
    },
  );

  it("Gemini で Gemini の埋め込みモデルが入っていればそのまま出す", () => {
    expect(
      embeddingModelDisplayName(
        config({ provider: "gemini", embedding: { model: "gemini-embedding-001", source_code: "" } }),
      ),
    ).toBe("gemini-embedding-001");
  });

  it.each(["openai", undefined])("%s では config の埋め込みモデル名をそのまま出す", (provider) => {
    expect(
      embeddingModelDisplayName(config({ provider, embedding: { model: "text-embedding-3-large", source_code: "" } })),
    ).toBe("text-embedding-3-large");
  });
});

describe("Azure の表示名の差し替え（表示言語）", () => {
  it("呼び出し側が渡した文言を使う", () => {
    expect(chatModelDisplayName(config({ provider: "azure" }), "gpt-4o", "Azure OpenAI server settings")).toBe(
      "Azure OpenAI server settings",
    );
    expect(embeddingModelDisplayName(config({ provider: "azure" }), "Azure OpenAI server settings")).toBe(
      "Azure OpenAI server settings",
    );
    // Azure 以外はモデル名のまま
    expect(chatModelDisplayName(config({ provider: "openai" }), "gpt-4o", "Azure OpenAI server settings")).toBe(
      "gpt-4o",
    );
  });
});
