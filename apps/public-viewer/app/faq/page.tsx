import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { ApiConnectionError } from "@/components/ApiConnectionError";
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
    const apiUrl = getApiBaseUrl();
    const errorMessage = e instanceof Error ? e.message : String(e);
    return <ApiConnectionError apiUrl={apiUrl} errorMessage={errorMessage} isServerSide={true} />;
  }
}
