// Whether this browser can speak Vietnamese (chime.ts picks the voice): the enrollment and #/live setup
// screens say so, and how to install one, instead of letting an English voice read Vietnamese.
import { useEffect, useState } from "react";
import { hasVietnameseVoice, NO_VIETNAMESE_VOICE_TEXT, onVoices } from "./chime";

export { NO_VIETNAMESE_VOICE_TEXT };

/** null until the browser has listed its voices, then true / false. */
export function useVietnameseVoice(): boolean | null {
  const [has, setHas] = useState(hasVietnameseVoice);
  useEffect(() => {
    const off = onVoices(() => setHas(hasVietnameseVoice()));
    // Ask again for a few seconds: some browsers fill the list without telling anyone.
    let tries = 0;
    const id = setInterval(() => {
      const now = hasVietnameseVoice();
      setHas(now);
      if (now !== null || ++tries > 20) clearInterval(id);
    }, 250);
    return () => {
      off();
      clearInterval(id);
    };
  }, []);
  return has;
}
