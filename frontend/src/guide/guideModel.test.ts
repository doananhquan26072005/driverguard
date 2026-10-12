// The guide (M102) draws the screens of #/hud-preview: a step whose scenario is gone would silently show
// the calm screen under an alert's explanation. Checked here, with the hash helpers and the role pages.
import { describe, expect, it } from "vitest";
import { NAV } from "../dashboard/nav";
import { SCENARIOS } from "../hud/HudPreview";
import { GUIDE, GUIDE_STEPS, guideHref, locate, ROLE_PAGES, stepFromHash, viewFromHash, WEB_KEY } from "./guideModel";

describe("guide steps", () => {
  it("every step shows a scenario that exists", () => {
    const known = new Set(SCENARIOS.map((s) => s.key));
    expect(GUIDE_STEPS.filter((s) => !known.has(s.scenario)).map((s) => s.key)).toEqual([]);
  });

  it("step keys and scenarios are used once, and every step says what it means and what to do", () => {
    expect(new Set(GUIDE_STEPS.map((s) => s.key)).size).toBe(GUIDE_STEPS.length);
    expect(new Set(GUIDE_STEPS.map((s) => s.scenario)).size).toBe(GUIDE_STEPS.length);
    for (const s of GUIDE_STEPS) {
      expect(s.key, s.key).toMatch(/^[a-z0-9-]+$/);
      expect(s.title.length && s.means.length && s.todo.length, s.key).toBeGreaterThan(0);
    }
  });

  it("covers the four levels, a not-monitored screen, a device fault and the trip summary", () => {
    const shown = GUIDE_STEPS.map((s) => s.scenario);
    for (const key of ["l0", "l1", "l2o", "l3", "off", "cam", "down", "trip"]) expect(shown, key).toContain(key);
  });

  it("the dot of a level screen is that level's colour", () => {
    const tone = { 1: "caution", 2: "warning", 3: "danger" } as const;
    for (const step of GUIDE_STEPS) {
      const level = SCENARIOS.find((s) => s.key === step.scenario)?.level;
      if (level) expect(step.tone, step.key).toBe(tone[level]);
    }
  });
});

describe("guide address", () => {
  it("#/guide/<key> opens that step; anything else opens the first", () => {
    expect(stepFromHash("#/guide/phone").scenario).toBe("l2p");
    expect(stepFromHash(guideHref("summary")).key).toBe("summary");
    expect(stepFromHash("#/guide").key).toBe(GUIDE_STEPS[0].key);
    expect(stepFromHash("#/guide/no-such-step").key).toBe(GUIDE_STEPS[0].key);
    expect(stepFromHash("#/dashboard").key).toBe(GUIDE_STEPS[0].key);
  });

  it("the address says which place is open: the welcome, a step or the web pages", () => {
    expect(GUIDE_STEPS.map((s) => s.key)).not.toContain(WEB_KEY);
    expect(viewFromHash("#/guide")).toBe("intro");
    expect(viewFromHash("#/guide/no-such-step")).toBe("intro");
    expect(viewFromHash(guideHref("phone"))).toBe("step");
    expect(viewFromHash(guideHref(WEB_KEY))).toBe("web");
  });

  it("locate gives the chapter and the running number", () => {
    const last = GUIDE_STEPS[GUIDE_STEPS.length - 1];
    expect(locate(last.key)).toEqual({ chapter: GUIDE[GUIDE.length - 1], index: GUIDE_STEPS.length - 1 });
    expect(locate("no-such-step").index).toBe(0);
  });
});

describe("web pages per role", () => {
  it("lists exactly the menu of each role, each page with its line", () => {
    for (const r of ROLE_PAGES) {
      expect(r.pages.map((p) => p.page), r.role).toEqual(NAV[r.role].flatMap((s) => s.items.map((i) => i.page)));
      for (const p of r.pages) expect(p.lead.length, `${r.role} ${p.page}`).toBeGreaterThan(0);
    }
    expect(ROLE_PAGES.map((r) => r.role).sort()).toEqual(Object.keys(NAV).sort());
  });
});
