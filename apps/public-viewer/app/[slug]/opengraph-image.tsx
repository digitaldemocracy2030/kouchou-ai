import { OpImage, contentType, size } from "./_op-image";

export { size, contentType };

export default async function Image({ params }: { params: { slug: string } }) {
  return OpImage(params.slug);
}
