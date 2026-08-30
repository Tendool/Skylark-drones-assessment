// Small inline icon set -- avoids pulling in an icon library for a handful of glyphs.

export function RefreshIcon({ spinning = false }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={spinning ? "icon-spin" : undefined}
    >
      <path d="M21 12a9 9 0 1 1-2.64-6.36" />
      <path d="M21 3v6h-6" />
    </svg>
  );
}

export function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 2 11 13" />
      <path d="M22 2 15 22l-4-9-9-4Z" />
    </svg>
  );
}

export function SunIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
    </svg>
  );
}

export function MoonIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" />
    </svg>
  );
}

export function SparkleIcon({ size = 30 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

export function UserIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21a8 8 0 0 0-16 0" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

export function BotIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="9" width="16" height="11" rx="3" />
      <path d="M12 9V5" />
      <circle cx="12" cy="3.5" r="1.5" fill="currentColor" stroke="none" />
      <circle cx="9" cy="14.5" r="1.3" fill="currentColor" stroke="none" />
      <circle cx="15" cy="14.5" r="1.3" fill="currentColor" stroke="none" />
      <path d="M2 13h2M20 13h2" />
    </svg>
  );
}

export function CopyIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="12" height="12" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

// Hero illustration for the empty chat state: a drone (same rotor language as
// BrandMark) surveying a floating glass dashboard card. Hand-drawn to match
// the brand rather than pulled from a generic icon set.
export function EmptyStateIllustration({ size = 176 }) {
  return (
    <svg width={size} height={size * 0.8} viewBox="0 0 220 176" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="heroDrone" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#ff8a52" />
          <stop offset="1" stopColor="#f1592a" />
        </linearGradient>
        <linearGradient id="heroBar" x1="0" y1="1" x2="0" y2="0">
          <stop offset="0" stopColor="#ffb199" />
          <stop offset="1" stopColor="#f1592a" />
        </linearGradient>
        <radialGradient id="heroGlow" cx="0.5" cy="0.4" r="0.6">
          <stop offset="0" stopColor="#ff8a52" stopOpacity="0.35" />
          <stop offset="1" stopColor="#ff8a52" stopOpacity="0" />
        </radialGradient>
      </defs>

      <circle cx="112" cy="78" r="86" fill="url(#heroGlow)" />

      {/* dashboard card */}
      <g transform="translate(40 92)">
        <rect x="0" y="0" width="140" height="76" rx="14" fill="currentColor" opacity="0.06" />
        <rect x="0.75" y="0.75" width="138.5" height="74.5" rx="13.25" stroke="currentColor" strokeOpacity="0.16" />
        <rect x="16" y="40" width="14" height="24" rx="3" fill="url(#heroBar)" opacity="0.85" />
        <rect x="36" y="28" width="14" height="36" rx="3" fill="url(#heroBar)" opacity="0.7" />
        <rect x="56" y="18" width="14" height="46" rx="3" fill="url(#heroBar)" opacity="0.9" />
        <path d="M84 46 100 32 116 40 132 20" stroke="#f1592a" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" fill="none" />
        <circle cx="132" cy="20" r="3.5" fill="#ff8a52" />
      </g>

      {/* drone */}
      <g transform="translate(96 8)">
        <g stroke="url(#heroDrone)" strokeWidth="3" strokeLinecap="round">
          <line x1="6" y1="6" x2="18" y2="18" />
          <line x1="42" y1="6" x2="30" y2="18" />
          <line x1="6" y1="42" x2="18" y2="30" />
          <line x1="42" y1="42" x2="30" y2="30" />
        </g>
        <g fill="none" stroke="url(#heroDrone)" strokeWidth="2.6">
          <ellipse cx="4" cy="4" rx="7" ry="3.4" />
          <ellipse cx="44" cy="4" rx="7" ry="3.4" />
          <ellipse cx="4" cy="44" rx="7" ry="3.4" />
          <ellipse cx="44" cy="44" rx="7" ry="3.4" />
        </g>
        <rect x="16" y="16" width="16" height="16" rx="4.5" fill="url(#heroDrone)" />
        <circle cx="24" cy="24" r="3" fill="#ffffff" opacity="0.9" />
      </g>

      {/* signal ping from drone to dashboard */}
      <path d="M116 52 C110 66, 100 78, 96 92" stroke="currentColor" strokeOpacity="0.22" strokeWidth="2" strokeDasharray="1 6" strokeLinecap="round" fill="none" />

      {/* floating sparkle accents */}
      <g stroke="currentColor" strokeOpacity="0.3" strokeWidth="2" strokeLinecap="round">
        <path d="M182 40v10M177 45h10" />
        <path d="M26 26v8M22 30h8" />
      </g>
    </svg>
  );
}

export function CheckIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}
