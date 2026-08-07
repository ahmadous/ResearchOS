// Marque ResearchOS = ton image détourée (fond transparent, lisible sur tout thème).
export default function Logo({ size = 32 }) {
  return (
    <img src="/Logo-mark.png" alt="ResearchOS"
      style={{ height: size, width: 'auto', display: 'block' }} />
  )
}

// Logotype : marque + « ResearchOS » (Research adaptatif, OS en dégradé).
export function Wordmark({ size = 30 }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      <Logo size={size} />
      <span style={{ fontWeight: 800, fontSize: size * 0.6, letterSpacing: '-0.02em' }}>
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
