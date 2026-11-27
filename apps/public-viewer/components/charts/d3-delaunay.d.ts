declare module "d3-delaunay" {
  type Point = [number, number];
  export class Delaunay {
    static from(points: Iterable<Point>): Delaunay;
    voronoi(bounds: [number, number, number, number]): {
      cellPolygon(index: number): Point[] | null;
    };
  }
}
