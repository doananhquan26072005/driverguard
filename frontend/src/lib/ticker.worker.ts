// Timer of steadyInterval (ticker.ts): a dedicated worker's timers are not slowed down while its
// page is in the background, so the ticks it posts keep their pace. Posted: the period in ms.
let id: ReturnType<typeof setInterval> | undefined;

self.onmessage = (e: MessageEvent<number>) => {
  clearInterval(id);
  id = setInterval(() => self.postMessage(0), e.data);
};
