import type { ParticipantVotes, Vote } from "./polisImport";

const voteValue: Record<Vote, number> = { agree: 1, disagree: -1, pass: 0 };
type Coordinate = { x: number; y: number };
type SparseRow = Array<[column: number, value: number]>;

export type ParticipantPoint = Coordinate & {
  voter: string;
  group?: string;
  agree: number;
  disagree: number;
  pass: number;
};

type TimedPoint = ParticipantPoint & { timestamp: number };

function dot(a: Float64Array, b: Float64Array): number {
  let result = 0;
  for (let i = 0; i < a.length; i++) result += a[i] * b[i];
  return result;
}

function principalAxis(rows: SparseRow[], size: number, previous?: Float64Array): Float64Array {
  let axis = Float64Array.from({ length: size }, (_, i) => Math.sin((i + 1) * (previous ? 2.683 : 1.619)));
  const norm = Math.sqrt(dot(axis, axis));
  axis = axis.map((value) => value / norm);
  for (let iteration = 0; iteration < 40; iteration++) {
    // Multiply by XᵀX without allocating a dense comment × comment matrix.
    const next = new Float64Array(size);
    for (const row of rows) {
      let score = 0;
      for (const [column, value] of row) score += value * axis[column];
      for (const [column, value] of row) next[column] += value * score;
    }
    if (previous) {
      const shared = dot(next, previous);
      for (let i = 0; i < size; i++) next[i] -= shared * previous[i];
    }
    const length = Math.sqrt(dot(next, next));
    if (length < 1e-10) return new Float64Array(size);
    for (let i = 0; i < size; i++) next[i] /= length;
    const converged = Math.abs(dot(axis, next)) > 1 - 1e-10;
    axis = next;
    if (converged) break;
  }

  let dominant = 0;
  for (const value of axis) if (Math.abs(value) > Math.abs(dominant)) dominant = value;
  return dominant < 0 ? axis.map((value) => -value) : axis;
}

function lastAt(series: TimedPoint[], timestamp: number): number {
  let left = 0;
  let right = series.length;
  while (left < right) {
    const mid = Math.floor((left + right) / 2);
    if (series[mid].timestamp <= timestamp) left = mid + 1;
    else right = mid;
  }
  return left - 1;
}

/** Fit one coordinate system to the last ballots, then replay earlier ballots in that system. */
export function projectParticipants(data: ParticipantVotes, commentIds: string[]) {
  const columns = new Map(commentIds.map((id, index) => [id, index]));
  const means = new Float64Array(columns.size);
  const counts = new Uint32Array(columns.size);
  for (const ballot of data.ballots.values()) {
    for (const [id, vote] of ballot) {
      const column = columns.get(id);
      if (column === undefined) continue;
      means[column] += voteValue[vote];
      counts[column]++;
    }
  }
  for (let column = 0; column < means.length; column++) {
    if (counts[column]) means[column] /= counts[column];
  }

  // Missing cells are the final mean for that comment, so their centered contribution is zero.
  // An explicit pass has value 0 before centering and is counted as a vote.
  const rows: SparseRow[] = [];
  for (const ballot of data.ballots.values()) {
    const row: SparseRow = [];
    for (const [id, vote] of ballot) {
      const column = columns.get(id);
      if (column !== undefined) row.push([column, voteValue[vote] - means[column]]);
    }
    if (row.length) rows.push(row);
  }
  const xAxis = principalAxis(rows, columns.size);
  const yAxis = principalAxis(rows, columns.size, xAxis);

  const trajectories = new Map<string, TimedPoint[]>();
  const final = new Map<string, ParticipantPoint>();
  let extent = 0;
  let start = Number.POSITIVE_INFINITY;
  let end = Number.NEGATIVE_INFINITY;
  const createPoint = (voter: string): ParticipantPoint => ({
    voter,
    group: data.groups.get(voter),
    x: 0,
    y: 0,
    agree: 0,
    disagree: 0,
    pass: 0,
  });

  const updatePoint = (point: ParticipantPoint, column: number, vote: Vote, previous?: Vote) => {
    const before = previous === undefined ? means[column] : voteValue[previous];
    const delta = voteValue[vote] - before;
    point.x += delta * xAxis[column];
    point.y += delta * yAxis[column];
    if (previous !== undefined) point[previous]--;
    point[vote]++;
  };
  if (data.events.length) {
    const currentBallots = new Map<string, Map<string, Vote>>();
    for (const { voter, comment, vote, timestamp } of data.events) {
      const column = columns.get(comment);
      if (column === undefined) continue;
      start = Math.min(start, timestamp);
      end = Math.max(end, timestamp);
      let ballot = currentBallots.get(voter);
      if (!ballot) {
        ballot = new Map();
        currentBallots.set(voter, ballot);
      }
      const previous = ballot.get(comment);
      if (previous === vote) continue;
      ballot.set(comment, vote);
      const point = final.get(voter) ?? createPoint(voter);
      final.set(voter, point);
      updatePoint(point, column, vote, previous);
      extent = Math.max(extent, Math.abs(point.x), Math.abs(point.y));
      const history = trajectories.get(voter) ?? [];
      if (history.at(-1)?.timestamp === timestamp) history.pop();
      history.push({ ...point, timestamp });
      trajectories.set(voter, history);
    }
  } else {
    for (const [voter, ballot] of data.ballots) {
      const point = createPoint(voter);
      for (const [comment, vote] of ballot) {
        const column = columns.get(comment);
        if (column !== undefined) updatePoint(point, column, vote);
      }
      if (point.agree + point.disagree + point.pass === 0) continue;
      extent = Math.max(extent, Math.abs(point.x), Math.abs(point.y));
      final.set(voter, point);
    }
  }

  return {
    extent,
    start: Number.isFinite(start) ? start : undefined,
    end: Number.isFinite(end) ? end : undefined,
    final: [...final.values()],
    pointsAt(timestamp?: number): ParticipantPoint[] {
      if (timestamp === undefined || timestamp >= end || !trajectories.size) return [...final.values()];
      const points: ParticipantPoint[] = [];
      for (const history of trajectories.values()) {
        const index = lastAt(history, timestamp);
        if (index >= 0) points.push(history[index]);
      }
      return points;
    },
    trailFor(voter: string, timestamp?: number): Coordinate[] {
      const history = trajectories.get(voter) ?? [];
      return timestamp === undefined ? history : history.slice(0, lastAt(history, timestamp) + 1);
    },
  };
}
