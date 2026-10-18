import { OpImage, contentType, size } from "./_op-image";

export { size, contentType };

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return OpImage(slug);
}
