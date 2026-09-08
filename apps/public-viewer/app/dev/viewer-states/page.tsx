import { ViewerStates } from "@/components/dev/ViewerStates";
import { notFound } from "next/navigation";

export default function Page() {
  if (process.env.NODE_ENV !== "development") notFound();
  return <ViewerStates />;
}
