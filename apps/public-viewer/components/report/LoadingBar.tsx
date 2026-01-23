import { HStack, Progress } from "@chakra-ui/react";
import React from "react";

type Props = {
  loaded: number;
  max: number;
  isVisualizing?: boolean;
};

export function LoadingBar({ loaded, max, isVisualizing }: Props) {
  if (isVisualizing) {
    return (
      <Progress.Root value={null} size={"xl"} mx={"auto"} p={5} maxW={"800px"} colorPalette={"cyan"}>
        <HStack gap="5">
          <Progress.Track flex="1">
            <Progress.Range />
          </Progress.Track>
          <Progress.Label>Visualizing...</Progress.Label>
        </HStack>
      </Progress.Root>
    );
  }
  return (
    <Progress.Root value={loaded} max={max} size={"xl"} mx={"auto"} p={5} maxW={"800px"} colorPalette={"cyan"}>
      <HStack gap="5">
        <Progress.Track flex="1">
          <Progress.Range />
        </Progress.Track>
        <Progress.ValueText>
          {Math.floor(loaded / 1024).toLocaleString()} KB / {Math.floor(max / 1024).toLocaleString()} KB
        </Progress.ValueText>
      </HStack>
    </Progress.Root>
  );
}
