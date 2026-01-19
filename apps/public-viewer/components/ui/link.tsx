import {
  Link as ChakraLink,
  type LinkProps as ChakraLinkProps,
  type RecipeVariantProps,
  useRecipe,
} from "@chakra-ui/react";
import { forwardRef } from "react";
import { linkRecipe } from "../theme/recipe/link";

type LinkVariantProps = RecipeVariantProps<typeof linkRecipe>;
type LinkProps = LinkVariantProps & Omit<ChakraLinkProps, keyof LinkVariantProps>;

export const Link = forwardRef<HTMLAnchorElement, LinkProps>(({ variant, ...rest }, ref) => {
  const recipe = useRecipe({ recipe: linkRecipe });
  const styles = recipe({ variant });

  return <ChakraLink ref={ref} css={styles} {...rest} />;
});
