// @vitest-environment jsdom
// Every login page fills in the demo driver (13/10): one press logs in. On the first page it leads to the
// camera, on the Dashboard's login to the driver's pages.
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DEMO_DRIVER } from "../lib/demo";
import Login from "./Login";

vi.mock("../lib/api", () => ({
  ApiError: class extends Error {},
  login: vi.fn(async (username: string) => ({ username, role: "driver", token: "t" })),
}));

let host: HTMLDivElement;
let root: Root;
const fields = () => [...host.querySelectorAll("input")].map((i) => i.value);

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
});

afterEach(() => {
  act(() => root.unmount());
  host.remove();
});

const live = { session: null, onStart: () => undefined, onGuest: () => undefined, onSwitch: () => undefined };

describe("login page", () => {
  it("on the first page, the demo driver is filled in and one press logs in with it", async () => {
    expect(DEMO_DRIVER).not.toBeNull();
    const onLogin = vi.fn();
    act(() => root.render(<Login onLogin={onLogin} live={live} />));
    expect(fields()).toEqual([DEMO_DRIVER!.username, DEMO_DRIVER!.password]);
    expect(host.textContent).toContain(`tài khoản tài xế dùng thử ${DEMO_DRIVER!.username}`);
    await act(async () => host.querySelector<HTMLButtonElement>("button[type=submit]")!.click());
    expect(onLogin).toHaveBeenCalledWith(expect.objectContaining({ username: DEMO_DRIVER!.username }));
  });

  it("the Dashboard's login is filled in too, and says where it leads", () => {
    // 13/10: the demo driver on every login page, whichever way it was reached.
    act(() => root.render(<Login onLogin={() => undefined} />));
    expect(fields()).toEqual([DEMO_DRIVER!.username, DEMO_DRIVER!.password]);
    expect(host.textContent).toContain("là vào trang của tài xế");
  });
});
