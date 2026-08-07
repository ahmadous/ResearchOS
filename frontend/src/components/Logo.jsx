// Marque ResearchOS (SVG vectoriel) : un « R » en dégradé bleu -> violet
// avec le motif de nœuds « recherche/molécule ». Net à toute taille, sans image.
export default function Logo({ size = 32 }) {
  const uid = 'ros-grad'
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" fill="none"
      xmlns="http://www.w3.org/2000/svg" role="img" aria-label="ResearchOS">
      <defs>
        <linearGradient id={uid} x1="20" y1="18" x2="100" y2="104" gradientUnits="userSpaceOnUse">
          <stop stopColor="#4f46e5" />
          <stop offset="1" stopColor="#7c3aed" />
        </linearGradient>
      </defs>
      {/* Le "R" */}
      <path
        d="M44 102 V34 H66 A19 19 0 0 1 66 72 H44 M62 72 L88 102"
        stroke={`url(#${uid})`} strokeWidth="13"
        strokeLinecap="round" strokeLinejoin="round" />
      {/* Motif de nœuds (recherche) */}
      <g stroke="#3b82f6" strokeWidth="5" strokeLinecap="round">
        <line x1="30" y1="57" x2="51" y2="47" />
        <line x1="51" y1="47" x2="43" y2="74" />
      </g>
      <g fill="#3b82f6">
        <circle cx="30" cy="57" r="7" />
        <circle cx="51" cy="47" r="7" />
        <circle cx="43" cy="74" r="7" />
      </g>
    </svg>
  )
}

// Logotype complet : marque + « ResearchOS » (Research foncé, OS en dégradé).
export function Wordmark({ size = 34 }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      <Logo size={size} />
      <span style={{ fontWeight: 800, fontSize: size * 0.62, letterSpacing: '-0.02em' }}>
        <span style={{ color: 'currentColor' }}>Research</span>
        <span style={{
          background: 'linear-gradient(90deg,#4f46e5,#7c3aed)',
          WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
        }}>OS</span>
      </span>
    </span>
  )
}
