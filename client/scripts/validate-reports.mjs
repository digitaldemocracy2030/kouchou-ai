import { exit } from "node:process";

/**
 * 静的ビルド前に公開状態のレポートが存在するかを確認するスクリプト
 * 公開レポートがない場合は、わかりやすい日本語のエラーメッセージを表示して終了する
 */

async function validateReports() {
  // 静的ビルド時のみ実行
  if (process.env.NEXT_PUBLIC_OUTPUT_MODE !== "export") {
    console.log("通常ビルドモードのため、レポート検証をスキップします");
    return;
  }

  console.log("📋 公開レポートの存在確認を開始します...");

  try {
    // API_BASEPATHの取得（デフォルトはhttp://localhost:8000）
    const apiBasePath = process.env.API_BASEPATH || "http://localhost:8000";
    const apiKey = process.env.NEXT_PUBLIC_PUBLIC_API_KEY || "";

    console.log(`API接続先: ${apiBasePath}/reports`);

    const response = await fetch(`${apiBasePath}/reports`, {
      headers: {
        "x-api-key": apiKey,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      console.error(`❌ APIへの接続に失敗しました (ステータス: ${response.status})`);
      console.error("APIサーバーが起動しているか確認してください");
      exit(1);
    }

    const reports = await response.json();

    // status が "ready" のレポートをフィルタリング
    const readyReports = reports.filter((report) => report.status === "ready");

    if (readyReports.length === 0) {
      console.error(`\n${"=".repeat(80)}`);
      console.error("❌ エラー: 公開状態のレポートが見つかりません");
      console.error("=".repeat(80));
      console.error("");
      console.error("静的HTML出力を行うには、少なくとも1つのレポートを公開状態にする必要があります。");
      console.error("");
      console.error("対処方法:");
      console.error("  1. 管理画面 (http://localhost:4000) にアクセスしてください");
      console.error("  2. レポートを作成するか、既存のレポートを公開状態に変更してください");
      console.error("  3. レポートのステータスが「ready」になっていることを確認してください");
      console.error("");
      console.error(`現在のレポート数: ${reports.length}`);
      console.error(`公開状態のレポート数: ${readyReports.length}`);
      console.error(`${"=".repeat(80)}\n`);
      exit(1);
    }

    console.log(`✅ 公開レポートが ${readyReports.length} 件見つかりました`);
    console.log("静的ビルドを続行します...\n");
  } catch (error) {
    console.error(`\n${"=".repeat(80)}`);
    console.error("❌ エラー: レポートの取得中に問題が発生しました");
    console.error("=".repeat(80));
    console.error("");
    console.error("エラー詳細:", error.message);
    console.error("");
    console.error("考えられる原因:");
    console.error("  - APIサーバーが起動していない");
    console.error("  - ネットワーク接続の問題");
    console.error("  - API_BASEPATHの設定が正しくない");
    console.error("");
    console.error("対処方法:");
    console.error("  1. docker compose up -d --wait api を実行してAPIサーバーを起動してください");
    console.error("  2. .env ファイルの API_BASEPATH 設定を確認してください");
    console.error(`${"=".repeat(80)}\n`);
    exit(1);
  }
}

await validateReports();
