"use client";

import {
  Button as ChakraButton,
  type ButtonProps as ChakraButtonProps,
  type RecipeVariantProps,
  useRecipe,
} from "@chakra-ui/react";
import { forwardRef } from "react";
import { buttonRecipe } from "../theme/recipe/button";

type ButtonVariantProps = RecipeVariantProps<typeof buttonRecipe>;
type ButtonProps = ButtonVariantProps & Omit<ChakraButtonProps, keyof ButtonVariantProps>;

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(({ size, variant, ...rest }, ref) => {
  const recipe = useRecipe({ recipe: buttonRecipe });
  const styles = recipe({ size, variant });

  return <ChakraButton ref={ref} css={styles} {...rest} />;
});
