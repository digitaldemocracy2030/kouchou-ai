import { Box, Code, Heading, Text, VStack } from "@chakra-ui/react";

type ApiConnectionErrorProps = {
  apiUrl: string;
  errorMessage?: string;
  isServerSide?: boolean;
};

export function ApiConnectionError({ apiUrl, errorMessage, isServerSide = true }: ApiConnectionErrorProps) {
  return (
    <Box className="container" py={12}>
      <VStack maxW="800px" mx="auto" gap={6} align="stretch">
        <Heading as="h1" size="lg" color="red.600">
          API接続エラー
        </Heading>

        <Box bg="red.50" p={6} borderRadius="md" borderLeft="4px solid" borderLeftColor="red.500">
          <Text fontWeight="bold" mb={2}>
            データの取得に失敗しました
          </Text>
          <Text>APIサーバーに接続できませんでした。サーバーの設定を確認してください。</Text>
        </Box>

        <Box bg="gray.50" p={6} borderRadius="md">
          <Text fontWeight="bold" mb={3}>
            接続先情報
          </Text>
          <VStack align="stretch" gap={2}>
            <Box>
              <Text fontSize="sm" color="gray.600">
                API URL:
              </Text>
              <Code p={2} display="block" bg="gray.100" borderRadius="sm">
                {apiUrl || "(未設定)"}
              </Code>
            </Box>
            <Box>
              <Text fontSize="sm" color="gray.600">
                リクエスト元:
              </Text>
              <Code p={2} display="block" bg="gray.100" borderRadius="sm">
                {isServerSide ? "サーバーサイド (SSR)" : "クライアントサイド (ブラウザ)"}
              </Code>
            </Box>
            {errorMessage && (
              <Box>
                <Text fontSize="sm" color="gray.600">
                  エラー詳細:
                </Text>
                <Code p={2} display="block" bg="gray.100" borderRadius="sm" whiteSpace="pre-wrap">
                  {errorMessage}
                </Code>
              </Box>
            )}
          </VStack>
        </Box>

        <Box bg="blue.50" p={6} borderRadius="md" borderLeft="4px solid" borderLeftColor="blue.500">
          <Text fontWeight="bold" mb={3}>
            考えられる原因と対処法
          </Text>
          <VStack align="stretch" gap={4}>
            <Box>
              <Text fontWeight="semibold" mb={1}>
                1. 環境変数の設定が正しくない
              </Text>
              <Text fontSize="sm" color="gray.700" mb={2}>
                Container Apps環境では、<Code>api:8000</Code>のような内部Docker
                ネットワーク名は使用できません。APIの外部公開URL（FQDN）を設定してください。
              </Text>
              <Box bg="white" p={3} borderRadius="sm" fontSize="sm">
                <Text fontWeight="medium" mb={1}>
                  設定例:
                </Text>
                <Code display="block" p={2} bg="gray.100">
                  NEXT_PUBLIC_API_BASEPATH=https://your-api.example.com
                </Code>
                <Code display="block" p={2} bg="gray.100" mt={1}>
                  API_BASEPATH=https://your-api.example.com
                </Code>
              </Box>
            </Box>

            <Box>
              <Text fontWeight="semibold" mb={1}>
                2. APIサーバーが起動していない
              </Text>
              <Text fontSize="sm" color="gray.700">
                APIサーバーが正常に起動しているか確認してください。
              </Text>
            </Box>

            <Box>
              <Text fontWeight="semibold" mb={1}>
                3. ネットワーク接続の問題
              </Text>
              <Text fontSize="sm" color="gray.700">
                ファイアウォールやネットワーク設定により、APIサーバーへのアクセスがブロックされている可能性があります。
              </Text>
            </Box>
          </VStack>
        </Box>

        <Box bg="yellow.50" p={4} borderRadius="md" fontSize="sm">
          <Text fontWeight="bold" mb={1}>
            管理者向け情報
          </Text>
          {isServerSide ? (
            <Text color="gray.700">
              このエラーはサーバー側でAPIへの接続に失敗した場合に表示されます。環境変数
              <Code>API_BASEPATH</Code>が正しいか確認してください。
            </Text>
          ) : (
            <Text color="gray.700">
              このエラーはブラウザからAPIへの接続に失敗した場合に表示されます。環境変数
              <Code>NEXT_PUBLIC_API_BASEPATH</Code>が正しいか確認してください。
            </Text>
          )}
        </Box>
      </VStack>
    </Box>
  );
}
