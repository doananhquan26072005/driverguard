// @vitest-environment jsdom
// #/privacy mounted for real (M106): the two retention periods are the server's (/api/v1/policy), the
// defaults of labels.ts when there is no backend, and the page states the rule the product is built on.
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RETENTION_DAYS } from "../lib/labels";
import PrivacyScreen from "./PrivacyScreen";

const api = vi.hoisted(() => ({ getPolicy: vi.fn() }));
vi.mock("../lib/api", () => ({ getPolicy: api.getPolicy }));

let host: HTMLDivElement;
let root: Root;
const kept = (what: string) => host.querySelector(`[data-keep="${what}"]`)?.textContent;
const mount = async () => {
  await act(async () => root.render(<PrivacyScreen />));
};

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  host = document.body.appendChild(document.createElement("div"));
  root = createRoot(host);
});
afterEach(() => {
  act(() => root.unmount());
  host.remove();
  vi.clearAllMocks();
});

describe("#/privacy", () => {
  it("shows the retention periods the server is set to", async () => {
    api.getPolicy.mockResolvedValue({ retention_events_days: 30, retention_summaries_days: 0 });
    await mount();
    expect(kept("events")).toBe("30 ngày");
    expect(kept("summaries")).toBe("tới khi quản trị viên xoá"); // 0 = never deleted automatically
  });

  it("with no backend, shows the defaults the consent screen states", async () => {
    api.getPolicy.mockRejectedValue(new Error("offline"));
    await mount();
    expect(kept("events")).toBe(`${RETENTION_DAYS.events} ngày`);
    expect(kept("summaries")).toBe(`${RETENTION_DAYS.summaries} ngày`);
  });

  it("says that no face image leaves the device, and leads back to the first page and to the guide", async () => {
    api.getPolicy.mockResolvedValue({ retention_events_days: 60, retention_summaries_days: 365 });
    await mount();
    expect(host.querySelector("h1")?.textContent).toBe("Quyền riêng tư");
    expect(host.textContent).toContain("Không ảnh hay video nào được lưu hoặc gửi đi");
    const links = [...host.querySelectorAll("a")].map((a) => a.getAttribute("href"));
    expect(links).toEqual(expect.arrayContaining(["#/live", "#/guide"]));
  });
});
