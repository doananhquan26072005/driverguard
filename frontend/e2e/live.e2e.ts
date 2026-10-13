// #/live end to end: the real page, Pyodide running edge_agent/ (blocks 6-14) and the backend on a
// throwaway database. Block 3 is fed synthetic landmark numbers (tools/e2e_setup.py) through the
// E2E hook of src/live/agent.ts; the vehicle speed comes from a stubbed driving simulator.
import { readFileSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";

const FACES = JSON.parse(readFileSync(new URL("./.cache/faces.json", import.meta.url), "utf8")) as {
  open: number[];
  shut: number[];
};
const DRIVE_SIM = "http://127.0.0.1:8766/can";
const PASSWORD = "e2e-password-1"; // tools/e2e_setup.py
const READY_MS = 180_000; // first Pyodide load of a fresh browser profile

interface State {
  connected?: boolean;
  level?: number;
  reasons?: string[];
  enrollment?: { status: string };
  vehicle?: { driving: boolean; turn_signal?: string | null; signal_lost?: boolean };
}

/** The driving simulator (tools/drive_sim.py) answers with this speed; 0 km/h = parked. */
async function stubSimulator(page: Page): Promise<{ speed: number }> {
  const sim = { speed: 0 };
  await page.route(DRIVE_SIM, (route) =>
    route.fulfill({
      contentType: "application/json",
      headers: { "Access-Control-Allow-Origin": "*" },
      body: JSON.stringify({ speed_kmh: sim.speed, turn_signal: null }),
    }),
  );
  return sim;
}

/** A driver who follows the HUD: eyes open, shut while enrollment asks for it. */
async function obedientDriver(page: Page, faces = FACES) {
  await page.addInitScript((f) => {
    const w = window as unknown as {
      __dgFeed: unknown;
      __dgState?: State;
      __dgShut: boolean;
    };
    w.__dgShut = false;
    const frame = (shut: boolean) => ({ faces: [shut ? f.shut : f.open], blink: shut ? [0.9, 0.9] : [0.05, 0.05], brow: [0] });
    w.__dgFeed = frame(false);
    setInterval(() => {
      const asked = w.__dgState?.enrollment?.status === "close_eyes";
      w.__dgFeed = frame(asked || w.__dgShut);
    }, 30);
  }, faces);
}

const state = (page: Page) => page.evaluate(() => (window as unknown as { __dgState?: State }).__dgState ?? {});
const shutEyes = (page: Page, shut: boolean) =>
  page.evaluate((s) => void ((window as unknown as { __dgShut: boolean }).__dgShut = s), shut);

async function startLive(page: Page, login?: string) {
  await page.goto("/#/live");
  if (login) {
    await page.getByLabel("Tên đăng nhập").fill(login);
    await page.getByLabel("Mật khẩu").fill(PASSWORD);
    await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  } else {
    await page.getByRole("button", { name: "Dùng thử không lưu" }).click();
  }
  // No second press: logging in (a driver) or the try-out starts the camera at once.
  await expect.poll(async () => (await state(page)).connected, { timeout: READY_MS }).toBe(true);
}

/** The consent screen comes first: it says the face is not stored or sent; the driver agrees. */
async function agree(page: Page) {
  await expect(page.getByRole("heading", { name: "Làm quen khuôn mặt" })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(/Không chụp, không lưu ảnh khuôn mặt/)).toBeVisible();
  expect((await state(page)).enrollment?.status).toBe("consent"); // nothing measured before the answer
  await page.getByRole("button", { name: "Đồng ý, bắt đầu" }).click();
}

async function enrolled(page: Page) {
  await expect.poll(async () => (await state(page)).enrollment?.status, { timeout: 40_000 }).toBe("done");
}

async function endTrip(page: Page) {
  await page.getByRole("button", { name: "Kết thúc ca lái" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Kết thúc", exact: true }).click();
  await expect(page.getByText(/^Tổng kết ca lái · /)).toBeVisible();
}

test("guest: agrees, enrolls while parked, eyes shut while driving is L3, the trip ends with a summary", async ({ page }) => {
  const sim = await stubSimulator(page);
  await obedientDriver(page);
  await startLive(page);
  const car = page.getByRole("region", { name: "Xe", exact: true });
  await agree(page);
  await expect(page.getByText("Xe đang đỗ · 0 km/h")).toBeVisible(); // the enrollment steps fill the screen (M58)
  await enrolled(page);

  sim.speed = 60;
  await expect(car.getByText("Đang lái", { exact: true })).toBeVisible();
  await page.waitForTimeout(12_000); // the open-eye baseline settles
  expect((await state(page)).level).toBe(0);
  await shutEyes(page, true);
  await expect.poll(async () => (await state(page)).level, { timeout: 10_000 }).toBe(3);
  expect((await state(page)).reasons).toContain("microsleep");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Mở mắt! Dừng xe nghỉ ngay");
  await shutEyes(page, false);
  await expect.poll(async () => (await state(page)).level, { timeout: 15_000 }).toBeLessThan(3);

  // M72: no one-touch way to stop or hide the monitoring. The demo button and the Dashboard link are
  // not on this HUD; "Dừng camera" asks first, and "Tiếp tục lái" leaves everything running.
  await expect(page.getByRole("button", { name: "Chạy mô phỏng" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Dashboard" })).toHaveCount(0);
  await page.getByRole("button", { name: "Dừng camera" }).click();
  const ask = page.getByRole("dialog");
  await expect(ask.getByRole("heading", { name: "Kết thúc ca lái?" })).toBeVisible();
  await ask.getByRole("button", { name: "Tiếp tục lái" }).click();
  await expect(ask).toHaveCount(0);
  const before = (await state(page)) as State & { updated_at?: number };
  await page.waitForTimeout(1_000);
  const after = (await state(page)) as State & { updated_at?: number };
  expect(after.connected).toBe(true);
  expect(after.updated_at ?? 0).toBeGreaterThan(before.updated_at ?? 0); // the loop is still running

  // ... and "Kết thúc" there ends the trip like the HUD's own button: the summary, the camera off.
  await page.getByRole("button", { name: "Dừng camera" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Kết thúc", exact: true }).click();
  await expect(page.getByText(/^Tổng kết ca lái · /)).toBeVisible();
  await expect(page.getByText("Chế độ dùng thử: bản tổng kết không được gửi đi.")).toBeVisible();
  // "Xong" goes back to the first page (13/10: it did nothing once the trip had ended).
  await page.getByRole("button", { name: "Xong" }).click();
  await expect(page.getByRole("button", { name: "Dùng thử không lưu" })).toBeVisible();
});

test("no face in view: the frames still run in Python, monitoring pauses, nothing fails", async ({ page }) => {
  // M50: a frame without a face used to raise in Pyodide (a JS null is not Python's None there).
  await stubSimulator(page);
  await page.addInitScript(() => void ((window as unknown as { __dgFeed: unknown }).__dgFeed = { faces: [], blink: [], brow: [] }));
  await startLive(page);
  await page.waitForTimeout(3_000);
  const s = (await state(page)) as State & { error?: string; processing_error?: boolean; fps?: number };
  expect(s.error).toBeUndefined();
  expect(s.processing_error).toBe(false);
  expect(s.fps ?? 0).toBeGreaterThan(5);
});

test("the loop recovers by itself: quiet frame callback, frames failing in the page, camera ended", async ({ page }) => {
  // M71. Nothing of this needed a reload before only by luck: the loop had no watch on itself.
  type Health = State & {
    updated_at?: number;
    processing_error?: boolean;
    camera_lost?: boolean;
    error?: string;
    incident?: { kind: string; attempts: number | null } | null;
  };
  const health = () => state(page) as Promise<Health>;
  const fresh = async () => Date.now() / 1000 - ((await health()).updated_at ?? 0);
  const open = { faces: [FACES.open], blink: [0.05, 0.05], brow: [0] };
  await stubSimulator(page);
  await page.addInitScript((f) => void ((window as unknown as { __dgFeed: unknown }).__dgFeed = f), open);
  await startLive(page);

  // 1. The browser stops calling requestVideoFrameCallback (what a stalled loop looked like in M67's
  //    long runs): after capture.frame_timeout_s a timer pulls the frames.
  await page.evaluate(() => void (HTMLVideoElement.prototype.requestVideoFrameCallback = () => 0));
  await expect.poll(fresh, { timeout: 5_000 }).toBeGreaterThan(2); // it did stand still
  await expect.poll(fresh, { timeout: 10_000 }).toBeLessThan(1);
  await page.waitForTimeout(3_000);
  expect(await fresh()).toBeLessThan(1); // and it keeps going
  expect((await health()).camera_lost).toBe(false);

  // 2. Frames fail in the page itself, before Python: "processing error", gone with the next good frame.
  await page.evaluate(() => void ((window as unknown as { __dgFeed: unknown }).__dgFeed = { faces: 1 }));
  await expect.poll(async () => (await health()).processing_error, { timeout: 10_000 }).toBe(true);
  expect((await health()).incident?.kind).toBe("processing_error");
  await page.evaluate((f) => void ((window as unknown as { __dgFeed: unknown }).__dgFeed = f), open);
  await expect.poll(async () => (await health()).processing_error, { timeout: 10_000 }).toBe(false);

  // 3. The camera track ends: lost at once, asked for again, monitoring resumes on the new stream.
  await page.evaluate(() => {
    const ask = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = async (c) => {
      await new Promise((r) => setTimeout(r, 3_000)); // long enough for the test to see "lost"
      return ask(c);
    };
    const video = document.querySelector("video")!;
    (video.srcObject as MediaStream).getVideoTracks()[0].stop();
  });
  await expect.poll(async () => (await health()).camera_lost, { timeout: 5_000 }).toBe(true);
  expect((await health()).incident).toMatchObject({ kind: "camera_lost", attempts: 1 });
  await expect.poll(async () => (await health()).camera_lost, { timeout: 15_000 }).toBe(false);
  await expect.poll(fresh, { timeout: 5_000 }).toBeLessThan(1);
});

test("a camera that hands over the same image again and again is a lost camera", async ({ page }) => {
  // M83. Frames keep arriving, so the watch on the loop (M71) saw nothing: a face that never moves.
  type Health = State & { camera_lost?: boolean; incident?: { kind: string; attempts: number | null } | null };
  const health = () => state(page) as Promise<Health>;
  const open = { faces: [FACES.open], blink: [0.05, 0.05], brow: [0] };
  await stubSimulator(page);
  await page.addInitScript((f) => void ((window as unknown as { __dgFeed: unknown }).__dgFeed = f), open);
  await startLive(page);
  await page.waitForTimeout(5_000);
  expect((await health()).camera_lost).toBe(false); // Chrome's fake camera moves: not a repeat

  // The video now shows a canvas repainted with the same pixels on every animation frame.
  const delivered = await page.evaluate(async () => {
    const ask = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = async (c) => {
      await new Promise((r) => setTimeout(r, 3_000)); // long enough for the test to see "lost"
      return ask(c);
    };
    const canvas = document.createElement("canvas");
    [canvas.width, canvas.height] = [640, 360];
    const ctx = canvas.getContext("2d")!;
    const still = ctx.createImageData(640, 360);
    for (let i = 0; i < still.data.length; i++) still.data[i] = i % 4 === 3 ? 255 : (i * 2654435761) >>> 24;
    const paint = () => {
      ctx.putImageData(still, 0, 0);
      requestAnimationFrame(paint);
    };
    paint();
    const video = document.querySelector("video")!;
    video.srcObject = canvas.captureStream(30);
    void video.play();
    let frames = 0;
    const count = () => {
      frames += 1;
      video.requestVideoFrameCallback(count);
    };
    video.requestVideoFrameCallback(count);
    await new Promise((r) => setTimeout(r, 2_000));
    return frames;
  });
  expect(delivered).toBeGreaterThan(10); // frames do arrive: it is their content that stands still
  await expect.poll(async () => (await health()).camera_lost, { timeout: 5_000 }).toBe(true);
  expect((await health()).incident?.kind).toBe("camera_lost");
  // Asked for again like a camera that ended (at the watch's next look): back on the stream that moves.
  await expect.poll(async () => (await health()).incident?.attempts, { timeout: 3_000 }).toBe(1);
  await expect.poll(async () => (await health()).camera_lost, { timeout: 15_000 }).toBe(false);
});

test("signed-in driver: change of driver enrolls again; the manager gets the trip report", async ({ page, browser }) => {
  await stubSimulator(page);
  await obedientDriver(page);
  await startLive(page, "an");
  await agree(page);
  await enrolled(page);

  await page.getByRole("button", { name: "Đổi tài xế" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Đổi tài xế" }).click();
  await expect.poll(async () => (await state(page)).enrollment?.status).not.toBe("done");
  await agree(page); // the new driver is asked again
  await enrolled(page); // the new driver (same synthetic face) enrolls

  // M33: while the trip runs, the manager's fleet overview has this browser as a vehicle that is alive.
  const manager = await (await browser.newContext()).newPage();
  await manager.goto("/#/dashboard");
  await manager.getByLabel("Tên đăng nhập").fill("quanly");
  await manager.getByLabel("Mật khẩu").fill(PASSWORD);
  await manager.getByRole("button", { name: "Đăng nhập" }).click();
  await manager.getByRole("link", { name: "Đội xe", exact: true }).click();
  const vehicle = manager.getByRole("row").filter({ hasText: "web-an" });
  const fleetShows = (text: string) =>
    expect(async () => {
      await manager.getByRole("button", { name: "Làm mới" }).click();
      await expect(vehicle).toContainText(text, { timeout: 2_000 });
    }).toPass({ timeout: 30_000 });
  await fleetShows("Đang hoạt động");
  await expect(vehicle).toContainText("drv-001");

  await endTrip(page);
  await expect(page.getByText("Đã gửi bản tổng kết cho quản lý đội xe.")).toBeVisible();
  await fleetShows("Đã kết thúc ca lái"); // an ended trip, not a lost vehicle
  // M49: the page timed its own loop and the heartbeat carried the numbers to the fleet overview.
  await expect(vehicle).toContainText(/p95 [\d,.]+ ms/);

  // M62: the manager reviews the report (list + detail), and marks it read.
  await manager.getByRole("link", { name: /^Báo cáo ca lái/ }).click();
  const report = manager.getByRole("region", { name: "Danh sách báo cáo" }).getByRole("button").filter({ hasText: "drv-001" });
  await expect(report).toHaveCount(1);
  await report.click();
  await expect(manager.getByText(/đổi tài 1 lần/)).toBeVisible(); // report detail: the story of the trip
  // M105: a note for the driver goes with "Đánh dấu đã xem"; the driver reads it under "Lưu ý".
  await manager.getByRole("textbox", { name: /Lưu ý cho tài xế/ }).fill("Nghỉ giữa ca sau 2 giờ lái nhé.");
  await manager.getByRole("button", { name: "Đánh dấu đã xem" }).click();
  await expect(manager.getByText(/quanly đã xem lúc/)).toBeVisible();
  await page.getByRole("button", { name: "Xong" }).click(); // the driver's overview, with its recent trips
  await expect(page.getByRole("columnheader", { name: "Lưu ý" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Nghỉ giữa ca sau 2 giờ lái nhé." })).toBeVisible();
});

test("web driving controls: #/drive on another page drives #/live; closing it is a lost vehicle signal", async ({ page, context }) => {
  // No terminal simulator here: the speed comes from #/drive through the backend (M31).
  await obedientDriver(page);
  await startLive(page);
  const link = page.getByRole("link", { name: /Điều khiển xe · mã/ });
  const code = /mã ([A-Z0-9]{6})/.exec((await link.getAttribute("aria-label")) ?? "")?.[1];
  expect(code).toBeTruthy();
  expect(await link.getAttribute("href")).toBe(`#/drive?code=${code}`);

  const remote = await context.newPage();
  await remote.goto(`/#/drive?code=${code}`);
  await expect(remote.getByText(`Mã ${code}`)).toBeVisible();
  await remote.getByRole("button", { name: "Chạy đều 50" }).click();
  await remote.getByRole("button", { name: /Trái/ }).click();
  await expect(remote.getByText("Đang gửi cho trang giám sát")).toBeVisible();
  await expect
    .poll(async () => (await state(page)).vehicle, { timeout: 20_000 })
    .toMatchObject({ driving: true, turn_signal: "left" });

  await remote.close(); // the remote goes quiet while driving
  await expect.poll(async () => (await state(page)).vehicle?.signal_lost, { timeout: 10_000 }).toBe(true);
  await expect(page.getByText("Mất tín hiệu tốc độ xe: vẫn theo dõi như đang chạy")).toBeVisible();
});

test("leaving #/live with the trip running ends the trip: the manager sees it ended, with its report", async ({ page, browser }) => {
  // M72. Before, another address just stopped the camera: no summary, no "ended", a vehicle "lost" 90 s later.
  await stubSimulator(page);
  await page.addInitScript(
    (f) => void ((window as unknown as { __dgFeed: unknown }).__dgFeed = f),
    { faces: [FACES.open], blink: [0.05, 0.05], brow: [0] },
  );
  await startLive(page, "an");

  const manager = await (await browser.newContext()).newPage();
  await manager.goto("/#/dashboard");
  await manager.getByLabel("Tên đăng nhập").fill("quanly");
  await manager.getByLabel("Mật khẩu").fill(PASSWORD);
  await manager.getByRole("button", { name: "Đăng nhập" }).click();
  await manager.getByRole("link", { name: "Đội xe", exact: true }).click();
  const vehicle = manager.getByRole("row").filter({ hasText: "web-an" });
  const fleetShows = (text: string) =>
    expect(async () => {
      await manager.getByRole("button", { name: "Làm mới" }).click();
      await expect(vehicle).toContainText(text, { timeout: 2_000 });
    }).toPass({ timeout: 30_000 });
  await fleetShows("Đang hoạt động");
  await manager.getByRole("link", { name: /^Báo cáo ca lái/ }).click();
  const reports = manager.getByRole("region", { name: "Danh sách báo cáo" }).getByRole("button").filter({ hasText: "drv-001" });
  await expect(manager.getByRole("region", { name: "Danh sách báo cáo" })).toBeVisible();
  await manager.waitForTimeout(1_000); // the list has loaded
  const before = await reports.count(); // reports of earlier tests still listed, if any

  await page.evaluate(() => void (location.hash = "#/dashboard")); // the driver's page goes elsewhere
  await expect(page.getByRole("button", { name: "Kết thúc ca lái" })).toHaveCount(0);

  await manager.getByRole("link", { name: "Đội xe", exact: true }).click();
  await fleetShows("Đã kết thúc ca lái");
  await manager.getByRole("link", { name: /^Báo cáo ca lái/ }).click();
  await expect(reports).toHaveCount(before + 1);
});

test("closing the tab with the trip running ends the trip too: the manager sees it ended, with its report", async ({ page, browser }) => {
  // M100. Before, a closed or reloaded tab left no summary and no "ended": the fleet showed "lost" 90 s later.
  await stubSimulator(page);
  await page.addInitScript(
    (f) => void ((window as unknown as { __dgFeed: unknown }).__dgFeed = f),
    { faces: [FACES.open], blink: [0.05, 0.05], brow: [0] },
  );
  await startLive(page, "an");

  const manager = await (await browser.newContext()).newPage();
  await manager.goto("/#/dashboard");
  await manager.getByLabel("Tên đăng nhập").fill("quanly");
  await manager.getByLabel("Mật khẩu").fill(PASSWORD);
  await manager.getByRole("button", { name: "Đăng nhập" }).click();
  await manager.getByRole("link", { name: "Đội xe", exact: true }).click();
  const vehicle = manager.getByRole("row").filter({ hasText: "web-an" });
  const fleetShows = (text: string) =>
    expect(async () => {
      await manager.getByRole("button", { name: "Làm mới" }).click();
      await expect(vehicle).toContainText(text, { timeout: 2_000 });
    }).toPass({ timeout: 30_000 });
  await fleetShows("Đang hoạt động");
  await manager.getByRole("link", { name: /^Báo cáo ca lái/ }).click();
  const reports = manager.getByRole("region", { name: "Danh sách báo cáo" }).getByRole("button").filter({ hasText: "drv-001" });
  await expect(manager.getByRole("region", { name: "Danh sách báo cáo" })).toBeVisible();
  await manager.waitForTimeout(1_000); // the list has loaded
  const before = await reports.count();

  await page.close({ runBeforeUnload: true }); // the browser's own "leave this page?" is accepted by Playwright

  await manager.getByRole("link", { name: "Đội xe", exact: true }).click();
  await fleetShows("Đã kết thúc ca lái");
  await manager.getByRole("link", { name: /^Báo cáo ca lái/ }).click();
  await expect(reports).toHaveCount(before + 1);
});

test("the first page is the login page: a manager goes to the dashboard, a driver who is logged in starts from it", async ({ page }) => {
  await stubSimulator(page);
  await page.goto("/"); // no address
  await expect(page.getByRole("link", { name: /Hướng dẫn sử dụng/ })).toBeVisible();
  await page.getByLabel("Tên đăng nhập").fill("quanly");
  await page.getByLabel("Mật khẩu").fill(PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await expect(page).toHaveURL(/#\/dashboard/);
  await expect(page.getByRole("link", { name: "Đội xe", exact: true })).toBeVisible();
  expect((await state(page)).connected ?? false).toBe(false); // no camera was opened for a manager

  // A driver's session from an earlier visit: no form, one press starts the trip.
  await page.getByRole("button", { name: "Đăng xuất" }).click();
  await page.getByLabel("Tên đăng nhập").fill("an");
  await page.getByLabel("Mật khẩu").fill(PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await expect(page.getByRole("button", { name: "Đăng xuất" })).toBeVisible();
  await page.goto("/#/live");
  await expect(page.getByText("Đăng nhập: an")).toBeVisible();
  await page.getByRole("button", { name: "Cho phép camera và bắt đầu" }).click();
  await expect.poll(async () => (await state(page)).connected, { timeout: READY_MS }).toBe(true);
});

test("the self-view can be dragged off the HUD's buttons and resized, and remembers where it was put", async ({ page }) => {
  // M100 (the user's choice of 09/10). Before, it sat fixed over "Cảnh báo này sai?" (roadmap M89).
  // Floating only on an upright screen since M103 (landscape: a card in the column beside the HUD).
  await page.setViewportSize({ width: 800, height: 1280 });
  await stubSimulator(page);
  await page.addInitScript(
    (f) => void ((window as unknown as { __dgFeed: unknown }).__dgFeed = f),
    { faces: [FACES.open], blink: [0.05, 0.05], brow: [0] },
  );
  await startLive(page);
  const frame = page.getByTestId("self-view");
  const start = (await frame.boundingBox())!;
  expect(Math.round(start.width)).toBe(176);

  await page.mouse.move(start.x + 40, start.y + 30);
  await page.mouse.down();
  await page.mouse.move(500, 120, { steps: 5 });
  await page.mouse.up();
  const moved = (await frame.boundingBox())!;
  expect(Math.abs(moved.x - (500 - 40))).toBeLessThan(3);
  expect(Math.abs(moved.y - (120 - 30))).toBeLessThan(3);

  await page.getByRole("button", { name: "Phóng to khung camera" }).click();
  expect(Math.round((await frame.boundingBox())!.width)).toBe(264);
  await expect(page.getByRole("button", { name: "Phóng to khung camera" })).toBeDisabled();
  await page.getByRole("button", { name: "Thu nhỏ khung camera" }).click();
  await page.getByRole("button", { name: "Thu nhỏ khung camera" }).click();
  expect(Math.round((await frame.boundingBox())!.width)).toBe(112);

  await page.mouse.move(moved.x + 20, moved.y + 20);
  await page.mouse.down();
  await page.mouse.move(5000, 5000, { steps: 5 }); // thrown past the corner: it stays inside the window
  await page.mouse.up();
  const cornered = (await frame.boundingBox())!;
  const view = page.viewportSize()!;
  expect(cornered.x + cornered.width).toBeLessThanOrEqual(view.width);
  expect(cornered.y + cornered.height).toBeLessThanOrEqual(view.height);

  const stored = await page.evaluate(() => JSON.parse(localStorage.getItem("dg.live.selfview") ?? "null"));
  expect(stored).toMatchObject({ size: 0, x: Math.round(cornered.x), y: Math.round(cornered.y) });
});

test("landscape: the camera and the driving panel sit beside the HUD, and the panel drives #/live", async ({ page }) => {
  // M103. No terminal simulator and no #/drive page: the speed goes from the panel straight to the agent.
  await obedientDriver(page);
  await startLive(page);
  const side = page.getByRole("complementary", { name: "Camera và điều khiển xe" });
  await expect(side).toBeVisible();
  await expect(page.getByTestId("self-view")).toHaveAttribute("data-docked", "true");
  await expect(page.getByRole("button", { name: "Phóng to khung camera" })).toHaveCount(0); // not dragged or resized
  await expect(page.getByRole("button", { name: /chi tiết kỹ thuật/i })).toHaveCount(0); // a picture, no engineers' numbers
  await expect(side.getByRole("note")).toHaveText("Phần này chỉ hiện khi mô phỏng ứng dụng, khi lái thật sẽ không có.");
  // M104: the driver's face drawn over the picture, on by default, switched off and on by its button.
  const drawing = page.getByTestId("face-overlay");
  await expect(drawing).toBeVisible();
  await expect.poll(() => drawing.evaluate((c: HTMLCanvasElement) => {
    const d = c.getContext("2d")!.getImageData(0, 0, c.width, c.height).data;
    for (let i = 3; i < d.length; i += 4) if (d[i] > 0) return true; // something was drawn
    return false;
  }), { timeout: 10_000 }).toBe(true);
  await page.getByRole("button", { name: "Ẩn khung nhận diện mặt" }).click();
  await expect(drawing).toHaveCount(0);
  await page.getByRole("button", { name: "Hiện khung nhận diện mặt" }).click();
  await expect(drawing).toBeVisible();

  // The HUD is scaled into the room left of the column, the whole of it in view.
  const hud = (await page.locator(".live-hud-screen").boundingBox())!;
  const column = (await side.boundingBox())!;
  const view = page.viewportSize()!;
  expect(hud.x + hud.width).toBeLessThanOrEqual(column.x);
  expect(hud.y + hud.height).toBeLessThanOrEqual(view.height);
  expect(Math.abs(hud.width / hud.height - 1280 / 800)).toBeLessThan(0.01);

  await agree(page);
  await enrolled(page);
  const panel = page.getByRole("region", { name: "Điều khiển xe" });
  await expect(panel.getByText("Bấm một nút để bắt đầu lái")).toBeVisible();
  await panel.getByRole("button", { name: "Chạy đều 50" }).click();
  await panel.getByRole("button", { name: /Trái/ }).click();
  await expect(panel.getByText("Đang đưa vào giám sát")).toBeVisible();
  await expect
    .poll(async () => (await state(page)).vehicle, { timeout: 20_000 })
    .toMatchObject({ driving: true, turn_signal: "left" });

  await panel.getByRole("button", { name: /Dừng xe/ }).click();
  await expect.poll(async () => (await state(page)).vehicle?.driving, { timeout: 20_000 }).toBe(false);
});

test("a signed-in driver: Xong on the summary opens the Dashboard, whose Bắt đầu ca lái starts the next trip from any page", async ({ page }) => {
  // 13/10. The try-out has no account: its Xong goes back to the first page (the guest test above).
  await stubSimulator(page);
  await obedientDriver(page);
  await startLive(page, "an");
  await endTrip(page);
  await page.getByRole("button", { name: "Xong" }).click();
  await expect(page).toHaveURL(/#\/dashboard/);
  // In the side menu, so on every page: here from "Ca lái của tôi", not the overview.
  await page.getByRole("navigation", { name: "Menu" }).getByRole("link", { name: "Ca lái của tôi" }).click();
  const next = page.getByRole("navigation", { name: "Menu" }).getByRole("link", { name: /Bắt đầu ca lái/ });
  await expect(next).toBeVisible();

  await page.evaluate(() => void ((window as unknown as { __dgState?: unknown }).__dgState = undefined));
  await next.click(); // no second press on the first page: the camera opens at once
  await expect.poll(async () => (await state(page)).connected, { timeout: READY_MS }).toBe(true);
  await expect(page).toHaveURL(/#\/live$/); // `start` is gone: a reload does not start a trip by itself
});
