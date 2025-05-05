import type { Meta } from "@/type";
import { Alert, HStack, Image } from "@chakra-ui/react";
import { useEffect, useState } from "react";

export function Header() {
  const [meta, setMeta] = useState<Meta | null>(null);
  // reporter.png（作成者画像）が存在するかどうかを管理
  // 204(No Content)の場合は画像を表示しない
  const [hasImage, setHasImage] = useState(false);

  // メタ情報の取得
  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_BASEPATH}/meta`)
      .then(response => response.json())
      .then(data => setMeta(data))
      .catch(() => setMeta(null));
  }, []);

  // reporter.pngの存在確認
  // 画像が存在する場合のみ画像を表示する（リンク切れやキャッシュ問題を防ぐため）
  useEffect(() => {
    if (!meta) {
      setHasImage(false);
      return;
    }
    fetch(`${process.env.NEXT_PUBLIC_API_BASEPATH}/meta/reporter.png`)
      .then(res => setHasImage(res.status === 200))
      .catch(() => setHasImage(false));
  }, [meta]);

  return (
    <HStack
      justify="space-between"
      alignItems={"center"}
      mb={8}
      mx={"auto"}
      maxW={"1200px"}
    >
      <HStack>
        {/* 画像が本当に存在する場合のみ表示する（204や404の場合は非表示） */}
        {meta && hasImage && (
          <Image
            src={`${process.env.NEXT_PUBLIC_API_BASEPATH}/meta/reporter.png`}
            mx={"auto"}
            objectFit={"cover"}
            maxH={{ base: "40px", md: "60px" }}
            maxW={{ base: "120px", md: "200px" }}
            alt={meta.reporter}
          />
        )}
      </HStack>
      <HStack>
        <Alert.Root status="warning">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Title fontSize={"md"}>管理者画面</Alert.Title>
            <Alert.Description>
              このページはレポート作成者向けの管理画面です
            </Alert.Description>
          </Alert.Content>
        </Alert.Root>
      </HStack>
    </HStack>
  );
}
