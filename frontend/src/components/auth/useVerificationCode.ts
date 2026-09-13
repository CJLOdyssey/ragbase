import { useEffect, useState } from 'react';

/**
 * 验证码发送 + 60s 倒计时。
 * 倒计时用 setTimeout 逐次调度，依赖仅 [cooldown]，无额外 deps 告警。
 */
export function useVerificationCode(
  send: (target: string) => Promise<unknown>,
) {
  const [cooldown, setCooldown] = useState(0);
  const [sending, setSending] = useState(false);

  const active = cooldown > 0;

  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => {
      setCooldown((c) => (c <= 1 ? 0 : c - 1));
    }, 1000);
    return () => clearInterval(id);
  }, [active]);

  async function sendCode(target: string) {
    if (cooldown > 0 || sending) return;
    setSending(true);
    try {
      await send(target);
      setCooldown(60);
    } finally {
      setSending(false);
    }
  }

  return { cooldown, sending, sendCode };
}
