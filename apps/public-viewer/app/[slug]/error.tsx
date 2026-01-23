"use client";

import { Button } from "@chakra-ui/react";
import { useEffect } from "react";

type Props = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function ErrorPage({ error, reset }: Props) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <>
      <p>
        エラー：データの取得に失敗しました
        <br />
        Error: fetch failed to {process.env.NEXT_PUBLIC_API_BASEPATH}.
      </p>
      <Button onClick={reset}>リトライする</Button>
    </>
  );
}
