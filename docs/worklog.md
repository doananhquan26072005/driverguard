# Worklog — DriverGuard

> Ai làm gì, ngày nào, kết quả gì. Bảng 1 tóm tắt theo ngày; bảng 2 là lịch sử commit lấy từ `git log`.
> Ghi chép chi tiết từng ngày (số đo, lệnh chạy lại, việc còn mở) nằm ở [worklog/](worklog/); quyết định và bài học
> ở [JOURNAL.md](JOURNAL.md); trạng thái từng mốc ở [roadmap.md](roadmap.md).

Thành viên theo tên trên GitHub: `kelsingo`, `Yuhnguyn` (PRD), `hddung-vinai` (nhánh `dungx`), `DAQuan` (nhánh `DAQuan`,
hai tài khoản `DAQuan-VinAI` / `DQQuan-VinAI`).

## 1. Theo ngày

| Ngày | Ai | Việc chính | Kết quả | PR | Chi tiết |
|---|---|---|---|---|---|
| 23/09 | kelsingo, Yuhnguyn | PRD gate 1, sơ đồ Use Case và User Flow | `docs/PRD.md` v2.2 | | |
| 24/09 | hddung-vinai | M0–M7: 14 khối, backend FastAPI, HUD và dashboard React, công cụ đánh giá | Pipeline chạy đủ từ camera tới metadata | #1 | |
| 24/09 | DAQuan | Review M0–M7, sửa an toàn M2–M4, đánh giá trên dataset Kaggle | YawDD 319 clip: microsleep sai 122 → 34; 329 test pass | #2 (mở) | [24/09](worklog/2026-09-24-DAQuan.md) |
| 25/09 | DAQuan | Cấu hình an toàn, giảm báo sai, kết nối lại camera, HUD mới | Báo sai YawDD 23 → 9; 365 test Python | #2 | [25/09](worklog/2026-09-25-DAQuan.md) |
| 26/09 | DAQuan | Đánh giá FL3D và SUST-DDD, sửa hai lỗi ở khối 5 | Microsleep ≥ 1,5 s đạt L3: 17,9% → 78,9% | #3 | [26/09](worklog/2026-09-26-DAQuan.md) |
| 28–29/09 | DAQuan | Deploy Railway v1 / v1.1, gói cài edge, M8 chạy trong trình duyệt (`#/live`) | 30 FPS trên Chrome; 434 test Python | #4–#8 | [28–29/09](worklog/2026-09-28-DAQuan.md) |
| 30/09 | DAQuan | Danh sách cải tiến theo ưu tiên, sơ đồ kiến trúc | `docs/improvements.md`, `docs/architecture_diagram.md` | #9, #10 | |
| 01/10 | DAQuan | v2: đăng ký tài xế, `unavailable` khi mất mặt, tổng kết chuyến, cách đo báo sai (M9–M20) | 519 test Python, 38 test frontend; v2.0 lên Railway | | [01/10](worklog/2026-10-01-DAQuan.md) |
| 02/10 | DAQuan | M21–M31: lớp runtime chung, test e2e, FMEA, âm thanh, mất tín hiệu xe, `#/drive` | 554 test Python, 2 test e2e; v2.1 | #11–#13 | [02/10](worklog/2026-10-02-DAQuan.md) |
| 03–04/10 | DAQuan | README theo yêu cầu khoá học, cập nhật sơ đồ tới M31 | Tài liệu khớp v2.2 | #14, #15 | |
| 05/10 | DAQuan | M32–M37: leo thang L1 lặp lại, heartbeat và tab "Đội xe", test hồi quy bằng trace, chính sách dữ liệu | 657 test Python, 56 test frontend, 3 e2e | #16 | [05/10](worklog/2026-10-05-DAQuan.md) |
| 06/10 | DAQuan | M38–M55: hiệu năng bản web, UTA-RLDD, chốt thiết bị đích VF e34 | Khối 6–14 trong Pyodide 1,97 → 0,61 ms / frame; 911 test Python | (trong #17) | [06/10](worklog/2026-10-06-DAQuan.md) |
| 07/10 | DAQuan | M56: ngưỡng riêng cho `eyeBlink`, mốc mống mắt theo tài xế | Camera xám / IR đạt L3: 0 / 48 → 46 / 48; 953 test Python | #17 | [07/10](worklog/2026-10-07-DAQuan.md) |
| 07/10 | hddung-vinai | M57–M66: giao diện Version 4 trên design system, giọng nói tiếng Việt, deploy tự động | HUD, web theo vai trò, `#/live` giao diện mới | #18 | |
| 08/10 | DAQuan | M67–M86: tốc độ `#/live`, audit 14 khối, các việc theo audit | YOLO WebGPU 94 → 17 ms; 15 phát hiện High, 0 Critical | #19, #21 | [08/10](worklog/2026-10-08-DAQuan.md) |
| 08/10 | hddung-vinai | Sửa Dockerfile Railway (M66) | Bản deploy build được | #20 | |
| 09/10 | DAQuan | M87–M101: CI với model thật, bù test, quyết định 09/10, CSP, kiểm `l1` trên DROZY | 1712 test Python, vitest 293, e2e 13 / 13 | #22 | [09/10](worklog/2026-10-09-DAQuan.md) |

## 2. Lịch sử commit

135 commit trên `main` + `DAQuan` tới `217d43e` (09/10), gồm 27 commit gộp (PR #1–#22 và các lần gộp `main`) không liệt
kê dưới đây. Sinh lại bằng:

```bash
git log --reverse --no-merges --date=short --format='| %ad | %an | `%h` | %s |'
```

| Ngày | Tác giả | Commit | Nội dung |
|---|---|---|---|
| 12/09 | phoenix-mentor[bot] | `44c0274` | Initial commit |
| 23/09 | kelsingo | `12735b8` | PRD gate1 |
| 23/09 | kelsingo | `0a0f426` | PRD gate1 |
| 23/09 | Yuhnguyn | `8d3a815` | docs: PRD v2.2 + so do UML Use Case & User Flow cho DriverGuard |
| 23/09 | Yuhnguyn | `ad66a87` | docs: xoa PRD trung lap docs/gate-1/PRD.md, giu docs/PRD.md lam ban duy nhat |
| 24/09 | hddung-vinai | `abca755` | M0: frame capture and preprocessing (blocks 1, 2) |
| 24/09 | hddung-vinai | `e1a58d8` | M1: face landmarks and per-frame features (blocks 3, 6) |
| 24/09 | hddung-vinai | `6dd7f99` | M3: phone detector and distraction branch (blocks 4, 8) |
| 24/09 | hddung-vinai | `4077bd5` | M2: drowsiness branch (block 7) |
| 24/09 | hddung-vinai | `ffe579a` | M4: risk engine, CAN context, trip memory, alert manager (blocks 9-12) |
| 24/09 | hddung-vinai | `f0d48dd` | M5: metadata publisher and FastAPI backend (block 14) |
| 24/09 | hddung-vinai | `6aeea57` | M6: in-car HUD and fleet / engineer dashboard (React) |
| 24/09 | hddung-vinai | `7fd0eac` | M2: add block 5, eye-state CNN (used when EAR is not reliable) |
| 24/09 | hddung-vinai | `d6628f1` | M7: accuracy evaluation and speed benchmark tools |
| 24/09 | hddung-vinai | `0293433` | Docs: HowToUse.md user guide and roadmap status (M2 + block 5, M7) |
| 24/09 | DAQuan | `ca2cf6b` | M2-M4 safety fixes, M7 Kaggle dataset evaluation, CI / requirements cleanup |
| 24/09 | DAQuan | `6fb8f28` | docs: worklog DAQuan - timeline, push and PR #2 |
| 24/09 | DAQuan | `70bdf67` | docs: worklog DAQuan - four improvement areas, false-positive results on 319 YawDD clips |
| 25/09 | DAQuan | `659b6bb` | Address PR #2 review: head drop after yawn/talking reaches L3, no re-alert on flickering reasons |
| 25/09 | DAQuan | `67e9a4e` | Config safety, fewer false alarms, camera reconnect, no hardcoded thresholds |
| 25/09 | DAQuan | `cceb3a3` | docs: worklog 25/09, roadmap, HowToUse, re-run YawDD evaluation |
| 25/09 | DAQuan | `faf05cb` | docs: worklog 25/09 - full test run results |
| 25/09 | DAQuan | `77513aa` | Fewer false alarms: per-frame PERCLOS, standing still and rests, no EAR/CNN flicker |
| 25/09 | DAQuan | `74e400a` | Phone detector: no busy-wait, warn when results arrive too late |
| 25/09 | DAQuan | `8d4b912` | HUD: a different sound per kind of alert, L3 siren repeats while eyes stay closed |
| 25/09 | DAQuan | `c3b304b` | HUD redesign: glanceable in 0.5 s, less on screen as the level rises |
| 25/09 | DAQuan | `26b64c6` | Faster preprocessing (CLAHE on YCrCb), hold the eye CNN only when it is dark / IR |
| 25/09 | DAQuan | `b76b928` | docs: worklog 25/09 section 8 (review, false alarms, speed, HUD sounds), YawDD and FPS re-run |
| 26/09 | DAQuan | `7228e6c` | M7: evaluate on FL3D (NITYMED videos) and SUST-DDD with tools/seq_eval.py |
| 26/09 | DAQuan | `6438c4d` | Fix eye-state triggers and catch more microsleeps without more false alarms |
| 26/09 | DAQuan | `8f76190` | docs: worklog 26/09 section 8.5 (commits, PR #3) |
| 28/09 | DAQuan | `b9a9753` | docs: fill evaluation report with measured metrics |
| 29/09 | DAQuan | `066efd6` | Edge agent: --hud-origin for a hosted HUD, one-command install package |
| 29/09 | DAQuan | `1e3cb11` | M8: DriverGuard in the browser (#/live) on the visitor's own camera |
| 29/09 | DAQuan | `a0c325c` | Deploy on Railway: one small image for backend, dashboard and #/live |
| 29/09 | DAQuan | `d26fa72` | docs: worklog 28-29/09 (Railway deploy, edge package, M8 in-browser agent, PR #5) |
| 29/09 | DAQuan | `b525983` | fix(ai-log): read .env without python-dotenv so pre-push really submits |
| 29/09 | DAQuan | `b60b766` | docs: DriveGuard version 1 release notes (features, usage, what is included, limits) |
| 29/09 | DAQuan | `9a9e6c7` | docs: improvements list (lighting, multi-face, eye-state models, gaze, metrics, video DMS ideas) |
| 30/09 | DAQuan | `09c88ea` | docs(improvements): priority order, evaluation datasets section |
| 30/09 | DAQuan | `e2fbc9c` | docs(architecture): DriverGuard diagrams replace the course template |
| 30/09 | DAQuan | `9a51396` | docs(improvements): task table by priority, driver enrollment, APK/UI, hardware, UTA tuning |
| 01/10 | DAQuan | `679a44a` | feat(edge): v2 driver enrollment, FR-6 unavailable, new drowsiness signals, trip summary, manual vehicle |
| 01/10 | DAQuan | `89d3a13` | feat(backend): trip reports with review, v2 system reasons and metrics |
| 01/10 | DAQuan | `6bca8bf` | feat(frontend): enrollment guide, trip summary and reports tab, vehicle buttons, plain-language driver UI |
| 01/10 | DAQuan | `b55ed17` | feat(eval): false alarms per hour with exposure hours and Poisson CI, window FAR / MAR, yawdd from traces |
| 01/10 | DAQuan | `0a47d76` | docs: release v2 notes, roadmap M9-M18, improvements review, research, worklog 01/10 |
| 01/10 | DAQuan | `c80e7ce` | chore(deploy): v2.0.0 on Railway as a separate service, v1 kept running |
| 02/10 | DAQuan | `6db8181` | feat(edge): v2 M19-M28 - drive simulator, turn-signal side, shared TripRuntime, safety fixes |
| 02/10 | DAQuan | `2d158da` | feat(backend): system reasons and metrics for v2 safety events |
| 02/10 | DAQuan | `4ea5309` | feat(frontend): v2 HUD - consent screen, always-on sound, safety states, e2e tests |
| 02/10 | DAQuan | `3151560` | docs: v2 docs M19-M29 - FMEA, README / architecture / HowToUse for v2, roadmap, release notes |
| 02/10 | DAQuan | `099d910` | feat(edge): no alert at all while the vehicle stands still (M30) |
| 02/10 | DAQuan | `f6694d0` | feat: web driving controls #/drive for a #/live session (M31) |
| 02/10 | DAQuan | `942786f` | docs: M30 / M31 in roadmap, release notes, FMEA, HowToUse, README, architecture |
| 02/10 | DAQuan | `6ecc303` | fix(frontend): generate the #/drive page's Tailwind classes (M31) |
| 03/10 | DAQuan | `ee6031f` | docs: rewrite README for DriverGuard and the course requirements |
| 04/10 | DAQuan | `ab70651` | docs(architecture): bring the diagrams up to M31 and the v2.2 deploy |
| 05/10 | DAQuan | `de6ce8d` | test: replay blocks 5, 7-12 on pinned traces in CI (M34) |
| 05/10 | DAQuan | `9f5c9d5` | feat(tools): offline blink-duration prototype on FL3D traces (M35) |
| 05/10 | DAQuan | `f0dd999` | feat: repeated L1 goes out as L2, heartbeat and fleet overview, data retention (M32, M33, M37) |
| 05/10 | DAQuan | `39ee395` | docs: release v3 notes, pilot readiness criteria, roadmap M32-M37 |
| 07/10 | DAQuan | `3a228fe` | chore: extend .gitignore, pin agent skills in skills-lock.json |
| 07/10 | DAQuan | `5d8347d` | feat(edge): distraction, presence and quality signals, eyeBlink thresholds, edge profiles (M38-M56) |
| 07/10 | DAQuan | `e1aba4f` | feat(backend): versions and audit log, urgent events, threshold rollout, driver data export (M38-M48) |
| 07/10 | DAQuan | `28f2fff` | feat(frontend): audit view, my-data card, live perf timing and GPU checks (M41-M51) |
| 07/10 | DAQuan | `0d6ffe9` | feat(tools): trace recording, gaze, light and UTA-RLDD studies with their results (M46-M56) |
| 07/10 | DAQuan | `a391374` | test: cover M38-M56 edge and backend behaviour, refresh regression fixture |
| 07/10 | DAQuan | `5921a78` | docs: roadmap M38-M56, release v3 notes, DPIA and driver notice templates, worklogs |
| 07/10 | hddung-vinai | `a957060` | feat(frontend): dark redesign tokens, self-hosted Inter, glass cards (M57) |
| 07/10 | hddung-vinai | `5e153d7` | feat(edge): HUD state carries trip, alert detail and incident from the agent (M65) |
| 07/10 | hddung-vinai | `07569e3` | docs: roadmap Version 4 (M57-M65), M57 and M65 done |
| 07/10 | hddung-vinai | `1e93ffa` | feat(hud): driving screens on the DriverGuard design system (M58) |
| 07/10 | hddung-vinai | `a7ee318` | fix(hud): 1280x800 scaled stage, consent / enrollment with face guide, trip summary (M58, part of M59) |
| 07/10 | hddung-vinai | `d8ce0c9` | test(hud): stage scale (M58) |
| 07/10 | hddung-vinai | `5cc3984` | fix(hud): review 07/10 - bigger buttons, plain words for the measures, slim fatigue strip, gear letter, clear not-monitored screens |
| 07/10 | hddung-vinai | `3b60c4f` | docs: roadmap M58 status line |
| 07/10 | hddung-vinai | `c1049eb` | feat(hud): presence question on the design system (M59) |
| 07/10 | hddung-vinai | `651a5cb` | feat(web): one login, a menu and home page per role (M60) |
| 07/10 | hddung-vinai | `46ad435` | feat(web): driver overview, trips and trip detail (M61) |
| 07/10 | hddung-vinai | `f55049b` | feat(web): manager fleet overview and trip report review (M62) |
| 07/10 | hddung-vinai | `2ef8e2d` | feat(web): engineer thresholds page, admin accounts and devices (M63) |
| 07/10 | hddung-vinai | `4030ecd` | feat(live): setup, loading and self-view on the design system, #/drive restyled (M64) |
| 07/10 | hddung-vinai | `67c1f44` | test(e2e): follow the redesigned report review and drive link; 4/4 pass (M62, M64) |
| 07/10 | hddung-vinai | `068a8e7` | fix(live): speak only with a Vietnamese voice, live camera in the enrollment frame (M64) |
| 07/10 | hddung-vinai | `0336b50` | feat(hud): recorded Vietnamese voice for every alert and notice (M64) |
| 07/10 | hddung-vinai | `5df374b` | ci(deploy): deploy to Railway after CI passes on main, send the two models (M66) |
| 08/10 | DAQuan | `5201206` | feat(bench): whole-run counters, start-up timings and long runs for the #/live bench (M67) |
| 08/10 | DAQuan | `873da57` | fix(live): phone detector runs at the configured rate, and before MediaPipe (M67) |
| 08/10 | DAQuan | `749767b` | feat(live): loop starts without waiting for the phone detector; Pyodide packages load beside the runtime (M67) |
| 08/10 | DAQuan | `3168852` | feat(live): phone detector on WebGPU where the browser has a real GPU (M67) |
| 08/10 | DAQuan | `ff08068` | feat(tools): phone_study, the phone branch against YOLO schedules and input sizes on 3MDAD (M67) |
| 08/10 | DAQuan | `7afc09d` | docs: M67 results, roadmap, release notes, improvements, worklog |
| 08/10 | hddung-vinai | `16262a8` | fix(deploy): install pyyaml in the webpy stage of Dockerfile.railway (M66) |
| 08/10 | DAQuan | `20c56f2` | feat(tools): UTA-RLDD scoring rules, person-level CI, trade-off and low-FPS studies (M69, M70, M75) |
| 08/10 | DAQuan | `25bc10a` | fix(edge): frame gaps, silent states, context resets, alert reminders, droop-then-shut (M68, M71-M74, M76) |
| 08/10 | DAQuan | `5eca582` | feat(live): watchdog for a stalled loop or lost camera, HUD without one-tap ways to hide monitoring (M71, M72) |
| 08/10 | DAQuan | `76b76aa` | docs: audit of the 14 blocks (08/10), M68-M76 roadmap, release notes, improvements, worklog |
| 09/10 | DAQuan | `750321f` | feat(edge): non-finite guards, self-healing phone branch, pose baselines, metadata guard, thresholds in YAML (M77-M81, M83-M85, M89, M90) |
| 09/10 | DAQuan | `3031351` | fix(backend): server clock for current state and retention, event id conflicts, shared metadata guard (M82, M84, M90) |
| 09/10 | DAQuan | `a451d18` | feat(live): YOLO worker watchdog, frozen camera, random trip id, generated defaults, portrait layout, missing tests (M78, M82, M83, M85, M88, M89) |
| 09/10 | DAQuan | `8f61343` | chore(eval): container timestamps, pinned libraries and models, provenance, CI on DAQuan with real models and FPS check (M86, M87) |
| 09/10 | DAQuan | `4f2f93c` | docs: M77-M90 roadmap, release v4 notes, audit doc fixes, improvements, worklog |
| 09/10 | DAQuan | `8a87976` | feat(edge): per-reason reminders, context cap, time-based ratios, unknown speed, slow loop, dark colour vs infrared (M92, M93, M95, M96, M98) |
| 09/10 | DAQuan | `ff1830d` | feat(backend): session refresh during a trip, Content-Security-Policy, bundled web runtime (M97, M99) |
| 09/10 | DAQuan | `d69b69e` | feat(live): token refresh and bounded uploads, runtime served from the build, movable self view, keepalive trip end (M97, M99, M100) |
| 09/10 | DAQuan | `f697714` | chore(eval): regenerate results after M71-M93, DROZY check of risk.drowsy.l1 with a pre-declared rule (M94, M101) |
| 09/10 | DAQuan | `217d43e` | docs: M91-M101 roadmap, 09/10 decisions, release v4 notes, audit doc fixes, improvements, worklog |
