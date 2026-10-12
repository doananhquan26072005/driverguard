// #/guide on the built app, under its Content-Security-Policy (M102): the guide draws the real HUD inside
// a box, so what can break is the box (a screen spilling out of it, or sized from the window) and the
// HUD's own code on a screen it was not written for. No camera, no agent, no login.
import { expect, test, type Page } from "@playwright/test";

const SIZES = [
  { width: 1280, height: 800 }, // the HUD's own landscape stage
  { width: 800, height: 1280 }, // the car's upright screen
  { width: 390, height: 800 }, // a phone
];

/** How far the HUD's stage reaches outside the guide's frame, in px. */
const spill = (page: Page) =>
  page.evaluate(() => {
    const frame = document.querySelector(".guide-screen")!.getBoundingClientRect();
    const stage = document.querySelector(".guide-screen [data-stage]")!.getBoundingClientRect();
    return Math.round(Math.max(frame.left - stage.left, stage.right - frame.right, frame.top - stage.top, stage.bottom - frame.bottom));
  });

for (const size of SIZES) {
  test(`guide ${size.width} x ${size.height}: every screen is drawn inside its frame`, async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    await page.setViewportSize(size);
    await page.goto("/#/guide");
    await page.reload();
    // The guide is an app shell: no place in it scrolls the window, in either direction.
    const fits = () =>
      page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth && document.documentElement.scrollHeight <= window.innerHeight);
    expect(await fits(), "welcome").toBe(true);
    await page.getByRole("button", { name: "Bắt đầu", exact: true }).click();
    const stage = page.locator(".guide-screen [data-stage]");
    const next = page.getByRole("button", { name: "Tiếp", exact: true });
    let steps = 0;
    for (; ; steps++) {
      await expect(stage, `step ${steps}`).toHaveAttribute("data-stage", "fixed");
      await expect(stage, `step ${steps}`).toHaveAttribute("data-shape", size.width === 800 ? "portrait" : "landscape");
      expect(await spill(page), `step ${steps}`).toBeLessThanOrEqual(1);
      expect(await fits(), `step ${steps}`).toBe(true);
      // The picture is big enough to read and the text under / beside it is on screen.
      const frame = (await page.locator(".guide-screen").boundingBox())!;
      expect(frame.width, `step ${steps}`).toBeGreaterThan(200);
      await expect(page.locator(".guide-explain h2"), `step ${steps}`).toBeInViewport();
      if (await next.isDisabled()) break;
      await next.click();
    }
    expect(steps).toBeGreaterThan(20);
    await page.getByRole("button", { name: "Trang web" }).click();
    await expect(page.getByRole("tab")).toHaveCount(4);
    expect(await fits(), "web pages").toBe(true);
    expect(errors).toEqual([]);
  });
}

test("the login page leads to the guide, and a screen in it takes no touch", async ({ page }) => {
  await page.goto("/#/dashboard");
  await page.getByRole("link", { name: /Hướng dẫn sử dụng/ }).click();
  await expect(page.getByRole("heading", { name: "Hướng dẫn sử dụng" })).toBeVisible();
  await page.getByRole("link", { name: "Về trang đăng nhập" }).click();
  await expect(page.getByRole("heading", { name: "Đăng nhập" })).toBeVisible();
  await page.goto("/#/guide/drowsy");
  await page.reload();
  await expect(page.getByRole("img", { name: /buồn ngủ/ })).toBeVisible();
  // The HUD's buttons are drawn but take nothing here (inert): a press where "Kết thúc ca lái" is drawn
  // opens no question.
  const end = await page.locator(".guide-screen button", { hasText: "Kết thúc ca lái" }).boundingBox();
  expect(end).toBeTruthy();
  await page.mouse.click(end!.x + end!.width / 2, end!.y + end!.height / 2);
  await expect(page.locator(".guide-screen [inert]")).toHaveCount(1);
  await expect(page.locator("[role=dialog]")).toHaveCount(0);
});
