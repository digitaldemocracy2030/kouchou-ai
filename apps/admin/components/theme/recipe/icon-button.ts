import { defineRecipe } from "@chakra-ui/react";

// buttonのレシピを元に作成
export const iconButtonRecipe = defineRecipe({
  className: "chakra-button",
  base: {
    display: "inline-flex",
    appearance: "none",
    alignItems: "center",
    justifyContent: "center",
    userSelect: "none",
    position: "relative",
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
        _icon: {
          width: "4",
          height: "4",
        },
      },
      md: {
        h: "10",
        minW: "10",
        _icon: {
          width: "5",
          height: "5",
        },
      },
      lg: {
        h: "11",
        minW: "11",
        _icon: {
          width: "5",
          height: "5",
        },
      },
    },

    variant: {
      solid: {
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
      outline: {
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
      surface: {
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
    variant: "solid",
  },
});
