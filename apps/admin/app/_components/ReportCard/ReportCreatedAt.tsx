import { Text } from "@chakra-ui/react";

export function ReportCreatedAt({ createdAt }: { createdAt?: string }) {
  return (
    <Text textStyle="body/sm">
      {createdAt
        ? new Date(createdAt).toLocaleString("ja-JP", {
            timeZone: "Asia/Tokyo",
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
          })
        : "日時データなし"}
    </Text>
  );
}
