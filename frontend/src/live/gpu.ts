// Which delegate MediaPipe gets (M51). Its "GPU" delegate runs on WebGL. Where WebGL is drawn by a
// software rasterizer (no usable GPU: a headless browser, a blocked or missing driver, some virtual
// machines), every frame is rendered on the CPU, far slower than MediaPipe's own CPU path. Measured
// in Chromium on the same machine and clip: 45 ms per frame on SwiftShader with the GPU delegate,
// 9 ms with the CPU delegate; 11 ms on a real GPU (eval/results/benchmark_web.md).

export type GpuKind = "hardware" | "software" | "none";

const SOFTWARE = /swiftshader|llvmpipe|softpipe|software|basic render|mesa offscreen/i;

/** What draws WebGL here, from the renderer's name (null / empty = no WebGL at all). */
export function gpuKind(renderer: string | null | undefined): GpuKind {
  if (!renderer) return "none";
  return SOFTWARE.test(renderer) ? "software" : "hardware";
}

/** The WebGL renderer's name as the browser reports it; null when WebGL 2 is not available. */
export function webglRenderer(): string | null {
  try {
    const gl = document.createElement("canvas").getContext("webgl2");
    if (!gl) return null;
    const info = gl.getExtension("WEBGL_debug_renderer_info");
    const name = info ? gl.getParameter(info.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
    gl.getExtension("WEBGL_lose_context")?.loseContext();
    return name ? String(name) : null;
  } catch {
    return null;
  }
}

/** GPU only where a real one draws WebGL; a forced value (measurements) wins. */
export function chooseDelegate(kind: GpuKind, forced: string | null): "GPU" | "CPU" {
  if (forced === "GPU" || forced === "CPU") return forced;
  return kind === "hardware" ? "GPU" : "CPU";
}

/** Threads the phone detector's session may use: phone.num_threads where the page is cross-origin
 *  isolated (wasm threads need SharedArrayBuffer) and the machine has that many cores, else one. */
export function yoloThreads(wanted: number, isolated: boolean, cores: number | undefined): number {
  if (!isolated) return 1;
  return Math.max(1, Math.min(Math.floor(wanted) || 1, cores || 1));
}
