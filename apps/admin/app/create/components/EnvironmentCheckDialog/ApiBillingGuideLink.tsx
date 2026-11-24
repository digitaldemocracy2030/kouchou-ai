import { Link } from "@chakra-ui/react";

export function ApiBillingGuideLink({ errorType }: { errorType?: string }) {
  if (errorType !== "insufficient_quota" && errorType !== "rate_limit_error") return null;

  return (
    <Link
      display="block"
      mt="1"
      textDecoration="underline"
      href="https://digitaldemocracy2030.github.io/kouchou-ai/self-hosting/api-billing-and-rate-limits"
      target="_blank"
      rel="noopener noreferrer"
    >
      APIの課金と429エラーの対処方法（別タブ）
    </Link>
  );
}
