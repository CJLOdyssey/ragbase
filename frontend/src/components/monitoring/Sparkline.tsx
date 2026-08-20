export interface SparklineProps {
  values: number[];
  color: string;
  fillId: string;
  width?: number;
  height?: number;
  fill?: boolean;
  strokeWidth?: number;
  invert?: boolean;
  className?: string;
}

function normalize(values: number[]): number[] {
  if (values.length === 0) return [];
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (max === min) return values.map(() => 0.5);
  return values.map((v) => (v - min) / (max - min));
}

export function buildLinePath(norm: number[], w: number, h: number): string {
  if (norm.length === 0) return '';
  const step = w / (norm.length - 1);
  return norm
    .map((v, i) => {
      const x = (i * step).toFixed(1);
      const y = (h - v * h).toFixed(1);
      return `${i === 0 ? 'M' : 'L'}${x},${y}`;
    })
    .join(' ');
}

export default function Sparkline({
  values,
  color,
  fillId,
  width = 120,
  height = 32,
  fill = true,
  strokeWidth = 1.5,
  invert = false,
  className,
}: SparklineProps) {
  const norm = invert ? normalize([...values].reverse()) : normalize(values);
  const line = buildLinePath(norm, width, height);
  const area = `${line} L${width},${height} L0,${height} Z`;

  return (
    <svg
      width="100%"
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className={className}
      style={{ display: 'block' }}
      aria-hidden={true}
    >
      <defs>
        <linearGradient id={fillId} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      {fill && <path d={area} fill={`url(#${fillId})`} />}
      <path
        d={line}
        stroke={color}
        strokeWidth={strokeWidth}
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
