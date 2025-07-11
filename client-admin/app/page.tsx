import { Header } from "@/components/Header";
import type { Report } from "@/type";
import { Box, Heading } from "@chakra-ui/react";
import { PageContent } from "./_components/PageContent";
import { getApiBaseUrl } from "./utils/api";

export default async function Page() {
  try {
    const response = await fetch(`${getApiBaseUrl()}/admin/reports`, {
      method: "GET",
      headers: {
        "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
        "Content-Type": "application/json",
      },
      cache: "no-store",
    });

    if (!response.ok) {
      return (
        <div className="container">
          <Header />
          <Box mx="auto" maxW="1000px" px="6" py="12">
            <Heading textAlign="center" fontSize="xl" mb={8}>
              レポートの取得に失敗しました
            </Heading>
          </Box>
        </div>
      );
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
    return (
      <Box mx="auto" maxW="1000px" px="6" py="12">
        <Heading textAlign="center" fontSize="xl" mb={8}>
          レポートの取得に失敗しました
        </Heading>
      </Box>
    );
  }
}
