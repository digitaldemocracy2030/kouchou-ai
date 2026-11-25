declare module "polybooljs" {
  export interface Polygon {
    regions: [number, number][][];
    inverted: boolean;
  }

  const polyBool: {
    intersect(a: Polygon, b: Polygon): Polygon;
    difference(a: Polygon, b: Polygon): Polygon;
  };
  export default polyBool;
}
