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
    expect(host.querySelector('[role="note"]')).toBeNull(); // no note about it (13/10): the fields say it
    await act(async () => host.querySelector<HTMLButtonElement>("button[type=submit]")!.click());
    expect(onLogin).toHaveBeenCalledWith(expect.objectContaining({ username: DEMO_DRIVER!.username }));
  });

  it("a press on the username field lists the demo accounts; picking the engineer fills both fields", () => {
    act(() => root.render(<Login onLogin={() => undefined} live={live} />));
    const user = host.querySelector<HTMLInputElement>("input[autocomplete=username]")!;
    expect(host.querySelector('[role="listbox"]')).toBeNull(); // closed until the field is pressed
    act(() => user.focus());
    const options = [...host.querySelectorAll('[role="option"]')];
    expect(options.map((o) => o.textContent)).toEqual(["taixe_demoTài xế", "kysu_demoKỹ sư"]);
    act(() => options[1].dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true })));
    expect(fields()).toEqual(["kysu_demo", "kysu12345"]);
    expect(host.querySelector('[role="listbox"]')).toBeNull();
  });

  it("the Dashboard's login is filled in too", () => {
    // 13/10: the demo driver on every login page, whichever way it was reached.
    act(() => root.render(<Login onLogin={() => undefined} />));
    expect(fields()).toEqual([DEMO_DRIVER!.username, DEMO_DRIVER!.password]);
  });
});
