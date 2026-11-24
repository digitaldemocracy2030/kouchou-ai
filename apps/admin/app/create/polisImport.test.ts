import { readPolisExport } from "./polisImport";

function csv(name: string, text: string) {
  return new File([text], name, { type: "text/csv" });
}

const comments = csv(
  "comments.csv",
  "comment-id,author-id,agrees,disagrees,moderated,comment-body\n" +
    "001,100,12,4,1,公開する意見\n" +
    "2,200,0,0,-1,除外済み\n" +
    "3,300,0,0,0,未審査の意見\n" +
    "4,100,0,0,1,  ",
);

it("除外済み・空欄のみを落とし、コメントCSVの賛否件数を属性にできる", async () => {
  const result = await readPolisExport(comments, null);
  expect(result).toMatchObject({
    excluded: 1,
    blank: 1,
    comments: [
      { id: "001", comment: "公開する意見", "Polis 賛成票（全体）": "12", "Polis 反対票（全体）": "4" },
      { id: "3", comment: "未審査の意見", "Polis 賛成票（全体）": "0", "Polis 反対票（全体）": "0" },
    ],
  });
});

it("グループ 0 を保持し、パスと未投票を区別する。投票行列にないコメントの票数は空欄にする", async () => {
  const votes = csv("participants-votes.csv", "participant,group-id,001,2\n100,0,1,1\n200,1,0,\n300,,-1,\n400,1,,");
  const result = await readPolisExport(comments, votes);
  expect(result).toMatchObject({ voteSource: "matrix", matchedComments: 1, groups: 2 });
  expect(result.comments).toEqual([
    {
      id: "001",
      comment: "公開する意見",
      "Polis 賛成票（全体）": "1",
      "Polis 反対票（全体）": "1",
      "Polis パス票（全体）": "1",
      "Polis 賛成票（グループ 0）": "1",
      "Polis 反対票（グループ 0）": "0",
      "Polis パス票（グループ 0）": "0",
      "Polis 賛成票（グループ 1）": "0",
      "Polis 反対票（グループ 1）": "0",
      "Polis パス票（グループ 1）": "1",
    },
    { id: "3", comment: "未審査の意見" },
  ]);
});

it("投票履歴が時刻順でなくても参加者ごとの最新票だけを集計する", async () => {
  const votes = csv(
    "votes.csv",
    "timestamp,comment-id,voter-id,vote\n20,001,12,-1\n10,001,12,1\n15,001,13,0\n20,2,12,1",
  );
  const result = await readPolisExport(comments, null, votes);
  expect(result).toMatchObject({ voteSource: "history", matchedComments: 1, groups: 0 });
  expect(result.comments[0]).toMatchObject({
    "Polis 賛成票（全体）": "0",
    "Polis 反対票（全体）": "1",
    "Polis パス票（全体）": "1",
  });
});

it("照合できない投票CSVをそのまま取り込まない", async () => {
  const votes = csv("participants-votes.csv", "participant,group-id,999\n10,0,1");
  await expect(readPolisExport(comments, votes)).rejects.toThrow("共通のIDがありません");
});

it("最新のタイムスタンプが同じで投票が異なるときはエラーにする", async () => {
  const votes = csv("votes.csv", "timestamp,comment-id,voter-id,vote\n20,001,12,-1\n20,001,12,1");
  await expect(readPolisExport(comments, null, votes)).rejects.toThrow("同じ参加者・コメント・時刻で異なる投票");
});
