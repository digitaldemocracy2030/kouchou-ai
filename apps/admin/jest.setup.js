import "@testing-library/jest-dom";

if (!global.structuredClone) {
  global.structuredClone = function structuredClone(objectToClone) {
    if (objectToClone === undefined) return undefined;
    return JSON.parse(JSON.stringify(objectToClone));
  };
}
