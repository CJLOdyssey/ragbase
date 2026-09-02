interface BrandLogoProps {
  className?: string;
  size?: number;
}

export function BrandLogo({ className = '', size }: BrandLogoProps) {
  const props = size ? { width: size, height: size } : {};
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 512 512"
      className={className}
      {...props}
    >
      <defs>
        <linearGradient
          id="lb-bg"
          x1="0"
          y1="0"
          x2="512"
          y2="512"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0%" stopColor="var(--logo-bg-1)" />
          <stop offset="100%" stopColor="var(--logo-bg-2)" />
        </linearGradient>
        <filter id="lb-blur-sm">
          <feGaussianBlur in="SourceGraphic" stdDeviation="2" />
        </filter>
        <filter id="lb-blur-md">
          <feGaussianBlur in="SourceGraphic" stdDeviation="4" />
        </filter>
      </defs>

      {/* Background */}
      <rect width="512" height="512" rx="112" fill="url(#lb-bg)" />

      {/* Database cylinder */}
      <g transform="translate(115, 330)">
        <ellipse
          cx="5"
          cy="8"
          rx="72"
          ry="20"
          fill="var(--logo-shadow)"
          opacity="0.8"
          filter="url(#lb-blur-md)"
        />
        <path
          d="M-72,-20 v-55 a72,20 0 0 0 144,0 v55"
          fill="var(--logo-cyan-body)"
          opacity="0.7"
        />
        <path
          d="M-72,-20 v-55 a72,20 0 0 0 144,0 v55"
          fill="none"
          stroke="var(--logo-cyan)"
          strokeWidth="2.5"
          opacity="0.6"
        />
        <ellipse
          cx="0"
          cy="-75"
          rx="72"
          ry="20"
          fill="var(--logo-cyan-top)"
          opacity="0.8"
        />
        <ellipse
          cx="0"
          cy="-75"
          rx="72"
          ry="20"
          fill="none"
          stroke="var(--logo-cyan)"
          strokeWidth="2.5"
          opacity="0.7"
        />
        <ellipse cx="-20" cy="-80" rx="30" ry="8" fill="#fff" opacity="0.12" />
        <ellipse
          cx="0"
          cy="-45"
          rx="72"
          ry="20"
          fill="none"
          stroke="var(--logo-cyan)"
          strokeWidth="1.5"
          opacity="0.3"
        />
      </g>

      {/* Vector network */}
      <g>
        <rect
          x="140"
          y="90"
          width="260"
          height="220"
          rx="20"
          fill="var(--logo-glass)"
        />
        <rect
          x="140"
          y="90"
          width="260"
          height="220"
          rx="20"
          fill="none"
          stroke="var(--logo-glass-stroke)"
          strokeWidth="1"
        />

        <g
          stroke="var(--logo-emerald)"
          strokeWidth="2.5"
          opacity="0.5"
          filter="url(#lb-blur-sm)"
        >
          <line x1="220" y1="145" x2="315" y2="120" />
          <line x1="220" y1="145" x2="295" y2="205" />
          <line x1="315" y1="120" x2="360" y2="190" />
          <line x1="295" y1="205" x2="360" y2="190" />
          <line x1="295" y1="205" x2="255" y2="280" />
          <line x1="190" y1="235" x2="255" y2="280" />
          <line x1="190" y1="235" x2="165" y2="180" />
          <line x1="165" y1="180" x2="220" y2="145" />
        </g>
        <g stroke="var(--logo-emerald)" strokeWidth="2" opacity="0.6">
          <line x1="220" y1="145" x2="315" y2="120" />
          <line x1="220" y1="145" x2="295" y2="205" />
          <line x1="315" y1="120" x2="360" y2="190" />
          <line x1="295" y1="205" x2="360" y2="190" />
          <line x1="295" y1="205" x2="255" y2="280" />
          <line x1="190" y1="235" x2="255" y2="280" />
          <line x1="190" y1="235" x2="165" y2="180" />
          <line x1="165" y1="180" x2="220" y2="145" />
        </g>

        <circle
          cx="220"
          cy="145"
          r="14"
          fill="var(--logo-emerald-fill)"
          opacity="0.9"
        />
        <circle
          cx="220"
          cy="145"
          r="14"
          fill="none"
          stroke="var(--logo-emerald)"
          strokeWidth="2"
        />
        <circle cx="216" cy="140" r="5" fill="#fff" opacity="0.25" />

        <circle
          cx="315"
          cy="120"
          r="11"
          fill="var(--logo-emerald-fill)"
          opacity="0.8"
        />
        <circle
          cx="315"
          cy="120"
          r="11"
          fill="none"
          stroke="var(--logo-emerald)"
          strokeWidth="2"
        />
        <circle cx="312" cy="116" r="4" fill="#fff" opacity="0.2" />

        <circle
          cx="295"
          cy="205"
          r="17"
          fill="var(--logo-emerald-fill)"
          opacity="0.95"
        />
        <circle
          cx="295"
          cy="205"
          r="17"
          fill="none"
          stroke="var(--logo-emerald)"
          strokeWidth="2.5"
        />
        <circle cx="290" cy="199" r="6" fill="#fff" opacity="0.3" />
        <circle
          cx="295"
          cy="205"
          r="25"
          fill="none"
          stroke="var(--logo-emerald-glow)"
          strokeWidth="2"
          opacity="0.4"
        />
        <circle
          cx="295"
          cy="205"
          r="33"
          fill="none"
          stroke="var(--logo-emerald-glow)"
          strokeWidth="1"
          opacity="0.2"
        />

        <circle
          cx="190"
          cy="235"
          r="12"
          fill="var(--logo-emerald-fill)"
          opacity="0.85"
        />
        <circle
          cx="190"
          cy="235"
          r="12"
          fill="none"
          stroke="var(--logo-emerald)"
          strokeWidth="2"
        />
        <circle cx="187" cy="231" r="4" fill="#fff" opacity="0.2" />

        <circle
          cx="360"
          cy="190"
          r="9"
          fill="var(--logo-emerald-fill)"
          opacity="0.7"
        />
        <circle
          cx="360"
          cy="190"
          r="9"
          fill="none"
          stroke="var(--logo-emerald)"
          strokeWidth="1.5"
        />

        <circle
          cx="255"
          cy="280"
          r="13"
          fill="var(--logo-emerald-fill)"
          opacity="0.8"
        />
        <circle
          cx="255"
          cy="280"
          r="13"
          fill="none"
          stroke="var(--logo-emerald)"
          strokeWidth="2"
        />

        <circle
          cx="165"
          cy="180"
          r="10"
          fill="var(--logo-emerald-fill)"
          opacity="0.75"
        />
        <circle
          cx="165"
          cy="180"
          r="10"
          fill="none"
          stroke="var(--logo-emerald)"
          strokeWidth="1.5"
        />
      </g>

      {/* Search magnifying glass */}
      <g transform="translate(385, 365)">
        <circle
          cx="5"
          cy="5"
          r="48"
          fill="var(--logo-shadow)"
          opacity="0.6"
          filter="url(#lb-blur-md)"
        />
        <line
          x1="35"
          y1="35"
          x2="72"
          y2="72"
          stroke="var(--logo-amber-body)"
          strokeWidth="10"
          strokeLinecap="round"
        />
        <line
          x1="35"
          y1="35"
          x2="72"
          y2="72"
          stroke="var(--logo-amber-handle)"
          strokeWidth="8"
          strokeLinecap="round"
        />
        <circle
          cx="0"
          cy="0"
          r="46"
          fill="var(--logo-amber-body)"
          opacity="0.6"
        />
        <circle
          cx="0"
          cy="0"
          r="46"
          fill="none"
          stroke="var(--logo-amber)"
          strokeWidth="5"
        />
        <circle cx="0" cy="0" r="36" fill="var(--logo-bg-2)" opacity="0.5" />
        <circle
          cx="0"
          cy="0"
          r="36"
          fill="none"
          stroke="var(--logo-amber)"
          strokeWidth="1.5"
          opacity="0.3"
        />
        <ellipse
          cx="-10"
          cy="-12"
          rx="16"
          ry="10"
          fill="#fff"
          opacity="0.1"
          transform="rotate(-20)"
        />
      </g>

      {/* AI spark */}
      <g transform="translate(418, 95)">
        <circle
          cx="0"
          cy="0"
          r="28"
          fill="var(--logo-rose)"
          opacity="0.15"
          filter="url(#lb-blur-md)"
        />
        <path
          d="M0,-22 L6,-8 L22,-8 L9,2 L14,18 L0,9 L-14,18 L-9,2 L-22,-8 L-6,-8 Z"
          fill="var(--logo-rose-fill)"
          opacity="0.9"
        />
        <path
          d="M0,-22 L6,-8 L22,-8 L9,2 L14,18 L0,9 L-14,18 L-9,2 L-22,-8 L-6,-8 Z"
          fill="none"
          stroke="var(--logo-rose)"
          strokeWidth="1.5"
        />
        <circle cx="-3" cy="-8" r="4" fill="#fff" opacity="0.3" />
      </g>
      <g transform="translate(448, 138) scale(0.5)">
        <path
          d="M0,-22 L6,-8 L22,-8 L9,2 L14,18 L0,9 L-14,18 L-9,2 L-22,-8 L-6,-8 Z"
          fill="var(--logo-rose-fill)"
          opacity="0.6"
        />
        <path
          d="M0,-22 L6,-8 L22,-8 L9,2 L14,18 L0,9 L-14,18 L-9,2 L-22,-8 L-6,-8 Z"
          fill="none"
          stroke="var(--logo-rose)"
          strokeWidth="2"
          opacity="0.5"
        />
      </g>

      {/* Query tokens */}
      <circle
        cx="175"
        cy="415"
        r="9"
        fill="var(--logo-violet-fill)"
        opacity="0.7"
      />
      <circle
        cx="175"
        cy="415"
        r="9"
        fill="none"
        stroke="var(--logo-violet)"
        strokeWidth="1.5"
        opacity="0.6"
      />
      <circle cx="173" cy="412" r="3" fill="#fff" opacity="0.2" />
      <circle
        cx="155"
        cy="440"
        r="6"
        fill="var(--logo-violet-fill)"
        opacity="0.5"
      />
      <circle
        cx="155"
        cy="440"
        r="6"
        fill="none"
        stroke="var(--logo-violet)"
        strokeWidth="1"
        opacity="0.4"
      />
    </svg>
  );
}
