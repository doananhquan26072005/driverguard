// The page's measurements against the device's, on the same pixels (M88, audit A1 L4). The images
// and the device's numbers are in measure.fixture.json, written by tools/measure_fixture.py from the
// code the device runs (blocks 2, 5, 6); a Python test fails when that file is out of date. Here
// measure.ts must land within the file's tolerances, which say how far apart the two may be and why.
import { describe, expect, it } from "vitest";
import FIXTURE from "./measure.fixture.json";
import { channelDiff, lumaSpread, meanLuma, sharpness, type Box } from "./measure";

const { width, height, stride } = FIXTURE;
const box = FIXTURE.box as Box;
type Name = keyof typeof FIXTURE.images;
type Field = keyof typeof FIXTURE.tolerance;

function rgba(rgb: readonly number[]): Uint8ClampedArray {
  const px = new Uint8ClampedArray(width * height * 4).fill(255);
  for (let i = 0; i < width * height; i++) px.set(rgb.slice(i * 3, i * 3 + 3), i * 4);
  return px;
}

/** What the page hands to Python for one frame (agent.ts processFrame), by the device's names. */
function page(px: Uint8ClampedArray): Record<Field, number> {
  const scene = lumaSpread(px, width, height, stride);
  return {
    channel_diff: channelDiff(px, width, height, stride),
    face_brightness: meanLuma(px, width, height, box),
    scene_brightness: scene.mean,
    scene_contrast: scene.std,
    sharpness: sharpness(px, width, height, box)!,
  };
}

describe("the page measures an image as the device does", () => {
  for (const name of Object.keys(FIXTURE.images) as Name[]) {
    const { rgb, device } = FIXTURE.images[name];
    const measured = page(rgba(rgb));
    for (const field of Object.keys(FIXTURE.tolerance) as Field[]) {
      it(`${name}: ${field}`, () => {
        const { abs, rel } = FIXTURE.tolerance[field];
        expect(Math.abs(measured[field] - device[field])).toBeLessThanOrEqual(abs + rel * Math.abs(device[field]));
      });
    }
    it(`${name}: infrared or not, by the same two limits`, () => {
      // edge_agent/perception/preprocess.py looks_infrared: small in itself and against the brightness (M98).
      const infrared = measured.channel_diff <= FIXTURE.ir_channel_diff_max && measured.channel_diff <= FIXTURE.ir_channel_rel_max * measured.scene_brightness;
      expect(infrared).toBe(device.is_ir);
    });
  }

  it("the fixture holds what it is meant to show: a colour image, a gray one, and a dim colour one", () => {
    const { colour, dim, gray } = FIXTURE.images;
    expect(colour.device.is_ir).toBe(false);
    expect(gray.device).toMatchObject({ is_ir: true, channel_diff: 0 });
    // Audit A1 H1: the dim image is the colour one at a twelfth of the light. Its channel difference is
    // under the absolute limit, and before M98 both sides took it for infrared.
    expect(dim.device.is_ir).toBe(false);
    expect(dim.device.channel_diff).toBeGreaterThan(0);
    expect(dim.device.channel_diff).toBeLessThanOrEqual(FIXTURE.ir_channel_diff_max);
  });
});
