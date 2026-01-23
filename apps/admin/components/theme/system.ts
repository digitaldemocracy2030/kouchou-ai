import { createSystem, defaultConfig } from "@chakra-ui/react";
import { fonts } from "./fonts";
import { semanticTokens } from "./semanticTokens";
import { textStyles } from "./textStyle";

export const system = createSystem(defaultConfig, {
  theme: {
    tokens: {
      fonts,
    },
    semanticTokens,
    textStyles,
  },
});
