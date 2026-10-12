// @vitest-environment jsdom
// #/guide mounted for real (M102): the address picks the place (welcome, a step, the web pages), the tabs,
// the dots and "Tiếp" / "Trước" move without adding to
// the history, and the screen shown is a picture (inert). HudView only draws, so it is replaced by a
// record of the snapshot it was given.
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { HudSnapshot } from "../lib/types";
import GuideScreen from "./GuideScreen";
import { GUIDE, GUIDE_STEPS, ROLE_PAGES } from "./guideModel";

const view = vi.hoisted(() => ({ snap: null as unknown }));
vi.mock("../hud/HudView", () => ({ default: (props: { snap: unknown }) => ((view.snap = props.snap), null) }));
vi.mock("../hud/TripSummaryView", () => ({ default: () => null }));

let host: HTMLDivElement;
let root: Root;
const button = (name: string) => [...host.querySelectorAll("button")].find((b) => b.textContent?.trim() === name)!;
const tabs = () => [...host.querySelectorAll<HTMLButtonElement>(".guide-tabs .guide-tab")];
const title = () => host.querySelector(".guide-explain h2")?.textContent;
const mount = (hash: string) => {
  window.location.hash = hash;
  act(() => root.render(<GuideScreen />));
};

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  // jsdom lays nothing out: give the screen's room a width, so the HUD is drawn.
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(640);
  vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(400);
  host = document.body.appendChild(document.createElement("div"));
  root = createRoot(host);
  view.snap = null;
});
afterEach(() => {
  act(() => root.unmount());
  host.remove();
  vi.restoreAllMocks();
});

describe("#/guide", () => {
  it("opens on the welcome; Bắt đầu opens the first step, with the dots of its chapter", () => {
    mount("#/guide");
    expect(host.querySelector(".guide-screen")).toBeNull();
    expect(tabs()).toHaveLength(GUIDE.length + 2);
    act(() => button("Bắt đầu").click());
    expect(window.location.hash).toBe(`#/guide/${GUIDE_STEPS[0].key}`);
    expect(title()).toBe(GUIDE_STEPS[0].title);
    expect(host.querySelectorAll(".guide-item")).toHaveLength(GUIDE[0].steps.length);
    expect(button("Trước").disabled).toBe(true);
  });

  it("a chapter's tab opens its first step; the web tab shows one role's pages at a time", () => {
    mount("#/guide");
    act(() => tabs()[2].click());
    expect(title()).toBe(GUIDE[1].steps[0].title);
    expect(tabs()[2].getAttribute("aria-current")).toBe("page");
    act(() => tabs().at(-1)!.click());
    expect(window.location.hash).toBe("#/guide/web");
    expect(host.querySelectorAll(".guide-role dt")).toHaveLength(ROLE_PAGES[0].pages.length);
    act(() => (host.querySelectorAll("[role=tab]")[3] as HTMLButtonElement).click());
    expect(host.querySelectorAll(".guide-role dt")).toHaveLength(ROLE_PAGES[3].pages.length);
  });

  it("#/guide/<step> opens that step and draws its screen from the preview's numbers", () => {
    mount("#/guide/microsleep");
    expect(title()).toBe("Nguy hiểm: nhắm mắt kéo dài (đỏ)");
    expect(host.querySelector(".guide-screen")?.getAttribute("data-scenario")).toBe("l3");
    expect((view.snap as HudSnapshot).level).toBe(3);
  });

  it("the screen is a picture: inert, described by its label", () => {
    mount("#/guide/drowsy");
    const screen = host.querySelector(".guide-screen")!;
    expect(screen.getAttribute("role")).toBe("img");
    expect(screen.getAttribute("aria-label")).toContain("buồn ngủ");
    expect(screen.firstElementChild?.hasAttribute("inert")).toBe(true);
  });

  it("Tiếp, Trước and the list move between steps and replace the address", () => {
    mount("#/guide/normal");
    const entries = window.history.length;
    act(() => button("Tiếp").click());
    expect(title()).toBe("Chú ý: có dấu hiệu buồn ngủ (vàng)");
    expect(window.location.hash).toBe("#/guide/drowsy");
    act(() => button("Trước").click());
    expect(window.location.hash).toBe("#/guide/normal");
    const last = GUIDE_STEPS[GUIDE_STEPS.length - 1];
    act(() => ([...host.querySelectorAll(".guide-item")].at(-1) as HTMLButtonElement).click());
    expect(title()).toBe(GUIDE[1].steps.at(-1)!.title);
    act(() => tabs()[GUIDE.length].click());
    act(() => ([...host.querySelectorAll(".guide-item")].at(-1) as HTMLButtonElement).click());
    expect(title()).toBe(last.title);
    expect(button("Tiếp").disabled).toBe(true);
    expect(window.history.length).toBe(entries);
  });

  it("the arrow keys do the same", () => {
    mount("#/guide/normal");
    act(() => void window.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight" })));
    expect(window.location.hash).toBe("#/guide/drowsy");
    act(() => void window.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft" })));
    expect(window.location.hash).toBe("#/guide/normal");
  });
});
