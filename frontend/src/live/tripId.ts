// Trip id of the in-browser agent (the device's is edge_agent/runtime.py new_trip_id: keep the two alike).
//
// The local date and time are only there for a person reading the id: a wrong clock, a changed time
// zone or the hour repeated when clocks go back can give the same second twice, and the backend keys
// a trip summary on (device_id, trip_id). The random part is what makes the id unique (M82).

const RANDOM_BYTES = 3;

function randomHex(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(RANDOM_BYTES));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function tripId(d = new Date(), random: string = randomHex()): string {
  const p = (n: number) => String(n).padStart(2, "0");
  const day = `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}`;
  return `trip-${day}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}-${random}`;
}
