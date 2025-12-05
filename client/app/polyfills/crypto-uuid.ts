/**
 * Polyfill for window.crypto.randomUUID
 *
 * Some browsers and environments may not have crypto.randomUUID available.
 * This polyfill provides a fallback implementation using crypto.getRandomValues or a UUID v4 generator.
 *
 * Guard: Only runs in browser environment (typeof window !== "undefined")
 * Idempotent: Only defines if not already present
 */

export function initCryptoUUIDPolyfill(): void {
  // Only run in browser environment
  if (typeof window === "undefined") {
    return;
  }

  // Check if crypto.randomUUID already exists
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return;
  }

  // Ensure window.crypto exists
  if (!window.crypto) {
    return;
  }

  // Polyfill implementation using crypto.getRandomValues
  window.crypto.randomUUID = (): string => {
    // UUID v4 format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
    // where x is any hex digit and y is one of 8, 9, A, or B.

    const buffer = new Uint8Array(16);
    crypto.getRandomValues(buffer);

    // Set version to 4 (bits 12-15 of time_hi_and_version field)
    buffer[6] = (buffer[6] & 0x0f) | 0x40;

    // Set variant to RFC 4122 (bits 6-7 of clock_seq_hi_and_reserved field)
    buffer[8] = (buffer[8] & 0x3f) | 0x80;

    // Convert buffer to UUID string format
    const hex = Array.from(buffer)
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");

    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  };
}
