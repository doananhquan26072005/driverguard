// Face alignment frame of the enrollment steps (M58, design system "FaceFrame"): a dashed oval and face
// landmarks drawn as dots, never a picture of a face. It is a guide, not the camera picture: the HUD
// never receives an image (only numbers), and nothing is stored. Green while the step goes well,
// amber while the agent asks for something (hint). Step 2 turns the face to the road, step 3 shuts the eyes.
import type { EnrollStep } from "../lib/types";

type P = [number, number];

const JAW: P[] = [
  [212.4, 141], [217.7, 155.9], [220.9, 171.7], [222, 188], [220.9, 204.3], [217.7, 220.1], [212.4, 235], [205.2, 248.4],
  [196.3, 260], [186, 269.4], [174.6, 276.3], [162.5, 280.6], [150, 282], [137.5, 280.6], [125.4, 276.3], [114, 269.4],
  [103.7, 260], [94.8, 248.4], [87.6, 235], [82.3, 220.1], [79.1, 204.3], [78, 188], [79.1, 171.7], [82.3, 155.9], [87.6, 141],
];
const BROW_L: P[] = [[100, 146], [108, 141.8], [116, 140], [124, 141.8], [132, 146]];
const BROW_R: P[] = [[168, 146], [176, 141.8], [184, 140], [192, 141.8], [200, 146]];
const EYE_L: P[] = [[131, 166], [127.2, 169.9], [118, 171.5], [108.8, 169.9], [105, 166], [108.8, 162.1], [118, 160.5], [127.2, 162.1]];
const EYE_R: P[] = [[195, 166], [191.2, 169.9], [182, 171.5], [172.8, 169.9], [169, 166], [172.8, 162.1], [182, 160.5], [191.2, 162.1]];
const SHUT_L: P[] = [[106, 166], [112, 167.4], [118, 168], [124, 167.4], [130, 166]];
const SHUT_R: P[] = [[170, 166], [176, 167.4], [182, 168], [188, 167.4], [194, 166]];
const NOSE: P[] = [[150, 176], [150, 188], [150, 199], [141, 207], [150, 210], [159, 207]];
const MOUTH: P[] = [
  [171, 232], [167, 235.8], [156.5, 238.2], [143.5, 238.2], [133, 235.8], [129, 232], [133, 228.2], [143.5, 225.8], [156.5, 225.8], [167, 228.2],
];

// Camera-frame corners. Inline: no Tailwind preflight here, so a border class would draw all four sides.
const EDGE = "2px solid rgba(255,255,255,0.45)";
const CORNERS = [
  { key: "tl", style: { top: 16, left: 16, borderTop: EDGE, borderLeft: EDGE, borderTopLeftRadius: 8 } },
  { key: "tr", style: { top: 16, right: 16, borderTop: EDGE, borderRight: EDGE, borderTopRightRadius: 8 } },
  { key: "bl", style: { bottom: 16, left: 16, borderBottom: EDGE, borderLeft: EDGE, borderBottomLeftRadius: 8 } },
  { key: "br", style: { bottom: 16, right: 16, borderBottom: EDGE, borderRight: EDGE, borderBottomRightRadius: 8 } },
];

const BADGE: Record<EnrollStep, string> = {
  look_camera: "Mặt đã nằm trong khung",
  look_road: "Đang giữ yên · trong khung",
  close_eyes: "Mắt đang nhắm · giữ nguyên",
};

export default function FaceGuide({ step, hint }: { step: EnrollStep; hint: string | null }) {
  const dx = step === "look_road" ? -12 : 0; // the head turns to the road
  const shut = step === "close_eyes";
  const at = (pts: P[]) => pts.map(([x, y]) => `${(x + dx).toFixed(1)},${y}`).join(" ");
  const eyes = shut ? [SHUT_L, SHUT_R] : [EYE_L, EYE_R];
  const dots = [...JAW, ...BROW_L, ...BROW_R, ...(shut ? [] : [...EYE_L, ...EYE_R]), ...NOSE, ...MOUTH];
  const ok = hint == null;
  return (
    <div
      role="img"
      aria-label={`Khung căn khuôn mặt: ${hint ?? BADGE[step]}`}
      className="relative min-h-[260px] flex-1 overflow-hidden rounded-[14px] border border-solid border-white/10 bg-[radial-gradient(70%_55%_at_50%_45%,#18202b_0%,#0b0e13_70%,#07090c_100%)]"
    >
      <svg aria-hidden viewBox="0 0 300 380" preserveAspectRatio="xMidYMid meet" className="absolute inset-0 size-full">
        <defs>
          <radialGradient id="face-guide-fill" cx="50%" cy="45%" r="55%">
            <stop offset="0%" stopColor="#60a5fa" stopOpacity="0.1" />
            <stop offset="100%" stopColor="#60a5fa" stopOpacity="0" />
          </radialGradient>
        </defs>
        <ellipse cx="150" cy="182" rx="104" ry="134" fill="url(#face-guide-fill)" />
        <ellipse
          cx="150"
          cy="182"
          rx="116"
          ry="146"
          fill="none"
          stroke={ok ? "rgba(74,222,128,0.55)" : "rgba(251,191,36,0.6)"}
          strokeWidth="7"
          pathLength="400"
          strokeDasharray="1.1 3.9"
        />
        <ellipse cx="150" cy="182" rx="102" ry="132" fill="none" stroke="rgba(147,197,253,0.18)" strokeWidth="1" />
        <g stroke="rgba(147,197,253,0.28)" strokeWidth="1" fill="none">
          <polyline points={at(JAW)} />
          <polyline points={at(BROW_L)} />
          <polyline points={at(BROW_R)} />
          {shut ? eyes.map((e, i) => <polyline key={i} points={at(e)} />) : eyes.map((e, i) => <polygon key={i} points={at(e)} />)}
          <polygon points={at(MOUTH)} />
        </g>
        <g fill="#93c5fd" opacity="0.85">
          {dots.map(([x, y], i) => (
            <circle key={i} cx={x + dx} cy={y} r="1.9" />
          ))}
        </g>
      </svg>
      {CORNERS.map((c) => (
        <span key={c.key} aria-hidden className="absolute size-[26px]" style={c.style} />
      ))}
      <span className="absolute top-3.5 left-1/2 inline-flex -translate-x-1/2 items-center gap-1.5 rounded-full border border-solid border-white/8 bg-black/50 px-2.5 py-1 text-xs whitespace-nowrap text-[#d4d4d4]">
        <span aria-hidden className="size-1.5 rounded-full bg-[#f87171]" />
        Camera · chỉ xem, không lưu
      </span>
      <span
        className={`absolute bottom-4 left-1/2 inline-flex -translate-x-1/2 items-center gap-2 rounded-full border border-solid px-3.5 py-2 text-sm font-semibold whitespace-nowrap ${
          ok ? "border-hud-safe/50 bg-[rgba(13,30,20,0.88)] text-[#bbf7d0]" : "border-hud-caution/50 bg-[rgba(40,30,8,0.9)] text-[#fde68a]"
        }`}
      >
        {hint ?? BADGE[step]}
      </span>
    </div>
  );
}
