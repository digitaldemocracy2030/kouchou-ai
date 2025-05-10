"use client";

import React, { useState } from "react";
import { Button, Icon, Tooltip } from "@chakra-ui/react";
import { CloudIcon } from "lucide-react";
import { toaster } from "@/components/ui/toaster";
import { MenuRoot, MenuTrigger, MenuContent, MenuItem } from "@/components/ui/menu";

export function DeployButton({ slug, report }: { slug: string; report?: { status: string } }) {
  const [isLoading, setIsLoading] = useState(false);
  const [deployUrl, setDeployUrl] = useState<string | null>(null);
  const [config, setConfig] = useState<{
    netlifyEnabled: boolean;
    vercelEnabled: boolean;
    externalHostingEnabled: boolean;
  }>({
    netlifyEnabled: false,
    vercelEnabled: false,
    externalHostingEnabled: false
  });

  React.useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await fetch('/api/deploy/config');
        if (res.ok) {
          const data = await res.json();
          setConfig(data);
        }
      } catch (error) {
        console.error('Failed to fetch deploy config:', error);
      }
    };
    
    fetchConfig();
  }, []);
  
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
  
  if (!config.externalHostingEnabled || !report || report.status !== "ready") {
    return null;
  }

  return (
    <>
      <MenuRoot>
        <MenuTrigger asChild>
          <Button
            variant="ghost"
            isLoading={isLoading}
            onClick={(e: React.MouseEvent) => e.stopPropagation()}
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
          </Button>
        </MenuTrigger>
        <MenuContent>
          {config.netlifyEnabled && (
            <MenuItem onClick={() => handleDeploy("netlify")}>
              Netlifyに公開
            </MenuItem>
          )}
          {config.vercelEnabled && (
            <MenuItem onClick={() => handleDeploy("vercel")}>
              Vercelに公開
            </MenuItem>
          )}
        </MenuContent>
      </MenuRoot>
      
      {deployUrl && (
        <Button
          variant="link"
          colorScheme="blue"
          onClick={(e: React.MouseEvent) => {
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
