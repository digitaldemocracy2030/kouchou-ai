"use client";

import { useState } from "react";
import { Button, Icon, Menu, MenuButton, MenuItem, MenuList, Tooltip } from "@chakra-ui/react";
import { CloudIcon } from "lucide-react";
import { toaster } from "@/components/ui/toaster";

export function DeployButton({ slug }: { slug: string }) {
  const [isLoading, setIsLoading] = useState(false);
  const [deployUrl, setDeployUrl] = useState<string | null>(null);
  
  const handleDeploy = async (service: "netlify" | "vercel") => {
    setIsLoading(true);
    try {
      const res = await fetch(`/api/deploy/${service}/${slug}`, {
        method: "POST",
      });
      
      if (!res.ok) {
        throw new Error(`デプロイに失敗しました: ${res.statusText}`);
      }
      
      const data = await res.json();
      setDeployUrl(data.url);
      
      toaster.create({
        type: "success",
        duration: 5000,
        title: "デプロイ成功",
        description: `${service === "netlify" ? "Netlify" : "Vercel"}にデプロイしました。`,
      });
    } catch (error) {
      toaster.create({
        type: "error",
        duration: 5000,
        title: "デプロイ失敗",
        description: error instanceof Error ? error.message : String(error),
      });
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <>
      <Menu>
        <MenuButton
          as={Button}
          variant="ghost"
          isLoading={isLoading}
          onClick={(e) => e.stopPropagation()}
        >
          <Tooltip
            content="外部サービスに公開"
            openDelay={0}
            closeDelay={0}
          >
            <Icon>
              <CloudIcon />
            </Icon>
          </Tooltip>
        </MenuButton>
        <MenuList>
          <MenuItem onClick={() => handleDeploy("netlify")}>
            Netlifyに公開
          </MenuItem>
          <MenuItem onClick={() => handleDeploy("vercel")}>
            Vercelに公開
          </MenuItem>
        </MenuList>
      </Menu>
      
      {deployUrl && (
        <Button
          variant="link"
          colorScheme="blue"
          onClick={(e) => {
            e.stopPropagation();
            window.open(deployUrl, "_blank");
          }}
        >
          公開サイトを開く
        </Button>
      )}
    </>
  );
}
