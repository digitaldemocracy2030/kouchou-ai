import { Header } from "@/components/Header";
import type { Report } from "@/type";
import { Box, Heading, Text, VStack, Code } from "@chakra-ui/react";
import { PageContent } from "./_components/PageContent";
import { getApiBaseUrl } from "./utils/api";

type ErrorInfo = {
  title: string;
  description: string;
  details?: string;
};

function getErrorInfo(error: unknown, apiUrl: string): ErrorInfo {
  // 接続エラー（サーバーが起動していない、アドレス/ポートが間違っている）
  if (error instanceof TypeError && (error.message.includes("fetch failed") || error.message.includes("ECONNREFUSED"))) {
    return {
      title: "APIサーバーに接続できません",
      description: "APIサーバーが起動していないか、接続先の設定が間違っている可能性があります。",
      details: `接続先: ${apiUrl}/admin/reports`,
    };
  }

  // その他のエラー
  return {
    title: "レポートの取得に失敗しました",
    description: "予期しないエラーが発生しました。",
    details: error instanceof Error ? error.message : String(error),
  };
}

function getHttpErrorInfo(status: number, apiUrl: string): ErrorInfo {
  switch (status) {
    case 401:
      return {
        title: "認証に失敗しました",
        description: "APIキーが無効または設定されていません。環境変数 NEXT_PUBLIC_ADMIN_API_KEY を確認してください。",
      };
    case 403:
      return {
        title: "アクセスが拒否されました",
        description: "このリソースへのアクセス権限がありません。",
      };
    case 404:
      return {
        title: "エンドポイントが見つかりません",
        description: "APIサーバーのバージョンが古いか、エンドポイントのパスが間違っている可能性があります。",
        details: `接続先: ${apiUrl}/admin/reports`,
      };
    case 500:
    case 502:
    case 503:
      return {
        title: "サーバーエラーが発生しました",
        description: "APIサーバーで内部エラーが発生しました。サーバーのログを確認してください。",
      };
    default:
      return {
        title: "レポートの取得に失敗しました",
        description: `HTTPステータス: ${status}`,
      };
  }
}

function ErrorDisplay({ errorInfo }: { errorInfo: ErrorInfo }) {
  return (
    <Box className="container" bgColor="bg.secondary">
      <Header />
      <Box mx="auto" maxW="600px" px="6" py="12">
        <VStack gap={4} align="stretch">
          <Heading textAlign="center" fontSize="xl" color="red.600">
            {errorInfo.title}
          </Heading>
          <Text textAlign="center" color="gray.600">
            {errorInfo.description}
          </Text>
          {errorInfo.details && (
            <Code p={3} borderRadius="md" fontSize="sm" display="block" whiteSpace="pre-wrap">
              {errorInfo.details}
            </Code>
          )}
        </VStack>
      </Box>
    </Box>
  );
}

export default async function Page() {
  const apiUrl = getApiBaseUrl();

  try {
    const response = await fetch(`${apiUrl}/admin/reports`, {
      method: "GET",
      headers: {
        "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
        "Content-Type": "application/json",
      },
      cache: "no-store",
    });

    if (!response.ok) {
      const errorInfo = getHttpErrorInfo(response.status, apiUrl || "");
      return <ErrorDisplay errorInfo={errorInfo} />;
    }

    const reports: Report[] = await response.json();

    return (
      <Box className="container" bgColor="bg.secondary">
        <Header />
        <Box mx="auto" maxW="1024px" boxSizing="content-box" px="6" py="12">
          <PageContent reports={reports} />
        </Box>
      </Box>
    );
  } catch (error) {
    console.error("Error fetching reports:", error);
    const errorInfo = getErrorInfo(error, apiUrl || "");
    return <ErrorDisplay errorInfo={errorInfo} />;
  }
}
