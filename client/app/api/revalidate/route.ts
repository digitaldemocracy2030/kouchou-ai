import { revalidatePath } from 'next/cache';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { path, secret } = await request.json();
    
    // Ondemand ISR用の秘密キーの検証
    const validSecret = process.env.REVALIDATE_SECRET;
    
    if (secret !== validSecret) {
      console.error('Invalid revalidation secret');
      return NextResponse.json({ message: 'Invalid secret' }, { status: 401 });
    }
    
    if (!path) {
      return NextResponse.json({ message: 'Path is required' }, { status: 400 });
    }

    // 指定されたパスのキャッシュを破棄
    revalidatePath(path);
    console.log(`Revalidated path: ${path}`);
    
    return NextResponse.json({ 
      revalidated: true, 
      now: Date.now(),
      path
    });
  } catch (error) {
    console.error('Revalidation error:', error);
    return NextResponse.json(
      { message: 'Error revalidating', error: String(error) }, 
      { status: 500 }
    );
  }
}