import React from "react";

export function CandleLogo({ className = "w-9 h-9", size = 38 }: { className?: string; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <defs>
        {/* Glow Filters */}
        <filter id="cLogoGlow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="1.5" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>

        {/* Gradients */}
        <linearGradient id="cardGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#1e1e2d" />
          <stop offset="100%" stopColor="#0f0f17" />
        </linearGradient>
        <linearGradient id="cardBorder" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#f59e0b" />
          <stop offset="50%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#10b981" />
        </linearGradient>

        <linearGradient id="bullGreen" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#34d399" />
          <stop offset="100%" stopColor="#059669" />
        </linearGradient>

        <linearGradient id="bullGold" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#fbbf24" />
          <stop offset="100%" stopColor="#d97706" />
        </linearGradient>

        <linearGradient id="bullCyan" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#38bdf8" />
          <stop offset="100%" stopColor="#0284c7" />
        </linearGradient>

        <linearGradient id="trendArrow" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#f59e0b" />
          <stop offset="50%" stopColor="#38bdf8" />
          <stop offset="100%" stopColor="#10b981" />
        </linearGradient>
      </defs>

      {/* Modern Rounded Diamond/Squircle Frame */}
      <rect
        x="2.5"
        y="2.5"
        width="43"
        height="43"
        rx="12"
        fill="url(#cardGrad)"
        stroke="url(#cardBorder)"
        strokeWidth="1.8"
        className="logo-badge-bg"
      />

      {/* Subtle Grid Lines */}
      <line x1="8" y1="24" x2="40" y2="24" stroke="#ffffff" strokeOpacity="0.08" strokeDasharray="2 2" className="logo-grid-line" />
      <line x1="24" y1="8" x2="24" y2="40" stroke="#ffffff" strokeOpacity="0.08" strokeDasharray="2 2" className="logo-grid-line" />

      {/* ── CANDLE 1 (Left - Green Bullish Candle) ── */}
      <line x1="11" y1="15" x2="11" y2="35" stroke="#34d399" strokeWidth="1.6" strokeLinecap="round" />
      <rect x="8.5" y="21" width="5" height="9" rx="1.5" fill="url(#bullGreen)" filter="url(#cLogoGlow)" />

      {/* ── CANDLE 2 (Center Left - Amber Gold Candle) ── */}
      <line x1="19.5" y1="19" x2="19.5" y2="39" stroke="#fbbf24" strokeWidth="1.6" strokeLinecap="round" />
      <rect x="17" y="24" width="5" height="10" rx="1.5" fill="url(#bullGold)" filter="url(#cLogoGlow)" />

      {/* ── CANDLE 3 (Center Right - Cyan Breakout Candle) ── */}
      <line x1="28" y1="9" x2="28" y2="31" stroke="#38bdf8" strokeWidth="1.6" strokeLinecap="round" />
      <rect x="25.5" y="14" width="5" height="12" rx="1.5" fill="url(#bullCyan)" filter="url(#cLogoGlow)" />

      {/* ── CANDLE 4 (Right - Apex Peak Green Candle) ── */}
      <line x1="36.5" y1="6" x2="36.5" y2="26" stroke="#34d399" strokeWidth="1.6" strokeLinecap="round" />
      <rect x="34" y="9" width="5" height="11" rx="1.5" fill="url(#bullGreen)" filter="url(#cLogoGlow)" />

      {/* ── Ascending Breakout Trend Curve ── */}
      <path
        d="M 11 25.5 Q 19.5 31, 28 20 T 36.5 14"
        stroke="url(#trendArrow)"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
        filter="url(#cLogoGlow)"
      />

      {/* Apex glowing star / target pulse */}
      <circle cx="36.5" cy="14.5" r="3.5" fill="#34d399" fillOpacity="0.4" />
      <circle cx="36.5" cy="14.5" r="1.8" fill="#ffffff" />
    </svg>
  );
}

export const EagleLogo = CandleLogo;
export const TradeMatrixLogo = CandleLogo;
