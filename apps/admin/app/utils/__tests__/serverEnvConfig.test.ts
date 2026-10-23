/**
 * @jest-environment node
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { GET } from "@/app/api/admin/reports/[slug]/config/route";

// admin のサーバー側（Route Handler / Server Action）が実行時に読む環境変数。
// NEXT_PUBLIC_* と違ってビルド時に埋め込まれないので、デプロイ経路ごとに
// admin コンテナの実行時の環境変数として渡す必要がある。
const SERVER_ONLY_ENV = "ADMIN_API_KEY";

const repoRoot = path.resolve(__dirname, "../../../../..");
const read = (relativePath: string) => readFileSync(path.join(repoRoot, relativePath), "utf8");

// NEXT_PUBLIC_ADMIN_API_KEY= には一致させず、ADMIN_API_KEY= 単体だけを拾う
const assignsServerOnlyEnv = (text: string) => new RegExp(`(^|[^A-Z_])${SERVER_ONLY_ENV}=`, "m").test(text);

describe("admin のサーバー側が読む ADMIN_API_KEY の設定経路", () => {
  it("サーバー側のコードが ADMIN_API_KEY を読んでいる（前提の確認）", () => {
    expect(read("apps/admin/app/api/admin/reports/[slug]/config/route.ts")).toContain(`process.env.${SERVER_ONLY_ENV}`);
    expect(read("apps/admin/app/_components/ReportCard/DuplicateReportDialog/actions.ts")).toContain(
      `process.env.${SERVER_ONLY_ENV}`,
    );
  });

  it("make azure-config-update が admin コンテナに ADMIN_API_KEY を渡す", () => {
    const makefile = read("Makefile");
    const target = makefile.match(/^azure-config-update:\n([\s\S]*?)(?=\n\S)/m);
    expect(target).not.toBeNull();
    const adminUpdate = target?.[1].match(/az containerapp update --name admin [\s\S]*?(?=&& \\\n\s*echo|"\s*$)/);
    expect(adminUpdate).not.toBeNull();
    expect(adminUpdate?.[0]).toContain(`'${SERVER_ONLY_ENV}=$(${SERVER_ONLY_ENV})'`);
  });

  it("azure-deploy.yml の admin 更新が ADMIN_API_KEY を secret から渡す", () => {
    const workflow = read(".github/workflows/azure-deploy.yml");
    const adminUpdate = workflow.match(/az containerapp update --name admin [\s\S]*?update_pids\+=/);
    expect(adminUpdate).not.toBeNull();
    expect(adminUpdate?.[0]).toContain(`"${SERVER_ONLY_ENV}=secretref:admin-api-key"`);
  });

  it("apps/admin/.env-sample に ADMIN_API_KEY があり、NEXT_PUBLIC_ADMIN_API_KEY と同じ値になっている", () => {
    const envSample = read("apps/admin/.env-sample");
    expect(assignsServerOnlyEnv(envSample)).toBe(true);
    const serverValue = envSample.match(/^ADMIN_API_KEY=(.*)$/m)?.[1];
    const publicValue = envSample.match(/^NEXT_PUBLIC_ADMIN_API_KEY=(.*)$/m)?.[1];
    expect(serverValue).toBe(publicValue);
  });
});

describe("ADMIN_API_KEY が無いときの案内", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    // NEXT_PUBLIC_ADMIN_API_KEY だけがあり、ADMIN_API_KEY が無い環境（Azure の旧設定と同じ組み合わせ）
    const { ADMIN_API_KEY: _omitted, ...rest } = originalEnv;
    process.env = { ...rest, NEXT_PUBLIC_ADMIN_API_KEY: "public-only", API_BASEPATH: "http://api.test" };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it("再利用設定の取得は 500 を返し、admin 側に ADMIN_API_KEY を足すよう案内する", async () => {
    const fetchMock = jest.fn();
    global.fetch = fetchMock;

    const response = await GET(new Request("http://admin.test"), { params: Promise.resolve({ slug: "r1" }) });

    expect(response.status).toBe(500);
    const body = await response.json();
    expect(body.detail).toContain("ADMIN_API_KEY is not set");
    expect(body.detail).toContain("admin のサーバー側の環境変数");
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
