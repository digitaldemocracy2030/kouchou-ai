import { generateStaticParams } from "@/app/[slug]/page";
import { OpImage } from "../_op-image";

export { generateStaticParams };

type PageProps = {
  params: Promise<{
    slug: string;
  }>;
};

// static build時のOGP画像生成用のroute
// ref: https://github.com/vercel/next.js/issues/51147#issuecomment-1842197049
export async function GET(_: Request, { params }: PageProps) {
  const slug = (await params).slug;
  try {
    return OpImage(slug);
  } catch (error) {
    return new Response("OG Image not available during static export", {
      status: 200,
      headers: {
        'Content-Type': 'text/plain',
      },
    });
  }
}
