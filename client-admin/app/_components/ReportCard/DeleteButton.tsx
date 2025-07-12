"use client";

import { IconButton } from "@/components/ui/icon-button";
import type { Report } from "@/type";
import { Trash2 } from "lucide-react";
import { useState } from "react";
import { DeleteDialog } from "./DeleteDialog";

type Props = {
  report: Report;
};

export function DeleteButton({ report }: Props) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <IconButton
        variant="ghost"
        size="lg"
        color="font.error"
        onClick={() => {
          setIsOpen(true);
        }}
      >
        <Trash2 />
      </IconButton>
      <DeleteDialog isOpen={isOpen} setIsOpen={setIsOpen} report={report} />
    </>
  );
}
