import { describe, expect, it } from "vitest";
import { chooseDelegate, gpuKind, yoloThreads } from "./gpu";

describe("which delegate MediaPipe gets (M51)", () => {
  it("tells a software rasterizer from a real GPU by the renderer's name", () => {
    expect(gpuKind("ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (LLVM 10.0.0) (0x0000C0DE)), SwiftShader driver)")).toBe("software");
    expect(gpuKind("llvmpipe (LLVM 15.0.7, 256 bits)")).toBe("software");
    expect(gpuKind("Microsoft Basic Render Driver")).toBe("software");
    expect(gpuKind("ANGLE (Apple, ANGLE Metal Renderer: Apple M5, Unspecified Version)")).toBe("hardware");
    expect(gpuKind("Mali-G52 MC2")).toBe("hardware");
    expect(gpuKind("Adreno (TM) 610")).toBe("hardware");
    expect(gpuKind(null)).toBe("none");
    expect(gpuKind("")).toBe("none");
  });

  it("uses the GPU delegate only on a real GPU", () => {
    expect(chooseDelegate("hardware", null)).toBe("GPU");
    expect(chooseDelegate("software", null)).toBe("CPU");
    expect(chooseDelegate("none", null)).toBe("CPU");
  });

  it("lets a measurement force either one, and ignores anything else", () => {
    expect(chooseDelegate("software", "GPU")).toBe("GPU");
    expect(chooseDelegate("hardware", "CPU")).toBe("CPU");
    expect(chooseDelegate("hardware", "fast")).toBe("GPU");
  });
});

describe("threads of the phone detector (M51)", () => {
  it("is one thread on a page that is not cross-origin isolated", () => {
    expect(yoloThreads(2, false, 8)).toBe(1);
  });

  it("is phone.num_threads on an isolated page, never more than the cores", () => {
    expect(yoloThreads(2, true, 8)).toBe(2);
    expect(yoloThreads(4, true, 2)).toBe(2);
    expect(yoloThreads(2, true, undefined)).toBe(1);
    expect(yoloThreads(0, true, 8)).toBe(1);
  });
});
