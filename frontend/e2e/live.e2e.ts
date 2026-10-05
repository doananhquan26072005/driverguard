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
    await expect(page.getByText(`Đăng nhập: ${login}`)).toBeVisible();
  } else {
    await page.getByRole("button", { name: "Dùng thử không lưu" }).click();
  }
  await page.getByRole("button", { name: "Cho phép camera và bắt đầu" }).click();
  await expect.poll(async () => (await state(page)).connected, { timeout: READY_MS }).toBe(true);
}

/** The consent screen comes first: it says the face is not stored or sent; the driver agrees. */
async function agree(page: Page) {
  await expect(page.getByRole("heading", { name: "Đăng ký khuôn mặt" })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(/Không chụp, không lưu ảnh khuôn mặt/)).toBeVisible();
  expect((await state(page)).enrollment?.status).toBe("consent"); // nothing measured before the answer
  await page.getByRole("button", { name: "Đồng ý, bắt đầu đăng ký" }).click();
}

async function enrolled(page: Page) {
  await expect.poll(async () => (await state(page)).enrollment?.status, { timeout: 40_000 }).toBe("done");
}

async function endTrip(page: Page) {
  await page.getByRole("button", { name: "Kết thúc chuyến" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Kết thúc", exact: true }).click();
  await expect(page.getByText("DriverGuard · Tổng kết chuyến đi")).toBeVisible();
}

test("guest: agrees, enrolls while parked, eyes shut while driving is L3, the trip ends with a summary", async ({ page }) => {
  const sim = await stubSimulator(page);
  await obedientDriver(page);
  await startLive(page);
  const car = page.getByRole("region", { name: "Xe", exact: true });
  await agree(page);
  await expect(car.getByText("Xe đang đỗ · đang đăng ký khuôn mặt")).toBeVisible();
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

  await endTrip(page);
  await expect(page.getByText("Chế độ dùng thử: bản tổng kết không được gửi đi.")).toBeVisible();
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
  await manager.getByRole("tab", { name: "Đội xe" }).click();
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
  await fleetShows("Đã kết thúc chuyến"); // an ended trip, not a lost vehicle

  await manager.getByRole("tab", { name: /Báo cáo chuyến đi/ }).click();
  const row = manager.getByRole("row").filter({ hasText: "drv-001" });
  await expect(row).toHaveCount(1);
  await row.getByRole("button").click();
  await expect(manager.getByRole("row", { name: /^Đổi tài xế/ })).toContainText("1 lần"); // report detail
});

test("web driving controls: #/drive on another page drives #/live; closing it is a lost vehicle signal", async ({ page, context }) => {
  // No terminal simulator here: the speed comes from #/drive through the backend (M31).
  await obedientDriver(page);
  await startLive(page);
  const link = page.getByRole("link", { name: /Điều khiển xe · mã/ });
  const code = /mã ([A-Z0-9]{6})/.exec((await link.textContent()) ?? "")?.[1];
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
  await expect(page.getByText("Mất tín hiệu xe: vẫn giám sát như đang chạy")).toBeVisible();
});
