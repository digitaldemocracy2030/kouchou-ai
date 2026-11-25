import { type CsvData, parseCsv } from "./parseCsv";

const voteLabels = { agree: "賛成", disagree: "反対", pass: "パス" };
export type Vote = keyof typeof voteLabels;
type Tally = Record<Vote, number>;
type CommentVotes = Map<string, Tally>;

export type VoteEvent = { voter: string; comment: string; vote: Vote; timestamp: number };
export type ParticipantVotes = {
  ballots: Map<string, Map<string, Vote>>;
  groups: Map<string, string>;
  events: VoteEvent[];
};

export type PolisImport = {
  comments: CsvData[];
  excluded: number;
  blank: number;
  attributeColumns: string[];
  voteSource: "comments" | "matrix" | "history";
  matchedComments: number;
  groups: number;
  historyMismatch?: boolean;
  participantVotes?: ParticipantVotes;
};

function hasColumns(rows: CsvData[], columns: string[]): boolean {
  return columns.every((column) => Object.hasOwn(rows[0], column));
}

function voteFromExport(value: string | null | undefined): Vote {
  switch (value?.trim()) {
    case "1":
      return "agree";
    case "-1":
      return "disagree";
    case "0":
      return "pass";
    default:
      throw new Error("投票CSVに 1、-1、0 以外の投票値があります。");
  }
}

function tallyFor(votes: CommentVotes, commentId: string): Tally {
  let tally = votes.get(commentId);
  if (!tally) {
    tally = { agree: 0, disagree: 0, pass: 0 };
    votes.set(commentId, tally);
  }
  return tally;
}

function matrixVotes(rows: CsvData[], commentIds: Set<string>) {
  const matchedIds = [...commentIds].filter((id) => Object.hasOwn(rows[0], id));
  const totals: CommentVotes = new Map(matchedIds.map((id) => [id, { agree: 0, disagree: 0, pass: 0 }]));
  const byGroup = new Map<string, CommentVotes>();
  const ballots: ParticipantVotes["ballots"] = new Map();
  const groups: ParticipantVotes["groups"] = new Map();
  for (const row of rows) {
    const participant = row.participant?.trim();
    if (!participant || ballots.has(participant)) {
      throw new Error("参加者別投票CSVの参加者IDが空欄か重複しています。");
    }
    const ballot = new Map<string, Vote>();
    ballots.set(participant, ballot);

    const group = row["group-id"]?.trim();
    let groupVotes: CommentVotes | undefined;
    if (group && group !== "-1") {
      if (!/^\d+$/.test(group)) throw new Error("参加者別投票CSVに不正なグループIDがあります。");
      groupVotes = byGroup.get(group) ?? new Map();
      byGroup.set(group, groupVotes);
      groups.set(participant, group);
    }

    for (const id of matchedIds) {
      if (!row[id]?.trim()) continue;
      const vote = voteFromExport(row[id]);
      ballot.set(id, vote);
      tallyFor(totals, id)[vote]++;
      if (groupVotes) tallyFor(groupVotes, id)[vote]++;
    }
  }
  return { totals, byGroup, ballots, groups };
}

function historyVotes(rows: CsvData[], commentIds: Set<string>) {
  const events: VoteEvent[] = [];
  for (const row of rows) {
    const comment = row["comment-id"]?.trim();
    const voter = row["voter-id"]?.trim();
    const rawTimestamp = row.timestamp?.trim();
    const timestamp = Number(rawTimestamp);
    if (!comment || !voter || !rawTimestamp || !/^\d+$/.test(rawTimestamp) || timestamp > 8.64e15) {
      throw new Error("投票履歴CSVに空のIDか不正なタイムスタンプがあります。");
    }
    if (!commentIds.has(comment)) continue;
    const vote = voteFromExport(row.vote);
    events.push({ voter, comment, vote, timestamp });
  }
  events.sort((a, b) => a.timestamp - b.timestamp);

  const latestByVoter = new Map<string, Map<string, VoteEvent>>();
  for (const event of events) {
    const ballot = latestByVoter.get(event.voter) ?? new Map<string, VoteEvent>();
    latestByVoter.set(event.voter, ballot);
    const previous = ballot.get(event.comment);
    if (previous?.timestamp === event.timestamp && previous.vote !== event.vote) {
      throw new Error("投票履歴CSVに同じ参加者・コメント・時刻で異なる投票があります。");
    }
    ballot.set(event.comment, event);
  }

  const ballots: ParticipantVotes["ballots"] = new Map();
  const totals: CommentVotes = new Map();
  for (const [voter, latest] of latestByVoter) {
    const ballot = new Map<string, Vote>();
    for (const [comment, { vote }] of latest) {
      tallyFor(totals, comment)[vote]++;
      ballot.set(comment, vote);
    }
    ballots.set(voter, ballot);
  }
  return { totals, ballots, events };
}

