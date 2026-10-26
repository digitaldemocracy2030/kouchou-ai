"use client";

import { IconButton } from "@/components/ui/icon-button";
import { Tooltip } from "@/components/ui/tooltip";
import type { Report } from "@/type";
import { Trash2 } from "lucide-react";
import { useState } from "react";
import { DeleteDialog } from "./DeleteDialog/DeleteDialog";

type Props = {
  report: Report;
};

export function DeleteButton({ report }: Props) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <Tooltip showArrow openDelay={300} closeDelay={100} content="レポートを削除" disabled={isOpen}>
        <IconButton
          variant="ghost"
          size="lg"
          color="font.error"
          aria-label="レポートを削除"
          onClick={() => {
            setIsOpen(true);
          }}
        >
          <Trash2 />
        </IconButton>
      </Tooltip>
      <DeleteDialog isOpen={isOpen} setIsOpen={setIsOpen} report={report} />
    </>
  );
}
