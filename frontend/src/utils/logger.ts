/* eslint-disable no-console */
import * as Sentry from '@sentry/browser';

enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

const CURRENT_LOG_LEVEL =
  import.meta.env.MODE === 'production' ? LogLevel.WARN : LogLevel.DEBUG;
const IS_PRODUCTION = import.meta.env.MODE === 'production';

const log = (
  level: LogLevel,
  message: string,
  ...optionalParams: unknown[]
): void => {
  if (IS_PRODUCTION && level < CURRENT_LOG_LEVEL) return;

  switch (level) {
    case LogLevel.DEBUG:
      console.debug(`[DEBUG] ${message}`, ...optionalParams);
      break;
    case LogLevel.INFO:
      console.info(`[INFO] ${message}`, ...optionalParams);
      break;
    case LogLevel.WARN:
      // WARN 仅本地 console：常规恢复路径（WS 重连、加载失败回退等）
      // 的 WARN 是预期噪声，全部上报 Sentry 会淹没真实错误信号。
      console.warn(`[WARN] ${message}`, ...optionalParams);
      break;
    case LogLevel.ERROR:
      console.error(`[ERROR] ${message}`, ...optionalParams);
      if (IS_PRODUCTION) {
        const error = optionalParams.find((p) => p instanceof Error) as
          Error | undefined;
        if (error) Sentry.captureException(error);
        else Sentry.captureMessage(message, 'error');
      }
      break;
  }
};

export const debug = (message: string, ...optionalParams: unknown[]): void => {
  log(LogLevel.DEBUG, message, ...optionalParams);
};

export const info = (message: string, ...optionalParams: unknown[]): void => {
  log(LogLevel.INFO, message, ...optionalParams);
};

export const warn = (message: string, ...optionalParams: unknown[]): void => {
  log(LogLevel.WARN, message, ...optionalParams);
};

export const error = (message: string, ...optionalParams: unknown[]): void => {
  log(LogLevel.ERROR, message, ...optionalParams);
};

export default { debug, info, warn, error };
