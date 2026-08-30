// Small inline icon set -- avoids pulling in an icon library for a handful of glyphs.

export function BrandMark({ size = 32 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" className="brand-mark">
      <defs>
        <linearGradient id="brandGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#3b6fe0" />
          <stop offset="1" stopColor="#1d3f8f" />
        </linearGradient>
      </defs>
      <rect width="48" height="48" rx="11" fill="url(#brandGrad)" />
      <g stroke="#eaf1ff" strokeWidth="2.4" strokeLinecap="round">
        <line x1="14" y1="14" x2="21" y2="21" />
        <line x1="34" y1="14" x2="27" y2="21" />
        <line x1="14" y1="34" x2="21" y2="27" />
        <line x1="34" y1="34" x2="27" y2="27" />
      </g>
      <g fill="none" stroke="#eaf1ff" strokeWidth="2.2">
        <circle cx="12" cy="12" r="4.2" />
        <circle cx="36" cy="12" r="4.2" />
        <circle cx="12" cy="36" r="4.2" />
        <circle cx="36" cy="36" r="4.2" />
      </g>
      <rect x="19.5" y="19.5" width="9" height="9" rx="2.5" fill="#eaf1ff" />
    </svg>
  );
}

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

export function CheckIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}
