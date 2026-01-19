"use client";

import {
  IconButton as ChakraIconButton,
  type IconButtonProps as ChakraIconButtonProps,
  type RecipeVariantProps,
  useRecipe,
} from "@chakra-ui/react";
import { forwardRef } from "react";
import { iconButtonRecipe } from "../theme/recipe/icon-button";

type IconButtonVariantProps = RecipeVariantProps<typeof iconButtonRecipe>;
type IconButtonProps = IconButtonVariantProps & Omit<ChakraIconButtonProps, keyof IconButtonVariantProps>;

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(({ size, variant, ...rest }, ref) => {
  const recipe = useRecipe({ recipe: iconButtonRecipe });
  const styles = recipe({ size, variant });

  return <ChakraIconButton ref={ref} css={styles} {...rest} />;
});
