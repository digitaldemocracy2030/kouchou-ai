"use client";

import { MenuContent, MenuItem, MenuPositioner, MenuRoot, MenuTrigger, MenuTriggerItem } from "@/components/ui/menu";
import type { Report } from "@/type";
import { IconButton, Portal } from "@chakra-ui/react";
import { Ellipsis, FileSpreadsheet, Pencil, TextIcon, Trash2 } from "lucide-react";
import { type Dispatch, type SetStateAction, useState } from "react";
import { DeleteDialog } from "../DeleteDialog";
import { csvDownload } from "./csvDownload";
import { csvDownloadForWindows } from "./csvDownloadForWindows";

type Props = {
  report: Report;
  setIsEditDialogOpen: Dispatch<SetStateAction<boolean>>;
  setIsClusterEditDialogOpen: Dispatch<SetStateAction<boolean>>;
};

export function ActionMenu({ report, setIsEditDialogOpen, setIsClusterEditDialogOpen }: Props) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <MenuRoot>
        <MenuTrigger asChild>
          <IconButton variant="ghost" size="lg" _hover={{ bg: "blue.50" }} _expanded={{ bg: "blue.50" }}>
            <Ellipsis />
          </IconButton>
        </MenuTrigger>
        <Portal>
          <MenuContent>
            <MenuItem
              value="edit"
              textStyle="body/md/bold"
              onClick={() => {
                setIsEditDialogOpen(true);
              }}
              _icon={{
                w: 5,
                h: 5,
              }}
            >
              <Pencil />
              レポート名編集
            </MenuItem>
            {report.status === "ready" && (
              <MenuItem
                value="edit-cluster"
                textStyle="body/md/bold"
                onClick={() => {
                  setIsClusterEditDialogOpen(true);
                }}
                _icon={{
                  w: 5,
                  h: 5,
                }}
              >
                <TextIcon />
                意見グループ編集
              </MenuItem>
            )}
            {report.status === "ready" && report.isPubcom && (
              <MenuRoot positioning={{ placement: "right-start", gutter: 4 }}>
                <MenuTriggerItem
                  value="csv-download-list"
                  textStyle="body/md/bold"
                  _icon={{
                    w: 5,
                    h: 5,
                  }}
                >
                  <FileSpreadsheet />
                  CSVダウンロード
                </MenuTriggerItem>
                <Portal>
                  <MenuPositioner>
                    <MenuContent>
                      <MenuItem
                        value="csv-download"
                        textStyle="body/md/bold"
                        onClick={async () => {
                          await csvDownload(report.slug);
                        }}
                      >
                        CSVダウンロード
                      </MenuItem>
                      <MenuItem
                        value="csv-download-for-windows"
                        textStyle="body/md/bold"
                        onClick={async () => {
                          await csvDownloadForWindows(report.slug);
                        }}
                      >
                        CSV for Excelダウンロード
                      </MenuItem>
                    </MenuContent>
                  </MenuPositioner>
                </Portal>
              </MenuRoot>
            )}
            <MenuItem
              value="delete"
              color="fg.error"
              textStyle="body/md/bold"
              _icon={{
                w: 5,
                h: 5,
              }}
              onClick={() => setIsOpen(true)}
            >
              <Trash2 />
              削除
            </MenuItem>
          </MenuContent>
        </Portal>
      </MenuRoot>
      <DeleteDialog isOpen={isOpen} setIsOpen={setIsOpen} report={report} />
    </>
  );
}