function coversBallots(
  ballots: ParticipantVotes["ballots"],
  other: ParticipantVotes["ballots"],
  commentIds: Set<string>,
): boolean {
  for (const [voter, ballot] of ballots) {
    const otherBallot = other.get(voter);
    for (const [comment, vote] of ballot) {
      if (commentIds.has(comment) && otherBallot?.get(comment) !== vote) return false;
    }
  }
  return true;
}

function voteColumn(vote: Vote, group?: string): string {
  return `Polis ${voteLabels[vote]}票（${group === undefined ? "全体" : `グループ ${group}`}）`;
}

export async function readPolisExport(
  commentsFile: File,
  matrixFile: File | null,
  historyFile: File | null = null,
): Promise<PolisImport> {
  const rows = await parseCsv(commentsFile);
  if (!hasColumns(rows, ["comment-id", "comment-body", "moderated", "agrees", "disagrees"])) {
    throw new Error("Polisの comments.csv を選んでください。");
  }

  const comments: CsvData[] = [];
  const ids = new Set<string>();
  let excluded = 0;
  let blank = 0;
  for (const row of rows) {
    const id = row["comment-id"]?.trim();
    const moderation = row.moderated?.trim();
    if (!id || !/^\d+$/.test(id) || ids.has(id)) {
      throw new Error("comments.csv のコメントIDは重複のない整数である必要があります。");
    }
    ids.add(id);
    if (moderation === "-1") {
      excluded++;
      continue;
    }
    if (moderation !== "0" && moderation !== "1") {
      throw new Error("comments.csv の moderated に -1、0、1 以外の値があります。");
    }
    const body = row["comment-body"] ?? "";
    if (!body.trim()) {
      blank++;
      continue;
    }
    comments.push({ id, comment: body });
  }

  const result: PolisImport = {
    comments,
    excluded,
    blank,
    attributeColumns: [],
    voteSource: "comments",
    matchedComments: 0,
    groups: 0,
  };
  if (!matrixFile && !historyFile) {
    const activeComments = new Map(comments.map((comment) => [comment.id, comment]));
    for (const row of rows) {
      const comment = activeComments.get(row["comment-id"]?.trim() ?? "");
      if (!comment) continue;
      for (const [vote, column] of [
        ["agree", "agrees"],
        ["disagree", "disagrees"],
      ] as const) {
        const count = row[column]?.trim() ?? "";
        if (count && !/^\d+$/.test(count)) throw new Error("comments.csv に不正な投票数があります。");
        if (count) comment[voteColumn(vote)] = count;
      }
    }
    result.attributeColumns = [voteColumn("agree"), voteColumn("disagree")].filter((column) =>
      comments.some((comment) => comment[column] !== undefined),
    );
    return result;
  }

  let matrix: ReturnType<typeof matrixVotes> | undefined;
  if (matrixFile) {
    const votes = await parseCsv(matrixFile);
    if (!hasColumns(votes, ["participant", "group-id"])) {
      throw new Error("参加者別投票には Polis の participants-votes.csv を選んでください。");
    }
    matrix = matrixVotes(votes, ids);
  }

  let history: ReturnType<typeof historyVotes> | undefined;
  if (historyFile) {
    const votes = await parseCsv(historyFile);
    if (!hasColumns(votes, ["voter-id", "comment-id", "timestamp", "vote"])) {
      throw new Error("投票履歴には Polis の votes.csv を選んでください。");
    }
    history = historyVotes(votes, ids);
  }

  const source = matrix ?? history;
  if (!source?.totals.size || (history && history.totals.size === 0)) {
    throw new Error("コメントと投票に共通のIDがありません。同じ会話のCSVを選んでください。");
  }
  if (matrix && history && ![...history.ballots.keys()].some((voter) => matrix.ballots.has(voter))) {
    throw new Error("参加者別投票と履歴を照合できません。同じ会話のCSVを選んでください。");
  }
  if (matrix && history) {
    const activeIds = new Set(comments.map((comment) => comment.id));
    if (
      !coversBallots(matrix.ballots, history.ballots, activeIds) ||
      !coversBallots(history.ballots, matrix.ballots, activeIds)
    ) {
      result.historyMismatch = true;
    }
  }
  result.voteSource = matrix ? "matrix" : "history";
  result.participantVotes = {
    ballots: source.ballots,
    groups: matrix?.groups ?? new Map(),
    events: result.historyMismatch ? [] : (history?.events ?? []),
  };
  const totals = source.totals;
  const byGroup = matrix?.byGroup ?? new Map();

  const scopes = [[undefined, totals] as const, ...byGroup];
  const choices = ["agree", "disagree", "pass"] as const;
  result.matchedComments = comments.filter((comment) => totals.has(comment.id)).length;
  result.groups = byGroup.size;
  if (result.matchedComments === 0) return result;
  for (const [group, groupTotals] of scopes) {
    result.attributeColumns.push(...choices.map((vote) => voteColumn(vote, group)));
    for (const comment of comments) {
      if (!totals.has(comment.id)) continue;
      const tally = groupTotals.get(comment.id);
      for (const vote of choices) comment[voteColumn(vote, group)] = String(tally?.[vote] ?? 0);
    }
  }
  return result;
}
