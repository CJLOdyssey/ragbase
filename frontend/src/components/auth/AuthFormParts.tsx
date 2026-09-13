import { type ReactNode } from 'react';
import { Eye, EyeOff, Loader2, QrCode } from 'lucide-react';
import { type AuthModalView } from './AuthContext';

/** 黄金比例圆角 13px，控件高 48px，主字号 15px。左右内边距由各字段显式给定。 */
const authInputClass =
  'h-[48px] w-full rounded-[13px] border border-white/[0.07] bg-[#22222e] text-[15px] text-[#f4f4f8] placeholder:text-[#6b6b7a] outline-none transition-colors focus:border-[#4f7cff]/70';

/**
 * 左栏扫码面板（宽 190 = φ 标尺）。
 * 登录 / 注册两态共用同一面板，内容完全一致，避免切换时结构跳变。
 */
export function WechatQrPanel() {
  return (
    <div className="flex w-[190px] flex-shrink-0 flex-col items-center self-stretch">
      <h4 className="mb-[21px] text-[14px] font-medium text-[#c8c8d2]">
        微信扫码登录
      </h4>
      <div className="flex w-full flex-1 flex-col items-center justify-center rounded-[13px] bg-white/[0.02] ring-1 ring-white/[0.05]">
        <div className="relative flex h-[150px] w-[150px] items-center justify-center rounded-[13px] bg-white p-[13px]">
          <div className="flex h-full w-full flex-col items-center justify-center gap-[6px] rounded-[8px] border border-dashed border-[#c8c8d2]">
            <QrCode size={30} className="text-[#9a9aa8]" />
            <span className="text-[11px] text-[#9a9aa8]">即将支持</span>
          </div>
        </div>
        <p className="mt-[13px] text-[12px] text-[#6b6b7a]">请使用微信扫一扫</p>
      </div>
    </div>
  );
}

/**
 * 认证两栏布局：左栏标题与右栏标题同基线对齐；下方扫码面板（bg+ring）与右表单
 * 等高等宽、上下像素对齐，内容面板内垂直居中。φ：190 : 308。
 * 两态结构完全一致，仅右栏内容切换，宽度零跳变。
 */
export function AuthTwoColumn({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-stretch gap-[34px]">
      <WechatQrPanel />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}

export function EmailField({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <input
      type="email"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder="邮箱地址"
      autoComplete="email"
      className={`${authInputClass} px-[16px]`}
    />
  );
}

interface PasswordFieldProps {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  visible: boolean;
  onToggleVisible: () => void;
}

export function PasswordField({
  value,
  onChange,
  placeholder,
  visible,
  onToggleVisible,
}: PasswordFieldProps) {
  return (
    <div className="relative">
      <input
        type={visible ? 'text' : 'password'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={`${authInputClass} pl-[16px] pr-[48px]`}
      />
      <button
        type="button"
        onClick={onToggleVisible}
        className="absolute right-[16px] top-1/2 -translate-y-1/2 bg-transparent text-[#8b8b9a] transition-colors hover:text-[#f4f4f8]"
      >
        {visible ? <EyeOff size={18} /> : <Eye size={18} />}
      </button>
    </div>
  );
}

interface CodeFieldProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  cooldown: number;
  sending: boolean;
  placeholder?: string;
}

export function CodeField({
  value,
  onChange,
  onSend,
  cooldown,
  sending,
  placeholder = '验证码',
}: CodeFieldProps) {
  return (
    <div className="flex gap-[13px]">
      <input
        type="text"
        value={value}
        onChange={(e) =>
          onChange(e.target.value.replace(/\D/g, '').slice(0, 6))
        }
        placeholder={placeholder}
        className={`${authInputClass} min-w-0 flex-1 px-[16px]`}
      />
      <button
        type="button"
        onClick={onSend}
        disabled={cooldown > 0 || sending}
        className="h-[48px] shrink-0 rounded-[13px] border border-white/[0.07] bg-[#22222e] px-[16px] text-[14px] text-[#c8c8d2] transition-colors hover:bg-[#2b2b38] disabled:cursor-not-allowed disabled:opacity-50"
      >
        {cooldown > 0 ? `${cooldown}s` : '获取验证码'}
      </button>
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="rounded-[13px] border border-red-500/20 bg-red-500/10 px-[16px] py-[10px] text-[13px] text-red-400">
      {message}
    </div>
  );
}

interface AgreementProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  children: ReactNode;
}

export function Agreement({ checked, onChange, children }: AgreementProps) {
  return (
    <label className="flex items-center gap-[8px] pt-[8px]">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="accent-[#4f7cff]"
      />
      <span className="whitespace-nowrap text-[12px] leading-none text-[#8b8b9a]">
        {children}
      </span>
    </label>
  );
}

interface SubmitButtonProps {
  submitting: boolean;
  label: string;
}

export function SubmitButton({ submitting, label }: SubmitButtonProps) {
  return (
    <button
      type="submit"
      disabled={submitting}
      className="flex h-[48px] w-full items-center justify-center gap-[8px] rounded-[13px] border-none bg-[#4f7cff] text-[15px] font-semibold text-white transition-all duration-200 hover:bg-[#5f89ff] disabled:cursor-not-allowed disabled:opacity-50"
    >
      {submitting && <Loader2 size={18} className="animate-spin" />}
      {label}
    </button>
  );
}

interface AuthTabsProps {
  view: AuthModalView;
  onChange: (view: AuthModalView) => void;
  loginLabel: string;
  registerLabel: string;
}

export function AuthTabs({
  view,
  onChange,
  loginLabel,
  registerLabel,
}: AuthTabsProps) {
  const tabs = [
    { key: 'login' as const, label: loginLabel },
    { key: 'register' as const, label: registerLabel },
  ];
  return (
    <div className="flex rounded-[13px] bg-[#22222e] p-[4px]">
      {tabs.map((tab) => {
        const active = view === tab.key;
        return (
          <button
            key={tab.key}
            onClick={() => onChange(tab.key)}
            className="flex-1 rounded-[9px] border-none py-[10px] text-[14px] transition-all duration-200"
            style={{
              background: active ? '#32323f' : 'transparent',
              color: active ? '#f4f4f8' : '#8b8b9a',
              fontWeight: active ? 600 : 400,
            }}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
