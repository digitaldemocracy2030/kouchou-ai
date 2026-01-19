import { Alert, Box, Flex, Image } from "@chakra-ui/react";

export function Header() {
  return (
    <Box py="5" px="6" bg="white">
      <Flex maxW="1200px" mx="auto" justifyContent="space-between" alignItems="center">
        <Image src="/images/logo.svg" alt="広聴AI" />
        <Box>
          <Alert.Root status="warning">
            <Alert.Indicator />
            <Alert.Content>
              <Alert.Title fontSize={"md"}>管理者画面</Alert.Title>
              <Alert.Description>このページはレポート作成者向けの管理画面です</Alert.Description>
            </Alert.Content>
          </Alert.Root>
        </Box>
      </Flex>
    </Box>
  );
}
