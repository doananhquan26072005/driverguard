import { describe, expect, it } from "vitest";
import { HOME, NAV, pageFromHash, pageHref, pageLabel, pagesOf } from "./nav";

describe("M60 pages per role", () => {
  it("lands each role on its own home page", () => {
    expect(pageFromHash("#/dashboard", "driver")).toBe("overview");
    expect(pageFromHash("", "manager")).toBe("overview");
    expect(pageFromHash("#/dashboard", "engineer")).toBe("thresholds");
    expect(pageFromHash("#/dashboard", "admin")).toBe("accounts");
    for (const role of ["driver", "manager", "engineer", "admin"] as const) expect(pagesOf(role)).toContain(HOME[role]);
  });

  it("opens a linked page, but never one the role does not have", () => {
    expect(pageFromHash("#/dashboard/fleet", "manager")).toBe("fleet");
    expect(pageFromHash("#/dashboard/accounts", "driver")).toBe("overview"); // not a driver page
    expect(pageFromHash("#/dashboard/thresholds", "driver")).toBe("overview");
    expect(pageFromHash("#/dashboard/nonsense", "engineer")).toBe("thresholds");
  });

  it("shows a driver only their own pages, and an admin everything an engineer has", () => {
    expect(pagesOf("driver")).toEqual(["overview", "trips", "alerts", "mydata"]);
    expect(pagesOf("admin")).toEqual(expect.arrayContaining(pagesOf("engineer")));
    expect(NAV.admin.map((s) => s.title)).toEqual(["Quản trị", "Vận hành"]);
    expect(pageLabel("manager", "thresholds")).toBe("Ngưỡng (chỉ xem)");
    expect(pageHref("fleet")).toBe("#/dashboard/fleet");
  });
});
