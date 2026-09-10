import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from './AuthContext';
import { AuthTabs } from './AuthFormParts';
import ForgotPasswordForm from './ForgotPasswordForm';
import LoginPanel from './LoginPanel';
import RegisterPanel from './RegisterPanel';

interface Props {
  onClose: () => void;
}

/**
 * 黄金比例弹窗：φ ≈ 1.618
 *  · 间距级数（Fibonacci）8 / 13 / 21 / 34 / 55
 *  · 圆角 8 / 13 / 21，控件高 48，主字号 15 / 辅助 12
 *  · 登录/注册共用同一 600px 外壳与左栏扫码面板，仅右栏表单切换，宽度零跳变
 *    （大厂共识：同一 AuthForm 外壳 + mode 变体，避免异构布局造成撕裂）
 */
export default function LoginModal({ onClose }: Props) {
  const { t } = useTranslation();
  const {
    loginModalView: view,
    forgotPassword,
    resetPassword,
    setLoginModalView: setView,
  } = useAuth();

  if (view === 'forgot' || view === 'reset') {
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-[21px] backdrop-blur-sm"
        onClick={onClose}
      >
        <div
          className="relative flex w-full max-w-[460px] flex-col overflow-hidden rounded-[21px] bg-[#16161f] ring-1 ring-white/[0.06] [box-shadow:0_34px_89px_-21px_rgba(0,0,0,0.85)]"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between border-b border-white/[0.06] px-[34px] py-[21px]">
            <h3 className="m-0 text-[18px] font-semibold text-[#f4f4f8]">
              {t('auth.resetPassword')}
            </h3>
            <button
              className="flex items-center justify-center rounded-[8px] bg-transparent p-[8px] text-[#8b8b9a] transition-colors hover:bg-white/[0.06] hover:text-[#f4f4f8]"
              onClick={onClose}
              aria-label={t('common.close')}
            >
              <X size={18} />
            </button>
          </div>
          <div className="p-[34px]">
            <ForgotPasswordForm
              onSendCode={async (email) => {
                await forgotPassword(email);
              }}
              onReset={async (email, code, newPassword) => {
                await resetPassword(email, code, newPassword);
                setView('login');
              }}
              onBack={() => setView('login')}
              error=""
            />
          </div>
        </div>
      </div>
    );
  }

  const isRegister = view === 'register';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-[21px] backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative flex max-h-[89vh] w-full max-w-[600px] flex-col overflow-hidden rounded-[21px] bg-[#16161f] ring-1 ring-white/[0.06] [box-shadow:0_34px_89px_-21px_rgba(0,0,0,0.85)]"
        onClick={(e) => e.stopPropagation()}
        style={{ animation: 'fadeIn 0.22s ease' }}
      >
        <div className="pointer-events-none absolute right-[-55px] top-[-89px] h-[210px] w-[340px] rounded-full bg-[#4f7cff]/[0.09] blur-[89px]" />

        <div className="relative flex-shrink-0 px-[34px] pt-[34px] pb-[21px]">
          <div className="mb-[21px] flex items-center justify-between">
            <span className="brand-wordmark text-[30px] leading-[1.2] text-[#f4f4f8]">
              RagBase
            </span>
            <button
              className="flex items-center justify-center rounded-[8px] bg-transparent p-[8px] text-[#8b8b9a] transition-colors hover:bg-white/[0.06] hover:text-[#f4f4f8]"
              onClick={onClose}
              aria-label={t('common.close')}
            >
              <X size={18} />
            </button>
          </div>
          <AuthTabs
            view={isRegister ? 'register' : 'login'}
            onChange={setView}
            loginLabel={t('auth.login')}
            registerLabel={t('auth.register')}
          />
        </div>

        <div className="relative px-[34px] pb-[34px]">
          {isRegister ? <RegisterPanel /> : <LoginPanel />}
        </div>
      </div>
    </div>
  );
}
