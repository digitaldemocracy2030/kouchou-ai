import { defineRecipe } from "@chakra-ui/react";

// https://github.com/chakra-ui/chakra-ui/blob/d722911fcfcc1e81c918556bd398918863bee785/packages/react/src/theme/recipes/button.ts
export const buttonRecipe = defineRecipe({
  className: "chakra-button",
  base: {
    display: "inline-flex",
    appearance: "none",
    alignItems: "center",
    justifyContent: "center",
    userSelect: "none",
    position: "relative",
    borderRadius: "full",
    whiteSpace: "nowrap",
    verticalAlign: "middle",
    borderWidth: "1px",
    borderColor: "transparent",
    cursor: "button",
    flexShrink: "0",
    outline: "0",
    lineHeight: "2",
    isolation: "isolate",
    fontWeight: "medium",
    transitionProperty: "common",
    transitionDuration: "moderate",
    focusVisibleRing: "outside",
    focusRingColor: "rgba(0, 0, 0, 0.36)",
    _disabled: {
      layerStyle: "disabled",
    },
    _icon: {
      flexShrink: "0",
    },
  },

  variants: {
    size: {
      xs: {
        h: "8",
        minW: "8",
        textStyle: "body/sm/bold",
        px: "5",
        gap: "2",
        _icon: {
          width: "4",
          height: "4",
        },
      },
      md: {
        h: "10",
        minW: "10",
        textStyle: "body/md/bold",
        px: "6",
        gap: "3",
        _icon: {
          width: "5",
          height: "5",
        },
      },
      xl: {
        h: "12",
        minW: "12",
        textStyle: "body/md/bold",
        px: "8",
        gap: "3",
        _icon: {
          width: "5",
          height: "5",
        },
      },
    },

    variant: {
      primary: {
        bg: "button.primary.default",
        color: "white",
        _hover: {
          bg: "button.primary.hover",
          shadow: "lg",
          _active: {
            bg: "button.primary.active",
          },
        },
        _expanded: {
          bg: "button.primary.active",
          shadow: "lg",
        },
      },
      secondary: {
        bg: "white",
        color: "font.primary",
        borderColor: "gray.800",
        _hover: {
          bg: "button.hover",
          shadow: "lg",
          _active: {
            bg: "button.active",
          },
        },
        _expanded: {
          bg: "button.active",
          shadow: "lg",
        },
      },
      tertiary: {
        bg: "white",
        color: "font.primary",
        borderColor: "gray.300",
        _hover: {
          bg: "button.hover",
          shadow: "lg",
          _active: {
            bg: "button.active",
          },
        },
        _expanded: {
          bg: "button.active",
          shadow: "lg",
        },
      },
      ghost: {
        bg: "transparent",
        color: "font.primary",
        _hover: {
          bg: "button.hover",
          shadow: "lg",
          _active: {
            bg: "button.active",
          },
        },
        _expanded: {
          bg: "button.active",
          shadow: "lg",
        },
      },
    },
  },

  defaultVariants: {
    size: "xs",
    variant: "primary",
  },
});
