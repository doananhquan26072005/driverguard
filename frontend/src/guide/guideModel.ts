// The guide for a new user (M102): which screens of the product can come up, what each one means and
// what to do. Every screen is one scenario of #/hud-preview (hud/HudPreview.tsx SCENARIOS), so the guide
// draws the real HUD and cannot drift from it; guideModel.test.ts checks every key exists. Pure data
// and hash helpers. The text is for a driver: what you see, then what to do, in that order.
import { NAV, PAGE_LEAD, type PageKey } from "../dashboard/nav";
import { ROLES } from "../lib/labels";
import type { Role } from "../lib/types";

/** Colour of the step's dot: the HUD's own status hues (index.css), never used for anything else. */
export type GuideTone = "safe" | "caution" | "warning" | "danger" | "system" | "plain";

export interface GuideStep {
  key: string; // #/guide/<key>
  scenario: string; // key of a SCENARIOS entry of hud/HudPreview.tsx
  tone: GuideTone;
  title: string;
  means: string; // what the screen is telling you
  todo: string; // what you should do
}

export interface GuideChapter {
  title: string;
  lead: string;
  steps: GuideStep[];
}

export const GUIDE: GuideChapter[] = [
  {
    title: "Bắt đầu ca lái",
    lead: "Việc cần làm một lần ở đầu mỗi ca, khi xe còn đang dừng.",
    steps: [
      {
        key: "consent",
        scenario: "en0",
        tone: "plain",
        title: "Hệ thống xin làm quen khuôn mặt",
        means:
          "Hệ thống cần khoảng 10 giây để biết mắt, miệng và tư thế đầu của bạn lúc bình thường. Không chụp, không lưu ảnh: chỉ ghi nhớ vài con số và xoá khi kết thúc ca lái.",
        todo: "Chạm “Đồng ý, bắt đầu”. Chọn “Để sau” thì vẫn lái được, nhưng cảnh báo có thể kém chính xác hơn.",
      },
      {
        key: "enroll",
        scenario: "en1",
        tone: "plain",
        title: "Làm quen khuôn mặt: ba bước",
        means: "Ba bước nối tiếp nhau: nhìn thẳng vào camera, nhìn ra đường phía trước, rồi nhắm mắt. Mỗi bước đều được đọc to, bạn không cần nhìn màn hình.",
        todo: "Làm theo lời đọc. Ở bước nhắm mắt, mở mắt khi nghe tiếng bíp.",
      },
      {
        key: "enroll-hint",
        scenario: "en2",
        tone: "plain",
        title: "Một bước chưa đạt",
        means: "Màn hình nói rõ cần chỉnh gì, ví dụ “Giữ đầu yên”. Bước đó được làm lại, các bước đã xong không mất.",
        todo: "Chỉnh theo lời nhắc rồi giữ yên vài giây.",
      },
      {
        key: "not-enrolled",
        scenario: "enw",
        tone: "caution",
        title: "Xe đã chạy mà chưa làm quen",
        means: "Dòng nhắc nằm ở cuối màn hình. Hệ thống vẫn theo dõi và vẫn cảnh báo, chỉ là chưa biết nét riêng của khuôn mặt bạn nên có thể kém chính xác hơn.",
        todo: "Cứ lái bình thường. Lần dừng xe sau hệ thống sẽ hỏi lại.",
      },
      {
        key: "sound",
        scenario: "mute",
        tone: "caution",
        title: "Âm thanh cảnh báo chưa bật",
        means: "Dải màu vàng ở trên cùng báo rằng thiết bị chưa được phép phát tiếng. Lúc này cảnh báo chỉ hiện trên màn hình, không có còi và lời nói.",
        todo: "Chạm vào màn hình một lần trước khi cho xe chạy.",
      },
    ],
  },
  {
    title: "Bốn mức khi đang lái",
    lead: "Mỗi mức một màu. Màu càng nóng thì càng cần làm ngay.",
    steps: [
      {
        key: "normal",
        scenario: "l0",
        tone: "safe",
        title: "Bình thường (xanh)",
        means: "Hệ thống đang theo dõi và không thấy dấu hiệu buồn ngủ hay mất tập trung. Bên phải là tốc độ, bên dưới là độ mệt từng phút của 15 phút gần nhất.",
        todo: "Không cần làm gì. Bạn không phải nhìn màn hình khi lái: khi có chuyện, hệ thống sẽ báo bằng tiếng.",
      },
      {
        key: "drowsy",
        scenario: "l1",
        tone: "caution",
        title: "Chú ý: có dấu hiệu buồn ngủ (vàng)",
        means: "Hệ thống thấy nhiều dấu hiệu buồn ngủ cộng lại, như mắt nhắm lâu, ngáp, gục đầu. Đây là lời nhắc sớm, chưa phải báo động.",
        todo: "Tìm chỗ dừng nghỉ. Nếu bạn thấy mình hoàn toàn tỉnh táo, chạm “Cảnh báo nhầm?” để hệ thống ghi nhận.",
      },
      {
        key: "trend",
        scenario: "l1t",
        tone: "caution",
        title: "Chú ý: mệt tăng dần (vàng)",
        means: "Chưa có dấu hiệu rõ ở lúc này, nhưng mức mệt của bạn đang tăng đều trong ca lái.",
        todo: "Xong cuốc này nên nghỉ một lúc trước khi nhận cuốc tiếp.",
      },
      {
        key: "off-road",
        scenario: "l2o",
        tone: "warning",
        title: "Cảnh báo: rời mắt khỏi đường (cam)",
        means: "Bạn nhìn đi chỗ khác quá lâu khi xe đang chạy. Có tiếng báo kèm lời nói.",
        todo: "Nhìn lại đường ngay. Nếu bạn vẫn đang nhìn đường, chạm “Cảnh báo nhầm?”.",
      },
      {
        key: "phone",
        scenario: "l2p",
        tone: "warning",
        title: "Cảnh báo: dùng điện thoại (cam)",
        means: "Camera thấy điện thoại ở gần mặt bạn trong lúc xe đang chạy.",
        todo: "Bỏ điện thoại xuống. Cần nghe máy hay xem bản đồ thì tấp vào lề rồi mới dùng.",
      },
      {
        key: "microsleep",
        scenario: "l3",
        tone: "danger",
        title: "Nguy hiểm: nhắm mắt kéo dài (đỏ)",
        means: "Mắt bạn đã nhắm lâu hơn một cái chớp mắt: có thể bạn vừa ngủ gật. Cả màn hình chuyển đỏ, còi kêu và kêu lại khi mắt bạn còn nhắm.",
        todo: "Mở mắt, giảm tốc và dừng xe nghỉ ngay ở chỗ an toàn. Đừng cố lái tiếp.",
      },
      {
        key: "unresponsive",
        scenario: "l3u",
        tone: "danger",
        title: "Nguy hiểm: không phản ứng với còi (đỏ)",
        means: "Còi đã kêu mà mắt bạn vẫn nhắm.",
        todo: "Tấp vào lề và dừng xe ngay.",
      },
    ],
  },
  {
    title: "Khi camera không thấy rõ bạn",
    lead: "Hệ thống nói thật là nó đang không theo dõi được, thay vì im lặng.",
    steps: [
      {
        key: "no-face",
        scenario: "off",
        tone: "caution",
        title: "Tạm ngưng theo dõi: không thấy mặt",
        means: "Camera không thấy khuôn mặt bạn nên lúc này không có cảnh báo buồn ngủ hay mất tập trung nào. Lần này không tính là một cảnh báo.",
        todo: "Ngồi đúng vị trí lái, đừng che camera. Hệ thống tự theo dõi lại khi thấy mặt bạn.",
      },
      {
        key: "blocked",
        scenario: "offc",
        tone: "caution",
        title: "Tạm ngưng theo dõi: camera bị che",
        means: "Ống kính bị che hoặc hình quá tối. Màn hình ghi rõ lý do; mặt quá tối hay ảnh mờ cũng hiện tương tự.",
        todo: "Khi dừng xe, kiểm tra và lau ống kính camera. Đừng chỉnh camera lúc xe đang chạy.",
      },
      {
        key: "glare",
        scenario: "offg",
        tone: "caution",
        title: "Tạm ngưng theo dõi: mặt bị chói",
        means: "Nắng chiếu thẳng vào mặt nên camera không thấy rõ mắt bạn.",
        todo: "Hạ tấm che nắng. Nếu vẫn chói, chỉnh lại camera khi dừng xe.",
      },
      {
        key: "presence",
        scenario: "ask",
        tone: "caution",
        title: "“Bạn vẫn ổn chứ?”",
        means: "Xe đang chạy mà camera không thấy bạn một lúc lâu, nên hệ thống hỏi thẳng. Cả màn hình là một nút bấm, có đồng hồ đếm ngược.",
        todo: "Chạm vào bất kỳ đâu trên màn hình nếu bạn vẫn ổn.",
      },
      {
        key: "no-answer",
        scenario: "ask2",
        tone: "danger",
        title: "Bạn chưa trả lời câu hỏi",
        means: "Hết giờ mà không ai chạm vào màn hình, nên hệ thống đã báo cho quản lý đội xe.",
        todo: "Chạm vào màn hình nếu bạn vẫn ổn. Quản lý có thể sẽ gọi cho bạn.",
      },
    ],
  },
  {
    title: "Khi thiết bị gặp trục trặc",
    lead: "Hệ thống báo rõ khi nó không theo dõi được bạn, và tự thử lại.",
    steps: [
      {
        key: "camera-lost",
        scenario: "cam",
        tone: "caution",
        title: "Mất hình camera",
        means: "Thiết bị không nhận được hình từ camera và đang tự kết nối lại. Trong lúc đó bạn không được theo dõi.",
        todo: "Lái cẩn thận như khi không có hệ thống. Nếu kéo dài, kiểm tra dây và ống kính camera khi dừng xe.",
      },
      {
        key: "error",
        scenario: "err",
        tone: "caution",
        title: "Hệ thống gặp lỗi",
        means: "Phần xử lý trong thiết bị bị lỗi và đang tự thử lại. Trong lúc đó bạn không được theo dõi.",
        todo: "Lái cẩn thận như khi không có hệ thống. Nếu lỗi kéo dài, tìm chỗ dừng xe an toàn.",
      },
      {
        key: "link-down",
        scenario: "down",
        tone: "system",
        title: "Mất kết nối với thiết bị",
        means: "Màn hình không còn nhận được tín hiệu từ thiết bị, nên không thể cảnh báo. Riêng màn hình này có màu xanh dương: lỗi của thiết bị, không phải của bạn.",
        todo: "Khi dừng xe, kiểm tra nguồn và cáp của thiết bị.",
      },
      {
        key: "slow",
        scenario: "slow",
        tone: "caution",
        title: "Máy chậm",
        means: "Ô màu vàng ở thanh trên cùng báo thiết bị đang xử lý chậm. Hệ thống vẫn theo dõi, nhưng cảnh báo có thể đến trễ.",
        todo: "Vẫn lái được. Nếu ô này hiện mãi, báo cho quản lý đội xe.",
      },
      {
        key: "no-phone-detector",
        scenario: "nophone",
        tone: "caution",
        title: "Tạm chưa nhận biết được điện thoại",
        means: "Riêng phần nhận biết điện thoại đang nghỉ. Cảnh báo buồn ngủ và rời mắt khỏi đường vẫn hoạt động.",
        todo: "Không cần làm gì, phần này tự chạy lại.",
      },
      {
        key: "speed-lost",
        scenario: "lost",
        tone: "caution",
        title: "Mất tín hiệu tốc độ xe",
        means: "Thiết bị không đọc được tốc độ. Để an toàn, hệ thống tiếp tục theo dõi như thể xe đang chạy.",
        todo: "Vẫn lái được. Khi dừng xe, kiểm tra kết nối tốc độ xe của thiết bị.",
      },
    ],
  },
  {
    title: "Kết thúc ca lái",
    lead: "Chạm “Kết thúc ca lái” ở góc dưới màn hình khi bạn nghỉ hẳn.",
    steps: [
      {
        key: "summary",
        scenario: "trip",
        tone: "plain",
        title: "Bản tổng kết ca lái",
        means: "Ca vừa rồi dài bao lâu, nghỉ mấy lần, được nhắc mấy lần, độ mệt thay đổi thế nào, kèm gợi ý cho lần sau. Bản này được gửi cho quản lý đội xe, chỉ gồm con số, không có hình.",
        todo: "Đọc qua rồi chạm “Xong”. Bạn xem lại được ở trang “Ca lái của tôi” sau khi đăng nhập.",
      },
    ],
  },
];

