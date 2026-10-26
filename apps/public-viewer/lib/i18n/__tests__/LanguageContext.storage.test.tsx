import "@testing-library/jest-dom";
import { LanguageProvider, useLanguage } from "@/lib/i18n/LanguageContext";
import { act, render, screen } from "@testing-library/react";

function Consumer() {
  const { language, setLanguage } = useLanguage();
  return (
    <>
      <p data-testid="lang">{language}</p>
      <button type="button" onClick={() => setLanguage("en")}>
        en
      </button>
    </>
  );
}

afterEach(() => {
  jest.restoreAllMocks();
});

it("localStorage を読んだだけで例外になる環境でも、描画と言語の切り替えができる", () => {
  jest.spyOn(window, "localStorage", "get").mockImplementation(() => {
    throw new DOMException("The operation is insecure.", "SecurityError");
  });
  render(
    <LanguageProvider>
      <Consumer />
    </LanguageProvider>,
  );
  expect(screen.getByTestId("lang")).toHaveTextContent("ja");
  act(() => {
    screen.getByRole("button", { name: "en" }).click();
  });
  expect(screen.getByTestId("lang")).toHaveTextContent("en");
});
