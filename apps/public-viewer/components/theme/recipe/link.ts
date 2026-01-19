import { defineRecipe } from "@chakra-ui/react";

// https://github.com/chakra-ui/chakra-ui/blob/3df43bab4e98af6cabc4f7e199e38c4b8ec11bbe/packages/react/src/theme/recipes/link.ts
export const linkRecipe = defineRecipe({
  className: "chakra-link",
  base: {
    display: "inline-flex",
    alignItems: "center",
    outline: "none",
    gap: "1.5",
    cursor: "pointer",
    borderRadius: "l1",
    focusRing: "outside",
  },

  variants: {
    variant: {
      underline: {
        color: "font.link",
        textDecoration: "underline",
        textUnderlineOffset: "3px",
        textDecorationColor: "currentColor/20",
        _hover: {
          opacity: 0.75,
          textDecoration: "none",
        },
      },
    },
  },

  defaultVariants: {
    variant: "underline",
  },
});
