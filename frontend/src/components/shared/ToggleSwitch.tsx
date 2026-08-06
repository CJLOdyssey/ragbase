interface Props {
  checked: boolean;
  onChange: (checked: boolean) => void;
  size?: 'sm' | 'md';
  label?: string;
}

export default function ToggleSwitch({ checked, onChange, size = 'md', label }: Props) {
  return (
    <label
      className={`relative inline-block cursor-pointer flex-shrink-0 ${size === 'sm' ? 'w-9 h-5' : 'w-10 h-[22px]'}`}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        aria-label={label || 'Toggle switch'}
        className="opacity-0 w-0 h-0 absolute peer"
      />
      <span
        className={
          `absolute inset-0 rounded-[22px] transition-colors duration-200 bg-[var(--color-surface-hover)] peer-checked:bg-[var(--color-accent)]
          before:content-[''] before:absolute before:rounded-full before:transition-all before:duration-200 before:bg-[var(--color-text-muted)] peer-checked:before:bg-[var(--color-text-on-accent)]
          ${size === 'sm'
            ? 'before:h-[14px] before:w-[14px] before:left-[3px] before:bottom-[3px] peer-checked:before:translate-x-4'
            : 'before:h-4 before:w-4 before:left-[3px] before:bottom-[3px] peer-checked:before:translate-x-[18px]'}`
        }
      />
    </label>
  );
}
