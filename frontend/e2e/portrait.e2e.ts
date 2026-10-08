// The HUD on an upright screen (M89, audit A4 M9): the car's own 10 inch screen stands upright. Drawn
// screens of #/hud-preview, no camera and no agent: only where things land. Before M89 an upright
// screen got the phone's layout (800 x 1280: the bottom bar below the fold) or, from 1024 px wide,
// the landscape's two columns stretched.
import { expect, test, type Page } from "@playwright/test";

const UPRIGHT = [
  { width: 800, height: 1280 },
  { width: 1200, height: 1920 },
];
// Calm, an L1 with its false-alarm button, an L2, not monitored, enrollment, no sound yet.
const SCREENS = ["l0", "l1", "l2p", "off", "en1", "mute", "down"];

async function open(page: Page, screen: string, night = 0) {
  await page.goto(`/#/hud-preview?s=${screen}&night=${night}`);
  await page.reload(); // the hash alone does not remount the preview
  await page.addStyleTag({ content: "[data-stage] ~ .fixed, .fixed.bottom-2.z-40 { display: none !important; }" }); // the scenario picker
  await expect(page.locator("[data-stage]")).toBeVisible();
}

/** How far the lowest and rightmost thing drawn in the stage reaches past the screen, in px. */
const overflow = (page: Page) =>
  page.evaluate(() => {
    let worst = 0;
    for (const el of document.querySelectorAll("[data-stage] *:not(.dg-backdrop)")) {
      const b = el.getBoundingClientRect();
      if (b.width && b.height) worst = Math.max(worst, b.bottom - window.innerHeight, b.right - window.innerWidth);
    }
    return { worst: Math.round(worst), scrolls: document.documentElement.scrollHeight > window.innerHeight };
  });

for (const size of UPRIGHT) {
  test(`upright ${size.width} x ${size.height}: every screen fits, on the 800 x 1280 design`, async ({ page }) => {
    await page.setViewportSize(size);
    for (const screen of SCREENS) {
      await open(page, screen);
      const stage = page.locator("[data-stage]");
      await expect(stage, screen).toHaveAttribute("data-stage", "fixed");
      await expect(stage, screen).toHaveAttribute("data-shape", "portrait");
      expect(await overflow(page), screen).toEqual({ worst: 0, scrolls: false });
    }
    // The buttons a driver needs are on the screen, side by side under the alert's own button.
    await open(page, "l1");
    const end = await page.getByRole("button", { name: /Kết thúc chuyến/ }).boundingBox();
    const driver = await page.getByRole("button", { name: /Đổi tài xế/ }).boundingBox();
    const wrong = await page.getByRole("button", { name: /Cảnh báo này sai/ }).boundingBox();
    expect(end && driver && wrong).toBeTruthy();
    expect(end!.y + end!.height).toBeLessThanOrEqual(size.height);
    expect(Math.abs(end!.y - driver!.y)).toBeLessThan(2);
    expect(wrong!.y + wrong!.height).toBeLessThanOrEqual(driver!.y);
    expect(wrong!.width).toBeGreaterThan(size.width / 2); // one line, not five
  });
}

test("the two upright sizes show the same layout, only scaled", async ({ page }) => {
  const boxes: Record<string, number>[] = [];
  for (const size of UPRIGHT) {
    await page.setViewportSize(size);
    await open(page, "l1");
    const speed = await page.getByText("km/h", { exact: true }).boundingBox();
    const title = await page.getByRole("heading", { level: 1 }).boundingBox();
    boxes.push({ speedY: speed!.y / size.height, titleY: title!.y / size.height, titleH: title!.height / size.height });
  }
  for (const key of Object.keys(boxes[0])) expect(boxes[1][key], key).toBeCloseTo(boxes[0][key], 2);
});

test("landscape keeps the 1280 x 800 design; the calm screen dims by the screen's own hours", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await open(page, "l0");
  await expect(page.locator("[data-stage]")).toHaveAttribute("data-shape", "landscape");
  expect(await overflow(page)).toEqual({ worst: 0, scrolls: false });
  await expect(page.locator("header.opacity-80")).toHaveCount(0); // day
  await open(page, "l0", 1);
  await expect(page.locator("header.opacity-80")).toHaveCount(1);
  await expect(page.getByLabel("Ban đêm")).toBeVisible();
  await open(page, "l2p", 1); // an alert is never dimmed
  await expect(page.locator("header.opacity-80")).toHaveCount(0);
});
