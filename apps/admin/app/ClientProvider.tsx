"use client";

import dynamic from "next/dynamic";

// NOTE
// Next.js v15 と ChakraUI v3 で hydration error を回避するためのコンポーネント
// 将来的に解消される可能性があるため、以下のディスカッションを参照してください
// https://github.com/chakra-ui/chakra-ui/discussions/9051

const Provider = dynamic(() => import("@/components/ui/provider").then((mod) => mod.Provider), {
  ssr: false,
});

export default function ClientProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  return <Provider>{children}</Provider>;
}
