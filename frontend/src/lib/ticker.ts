// setInterval that keeps its pace in a background tab. Browsers slow a hidden page's timers to about
// one a second (Chrome: once a minute after 5 min), so with #/live and #/drive as two tabs of one
// window, the hidden one sent / read the speed too rarely: the reading outlived
// context.vehicle_signal_stale_s and #/live said "Mất tín hiệu xe", and the car of #/drive stood
// almost still until its tab was shown again. The ticks come from a worker (ticker.worker.ts), whose
// timers are not slowed; without workers (tests, old browsers) a plain setInterval stands in.

/** Calls fn every ms until the returned function is called. */
export function steadyInterval(fn: () => void, ms: number): () => void {
  const plain = () => {
    const id = setInterval(fn, ms);
    return () => clearInterval(id);
  };
  if (typeof Worker === "undefined") return plain();
  let worker: Worker;
  try {
    worker = new Worker(new URL("./ticker.worker.ts", import.meta.url), { type: "module" });
  } catch {
    return plain(); // refused (e.g. a Content-Security-Policy without workers)
  }
  let stop = () => worker.terminate();
  worker.onmessage = () => fn();
  worker.onerror = () => {
    worker.terminate();
    stop = plain();
  };
  worker.postMessage(ms);
  return () => stop();
}
