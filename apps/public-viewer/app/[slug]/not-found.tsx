import { Button } from "@chakra-ui/react";
import Link from "next/link";

export default function NotFound() {
  return (
    <>
      <p>ページが見つかりませんでした</p>
      <Link href="/">
        <Button>トップに戻る</Button>
      </Link>
    </>
  );
}
