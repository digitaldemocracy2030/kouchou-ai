"use client";

import { Box, Button } from "@chakra-ui/react";
import { ApiConnectionError } from "@/components/ApiConnectionError";
import { Box, Button } from "@chakra-ui/react";
import { useEffect } from "react";

type Props = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function ErrorPage({ error, reset }: Props) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  const apiUrl = process.env.NEXT_PUBLIC_API_BASEPATH || "";

  return (
    <>
      <ApiConnectionError apiUrl={apiUrl} errorMessage={error.message} isServerSide={false} />
      <Box textAlign="center" mb={8}>
        <Button onClick={reset}>リトライする</Button>
      </Box>
    </>
  );
}
