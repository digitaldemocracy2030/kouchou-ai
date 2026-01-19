import { Tooltip } from "@/components/ui/tooltip";
import type { Report } from "@/type";
import { Link, Text } from "@chakra-ui/react";
import { useEffect, useRef, useState } from "react";

type Props = {
  report: Report;
};

export function ReportTitle({ report }: Props) {
  const ref = useRef<HTMLParagraphElement>(null);
  const [isOverflown, setIsOverflown] = useState(false);

  // biome-ignore lint/correctness/useExhaustiveDependencies: レポートタイトル編集後に文字数の長さを再判定する
  useEffect(() => {
    const element = ref.current;
    setIsOverflown(element ? element.scrollWidth > element.clientWidth : false);
  }, [report.title]);

  return (
    <Tooltip showArrow content={<Text textStyle="body/sm/bold">{report.title}</Text>} disabled={!isOverflown}>
      {report.status === "ready" ? (
        <Link
          w="full"
          href={`${process.env.NEXT_PUBLIC_CLIENT_BASEPATH}/${report.slug}`}
          target="_blank"
          rel="noopener noreferrer"
          _hover={{ color: "font.link" }}
        >
          <Text ref={ref} textStyle="body/md/bold" truncate>
            {report.title}
          </Text>
        </Link>
      ) : (
        <Text ref={ref} textStyle="body/md/bold" truncate>
          {report.title}
        </Text>
      )}
    </Tooltip>
  );
}
