import type { ParticipantVotes, Vote } from "./polisImport";
import { projectParticipants } from "./polisProjection";

it("参加者単位で最終票を2次元に並べ、似た投票を近くに置く", () => {
  const data: ParticipantVotes = {
    ballots: new Map<string, Map<string, Vote>>([
      [
        "1",
        new Map([
          ["a", "agree"],
          ["b", "agree"],
        ]),
      ],
      [
        "2",
        new Map([
          ["a", "agree"],
          ["b", "agree"],
        ]),
      ],
      [
        "3",
        new Map([
          ["a", "disagree"],
          ["b", "disagree"],
        ]),
      ],
      [
        "4",
        new Map([
          ["a", "disagree"],
          ["b", "agree"],
        ]),
      ],
    ]),
    groups: new Map([["1", "0"]]),
    events: [],
  };
  const [first, same, opposite, partial] = projectParticipants(data, ["a", "b"]).pointsAt();
  const distance = (first: { x: number; y: number }, other: { x: number; y: number }) =>
    Math.hypot(first.x - other.x, first.y - other.y);
  expect(first.group).toBe("0");
  expect(distance(first, same)).toBeCloseTo(0);
  expect(distance(first, opposite)).toBeCloseTo(Math.sqrt(8));
  expect(distance(first, partial)).toBeCloseTo(2);
});

it("投票し直すと票数と位置を更新し、投票が変わらない参加者の位置は時点間で固定する", () => {
  const data: ParticipantVotes = {
    ballots: new Map<string, Map<string, Vote>>([
      ["1", new Map([["a", "disagree"]])],
      ["2", new Map([["a", "pass"]])],
      ["3", new Map([["b", "agree"]])],
    ]),
    groups: new Map(),
    events: [
      { voter: "1", comment: "a", vote: "agree", timestamp: 10 },
      { voter: "2", comment: "a", vote: "pass", timestamp: 10 },
      { voter: "3", comment: "b", vote: "agree", timestamp: 15 },
      { voter: "1", comment: "a", vote: "disagree", timestamp: 20 },
    ],
  };
  const projection = projectParticipants(data, ["a"]);
  expect(projection.pointsAt(5)).toEqual([]);
  const [firstBefore, unchangedBefore] = projection.pointsAt(10);
  const [firstAfter, unchangedAfter] = projection.pointsAt(20);
  expect(firstBefore).toMatchObject({ voter: "1", agree: 1, disagree: 0, pass: 0 });
  expect(firstAfter).toMatchObject({ voter: "1", agree: 0, disagree: 1, pass: 0 });
  expect(firstBefore.x).not.toBeCloseTo(firstAfter.x);
  expect(unchangedBefore).toMatchObject({ voter: "2", agree: 0, disagree: 0, pass: 1 });
  expect(unchangedAfter.x).toBeCloseTo(unchangedBefore.x);
  expect(projection.final).toHaveLength(2);
  expect(projection.trailFor("1", 10)).toHaveLength(1);
  expect(projection.trailFor("1", 20)).toHaveLength(2);
});
