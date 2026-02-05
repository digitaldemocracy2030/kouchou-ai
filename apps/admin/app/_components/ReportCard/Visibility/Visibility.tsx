"use client";

import { MenuContent, MenuItem, MenuRoot, MenuTrigger } from "@/components/ui/menu";
import { toaster } from "@/components/ui/toaster";
import { Tooltip } from "@/components/ui/tooltip";
import type { Report, ReportVisibility } from "@/type";
import { Box, IconButton } from "@chakra-ui/react";
import { Eye, EyeClosedIcon, LockKeyhole } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { updateReportVisibility } from "./actions";

type Props = {
  report: Report;
};

const iconStyles = {
  public: {
    bg: "bg.public",
    color: "font.public",
    borderColor: "border.public",
    text: "公開",
    ariaLabel: "公開設定を変更",
    icon: <Eye />,
  },
  unlisted: {
    bg: "bg.limitedPublic",
    color: "font.limitedPublic",
    borderColor: "border.limitedPublic",
    text: "限定公開",
    ariaLabel: "公開設定を変更",
    icon: <LockKeyhole />,
  },
  private: {
    bg: "bg.private",
    color: "font.private",
    borderColor: "border.private",
    text: "非公開",
    ariaLabel: "公開設定を変更",
    icon: <EyeClosedIcon />,
  },
};

export function Visibility({ report }: Props) {
  const router = useRouter();
  const visibility = report.visibility || "private"; // fallback to 'private'
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <MenuRoot
      onOpenChange={(details) => setIsMenuOpen(details.open)}
      onSelect={async (e) => {
        if (e.value === report.visibility) return;

        const result = await updateReportVisibility(report.slug, e.value as ReportVisibility);

        if (result.success) {
          router.refresh();
        } else {
          toaster.create({
            type: "error",
            title: "更新エラー",
            description: result.error,
          });
        }
      }}
    >
      <Tooltip showArrow openDelay={300} closeDelay={100} content={iconStyles[visibility].text} disabled={isMenuOpen}>
        <Box display="inline-flex">
          <MenuTrigger asChild>
            <IconButton
              size="lg"
              border="1px solid"
              aria-label={iconStyles[visibility].ariaLabel}
              {...iconStyles[visibility]}
              _icon={{
                w: 5,
                h: 5,
              }}
              _hover={{
                shadow: "inset 0 0 0 44px rgba(0, 0, 0, 0.06)",
              }}
            >
              {iconStyles[visibility].icon}
            </IconButton>
          </MenuTrigger>
        </Box>
      </Tooltip>
      <MenuContent>
        {Object.entries(iconStyles).map(([key, style]) => (
          <MenuItem
            key={key}
            value={key}
            color={style.color}
            textStyle="body/md/bold"
            border="1px solid"
            borderColor="transparent"
            _icon={{
              w: 5,
              h: 5,
            }}
            _hover={{
              borderColor: style.borderColor,
              bg: style.bg,
            }}
          >
            {style.icon}
            {style.text}
          </MenuItem>
        ))}
      </MenuContent>
    </MenuRoot>
  );
}
