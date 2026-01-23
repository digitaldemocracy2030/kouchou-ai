import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import type { Meta } from "@/type";
import { Box } from "@chakra-ui/react";
import { getApiBaseUrl } from "../utils/api";
import { Contact } from "./Contact";
import { Faq } from "./Faq";

export default async function Page() {
  try {
    const metaResponse = await fetch(`${getApiBaseUrl()}/meta/metadata.json`, {
      next: { tags: ["meta"] },
    });
    const meta: Meta = await metaResponse.json();

    return (
      <>
        <Header />
        <Box className="container" bg="#EFF6FF" pb="24">
          <Box mx="auto" maxW="1024px">
            <Faq />
            <Contact />
          </Box>
        </Box>
        <Footer meta={meta} />
      </>
    );
  } catch (e) {
    return (
      <p>
        エラー：データの取得に失敗しました
        <br />
        Error: fetch failed to {process.env.NEXT_PUBLIC_API_BASEPATH}.
      </p>
    );
  }
}
