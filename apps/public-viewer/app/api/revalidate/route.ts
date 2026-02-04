import { revalidateTag } from "next/cache";
import { type NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const { tag, secret } = await request.json();

    // Ondemand ISR用の秘密キーの検証
    const validSecret = process.env.REVALIDATE_SECRET;

    if (secret !== validSecret) {
      console.error("Invalid revalidation secret");
      return NextResponse.json({ message: "Invalid secret" }, { status: 401 });
    }

    if (!tag) {
      return NextResponse.json({ message: "Tag is required" }, { status: 400 });
    }

    // 指定されたタグのキャッシュを破棄
    revalidateTag(tag);
    console.log(`Revalidated tag: ${tag}`);

    return NextResponse.json({
      revalidated: true,
      now: Date.now(),
      tag,
      method: "force",
    });
  } catch (error) {
    console.error("Revalidation error:", error);
    return NextResponse.json({ message: "Error revalidating", error: String(error) }, { status: 500 });
  }
}