export const GUIDE_STEPS: GuideStep[] = GUIDE.flatMap((c) => c.steps);

/** Where a step sits: its chapter and its number among all the steps (from 0). */
export function locate(key: string): { chapter: GuideChapter; index: number } {
  const index = Math.max(
    0,
    GUIDE_STEPS.findIndex((s) => s.key === key),
  );
  const chapter = GUIDE.find((c) => c.steps.includes(GUIDE_STEPS[index])) ?? GUIDE[0];
  return { chapter, index };
}

/** The step of `#/guide/<key>`, or the first step for anything else. */
export function stepFromHash(hash: string): GuideStep {
  const key = /^#\/guide\/([a-z0-9-]+)/.exec(hash)?.[1];
  return GUIDE_STEPS.find((s) => s.key === key) ?? GUIDE_STEPS[0];
}

export const guideHref = (key?: string) => (key ? `#/guide/${key}` : "#/guide");

/** The guide's three places: the welcome (`#/guide`), one screen (`#/guide/<step>`), the web pages (`#/guide/web`). */
export type GuideView = "intro" | "step" | "web";
export const WEB_KEY = "web"; // never a step key (guideModel.test.ts)

export function viewFromHash(hash: string): GuideView {
  const key = /^#\/guide\/([a-z0-9-]+)/.exec(hash)?.[1];
  if (key === WEB_KEY) return "web";
  return GUIDE_STEPS.some((s) => s.key === key) ? "step" : "intro";
}

/** The web pages each role gets after login: the menu of nav.ts with the line under each page's title. */
export interface RolePages {
  role: Role;
  name: string;
  intro: string;
  pages: { page: PageKey; label: string; lead: string }[];
}

const ROLE_INTRO: Record<Role, string> = {
  driver: "Chỉ thấy dữ liệu của chính mình.",
  manager: "Thấy cả đội xe, không sửa được ngưỡng cảnh báo.",
  engineer: "Xem và chỉnh ngưỡng cảnh báo, theo dõi tỉ lệ báo nhầm.",
  admin: "Tạo tài khoản, đăng ký thiết bị, xử lý yêu cầu xoá dữ liệu.",
};

export const ROLE_PAGES: RolePages[] = (["driver", "manager", "engineer", "admin"] as const).map((role) => ({
  role,
  name: ROLES[role],
  intro: ROLE_INTRO[role],
  pages: NAV[role].flatMap((s) => s.items).map((i) => ({ page: i.page, label: i.label, lead: PAGE_LEAD[i.page] ?? "" })),
}));
