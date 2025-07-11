import { MenuContent, MenuItem, MenuRoot, MenuTrigger } from "@/components/ui/menu";
import { toaster } from "@/components/ui/toaster";
import type { Report, ReportVisibility } from "@/type";
import { IconButton, Portal } from "@chakra-ui/react";
import { Eye, EyeClosedIcon, LockKeyhole } from "lucide-react";
import type { Dispatch, SetStateAction } from "react";
import { updateReportVisibility } from "./actions";

type Props = {
  report: Report;
  setReports: Dispatch<SetStateAction<Report[]>>;
};

const iconStyles = {
  public: {
    bg: "bg.public",
    color: "font.public",
    borderColor: "border.public",
    text: "公開",
    icon: <Eye />,
  },
  unlisted: {
    bg: "bg.limitedPublic",
    color: "font.limitedPublic",
    borderColor: "border.limitedPublic",
    text: "限定公開",
    icon: <LockKeyhole />,
  },
  private: {
    bg: "bg.private",
    color: "font.private",
    borderColor: "border.private",
    text: "非公開",
    icon: <EyeClosedIcon />,
  },
};

export function Visibility({ report, setReports }: Props) {
  return (
    <MenuRoot
      onSelect={async (e) => {
        if (e.value === report.visibility) return;

        const result = await updateReportVisibility(report.slug, e.value as ReportVisibility);

        if (result.success) {
          setReports((prevReports) =>
            prevReports.map((r) =>
              r.slug === report.slug ? { ...r, visibility: result.visibility } : r,
            ),
          );
        } else {
          toaster.create({
            type: "error",
            title: "更新エラー",
            description: result.error,
          });
        }
      }}
    >
      <MenuTrigger asChild>
        <IconButton
          size="lg"
          border="1px solid"
          {...iconStyles[report.visibility]}
          _icon={{
            w: 5,
            h: 5,
          }}
          _hover={{
            shadow: "inset 0 0 0 44px rgba(0, 0, 0, 0.06)",
          }}
        >
          {iconStyles[report.visibility].icon}
        </IconButton>
      </MenuTrigger>
      <Portal>
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
      </Portal>
    </MenuRoot>
  );
}
