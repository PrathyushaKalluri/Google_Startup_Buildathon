import type { AssetType } from '../types';

const INK = '#302820';
const C = { haldi: '#FFC83D', mirchi: '#F46D54', peacock: '#157A78', leaf: '#70A95A', cream: '#FFF8EB', sand: '#EDE1CD', white: '#FFFFFF' };

function Face({ x, y, mood = 'happy', s = 1 }: { x: number; y: number; mood?: 'happy' | 'worried'; s?: number }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`} stroke={INK} strokeWidth={2.2} strokeLinecap="round" fill="none">
      <circle cx={-7} cy={0} r={2.2} fill={INK} stroke="none" />
      <circle cx={7} cy={0} r={2.2} fill={INK} stroke="none" />
      {mood === 'happy' ? <path d="M-5 6 Q0 10 5 6" /> : <path d="M-5 9 Q0 5 5 9" />}
      {mood === 'happy' ? (
        <>
          <circle cx={-12} cy={5} r={2.2} fill={C.mirchi} stroke="none" opacity={0.55} />
          <circle cx={12} cy={5} r={2.2} fill={C.mirchi} stroke="none" opacity={0.55} />
        </>
      ) : (
        <path d="M13 -6 q2 3 0 5 q-2 -2 0 -5z" fill={C.peacock} stroke="none" />
      )}
    </g>
  );
}

/** Doodle-style appliance with a little personality. Each type has its own shape and colour. */
export function ApplianceArt({ type, mood = 'happy', className = 'h-20 w-20' }: { type: AssetType; mood?: 'happy' | 'worried'; className?: string }) {
  const stroke = { stroke: INK, strokeWidth: 2.5, strokeLinejoin: 'round' as const, strokeLinecap: 'round' as const };
  return (
    <svg viewBox="0 0 120 120" className={className} aria-hidden="true">
      {type === 'ac' && (
        <g>
          <rect x={14} y={30} width={92} height={42} rx={14} fill={C.white} {...stroke} />
          <path d="M24 62 H96" {...stroke} fill="none" />
          <circle cx={92} cy={40} r={3} fill={C.leaf} />
          <Face x={58} y={45} mood={mood} />
          <g stroke={C.peacock} strokeWidth={2.5} strokeLinecap="round" fill="none">
            <path d="M34 82 q4 6 0 12 q-4 6 0 12" />
            <path d="M60 82 q4 6 0 12 q-4 6 0 12" />
            <path d="M86 82 q4 6 0 12 q-4 6 0 12" />
          </g>
        </g>
      )}
      {type === 'geyser' && (
        <g>
          <rect x={34} y={14} width={52} height={80} rx={26} fill={mood === 'worried' ? C.mirchi : C.haldi} {...stroke} />
          <circle cx={60} cy={70} r={9} fill={C.cream} {...stroke} />
          <path d="M60 70 L64 65" {...stroke} />
          <Face x={60} y={40} mood={mood} />
          <path d="M48 94 V104 M72 94 V104" {...stroke} />
          {mood === 'worried' ? (
            <path d="M90 30 l6 -4 M92 40 h7" stroke={C.peacock} strokeWidth={2.5} strokeLinecap="round" />
          ) : (
            <path d="M92 22 q4 -6 0 -12 M100 26 q4 -6 0 -12" stroke={C.mirchi} strokeWidth={2.5} fill="none" strokeLinecap="round" />
          )}
        </g>
      )}
      {type === 'ro' && (
        <g>
          <rect x={30} y={12} width={60} height={88} rx={12} fill={C.peacock} {...stroke} />
          <rect x={40} y={22} width={40} height={28} rx={8} fill={C.cream} {...stroke} />
          <Face x={60} y={36} mood={mood} s={0.9} />
          <path d="M60 58 c-6 9 -8 13 -8 17 a8 8 0 0 0 16 0 c0 -4 -2 -8 -8 -17z" fill="#BFE3F2" {...stroke} />
          <path d="M84 70 h12 v8" {...stroke} fill="none" />
          <path d="M96 84 q-2 4 0 6 q2 -2 0 -6z" fill="#BFE3F2" stroke={INK} strokeWidth={1.5} />
        </g>
      )}
      {type === 'washer' && (
        <g>
          <rect x={20} y={14} width={80} height={90} rx={14} fill={C.haldi} {...stroke} />
          <path d="M20 32 H100" {...stroke} />
          <circle cx={34} cy={23} r={3} fill={C.mirchi} />
          <circle cx={46} cy={23} r={3} fill={C.leaf} />
          <circle cx={60} cy={68} r={26} fill={C.cream} {...stroke} />
          <circle cx={60} cy={68} r={17} fill="#BFE3F2" stroke={INK} strokeWidth={2} />
          <Face x={60} y={66} mood={mood} s={0.85} />
          <circle cx={94} cy={52} r={4} fill="none" stroke={C.peacock} strokeWidth={2} />
          <circle cx={102} cy={42} r={2.5} fill="none" stroke={C.peacock} strokeWidth={2} />
        </g>
      )}
      {type === 'fridge' && (
        <g>
          <rect x={32} y={8} width={56} height={98} rx={12} fill={C.leaf} {...stroke} />
          <path d="M32 44 H88" {...stroke} />
          <path d="M78 22 V34 M78 54 V72" {...stroke} />
          <Face x={58} y={26} mood={mood} s={0.9} />
          <rect x={44} y={80} width={16} height={10} rx={2} fill={C.haldi} stroke={INK} strokeWidth={1.8} transform="rotate(-8 52 85)" />
        </g>
      )}
      {type === 'plumbing' && (
        <g>
          <path d="M20 46 H64 a14 14 0 0 1 14 14 V68" fill="none" stroke={INK} strokeWidth={12} strokeLinecap="round" />
          <path d="M20 46 H64 a14 14 0 0 1 14 14 V68" fill="none" stroke="#9FB7C4" strokeWidth={7} strokeLinecap="round" />
          <rect x={40} y={26} width={16} height={12} rx={3} fill={C.mirchi} {...stroke} />
          <path d="M48 26 V20 M38 20 H58" {...stroke} />
          <path d="M78 78 c-5 8 -7 11 -7 14 a7 7 0 0 0 14 0 c0 -3 -2 -6 -7 -14z" fill="#BFE3F2" {...stroke} />
          <Face x={36} y={78} mood={mood} s={0.8} />
        </g>
      )}
      {type === 'lighting' && (
        <g>
          <path d="M60 10 V24" {...stroke} />
          <path d="M40 24 H80 L72 44 H48 Z" fill={C.haldi} {...stroke} />
          <circle cx={60} cy={62} r={18} fill={C.cream} {...stroke} />
          <Face x={60} y={60} mood={mood} s={0.8} />
          <g stroke={C.haldi} strokeWidth={3} strokeLinecap="round">
            <path d="M30 62 H20 M90 62 H100 M38 86 l-7 7 M82 86 l7 7 M60 88 V100" />
          </g>
        </g>
      )}
    </svg>
  );
}

export function Sparkle({ className = 'h-5 w-5', color = C.haldi }: { className?: string; color?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <path d="M12 2 C12.8 8 16 11.2 22 12 C16 12.8 12.8 16 12 22 C11.2 16 8 12.8 2 12 C8 11.2 11.2 8 12 2Z" fill={color} stroke={INK} strokeWidth={1.4} strokeLinejoin="round" />
    </svg>
  );
}

export function Rangoli({ className = 'h-24 w-24', petals = 8 }: { className?: string; petals?: number }) {
  const colors = [C.haldi, C.mirchi, C.peacock, C.leaf];
  return (
    <svg viewBox="-50 -50 100 100" className={className} aria-hidden="true">
      {Array.from({ length: petals }).map((_, i) => (
        <g key={i} transform={`rotate(${(360 / petals) * i})`}>
          <path d="M0 -8 C8 -18 8 -32 0 -44 C-8 -32 -8 -18 0 -8Z" fill={colors[i % 4]} stroke={INK} strokeWidth={1.2} opacity={0.9} />
          <circle cy={-47} r={2} fill={INK} />
        </g>
      ))}
      <circle r={9} fill={C.cream} stroke={INK} strokeWidth={1.4} />
      <circle r={4} fill={C.mirchi} />
    </svg>
  );
}

export function Squiggle({ className = 'h-6 w-24', color = C.mirchi }: { className?: string; color?: string }) {
  return (
    <svg viewBox="0 0 100 20" className={className} aria-hidden="true" preserveAspectRatio="none">
      <path d="M2 12 Q12 2 22 12 T42 12 T62 12 T82 12 T98 10" fill="none" stroke={color} strokeWidth={3.5} strokeLinecap="round" />
    </svg>
  );
}

export function HandArrow({ className = 'h-10 w-16' }: { className?: string }) {
  return (
    <svg viewBox="0 0 80 50" className={className} aria-hidden="true">
      <path d="M4 40 C20 10 46 6 70 18" fill="none" stroke={INK} strokeWidth={2.5} strokeLinecap="round" strokeDasharray="1 6" />
      <path d="M60 10 L72 18 L60 26" fill="none" stroke={INK} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** The household agent: a warm haldi character with a teal gamcha and a spanner, among home objects. */
export function SaathiHero({ className = 'w-full max-w-[380px]' }: { className?: string }) {
  const s = { stroke: INK, strokeWidth: 2.5, strokeLinejoin: 'round' as const, strokeLinecap: 'round' as const };
  return (
    <svg viewBox="0 0 360 300" className={className} role="img" aria-label="Saathi, the household assistant, surrounded by an AC remote, a toolbox, a water purifier and a service receipt">
      <circle cx={180} cy={160} r={120} fill={C.cream} stroke={INK} strokeWidth={2} strokeDasharray="2 8" />
      {/* receipt */}
      <g transform="rotate(-10 62 90)">
        <path d="M30 50 h64 v86 l-8 -6 -8 6 -8 -6 -8 6 -8 -6 -8 6 -8 -6 -8 6z" fill={C.white} {...s} />
        <path d="M40 66 h44 M40 78 h30 M40 90 h40 M40 102 h22" stroke={INK} strokeWidth={2} strokeLinecap="round" opacity={0.5} />
        <circle cx={78} cy={112} r={10} fill="none" stroke={C.mirchi} strokeWidth={2.5} />
        <path d="M73 112 l4 4 7 -8" fill="none" stroke={C.mirchi} strokeWidth={2.5} strokeLinecap="round" />
      </g>
      {/* RO purifier */}
      <g transform="translate(272 54)">
        <rect x={0} y={0} width={46} height={72} rx={10} fill={C.peacock} {...s} />
        <rect x={8} y={8} width={30} height={20} rx={6} fill={C.cream} {...s} />
        <path d="M23 40 c-5 7 -6 10 -6 13 a6 6 0 0 0 12 0 c0 -3 -1 -6 -6 -13z" fill="#BFE3F2" {...s} />
      </g>
      {/* toolbox */}
      <g transform="translate(250 200)">
        <path d="M22 10 v-8 h30 v8" fill="none" {...s} />
        <rect x={0} y={10} width={74} height={44} rx={8} fill={C.mirchi} {...s} />
        <path d="M0 26 H74" {...s} />
        <rect x={30} y={22} width={14} height={9} rx={2} fill={C.haldi} stroke={INK} strokeWidth={2} />
      </g>
      {/* AC remote */}
      <g transform="rotate(14 70 220) translate(46 180)">
        <rect x={0} y={0} width={34} height={70} rx={10} fill={C.white} {...s} />
        <rect x={7} y={8} width={20} height={12} rx={3} fill={C.leaf} stroke={INK} strokeWidth={2} />
        <circle cx={11} cy={34} r={3.5} fill={C.haldi} stroke={INK} strokeWidth={1.5} />
        <circle cx={23} cy={34} r={3.5} fill={C.mirchi} stroke={INK} strokeWidth={1.5} />
        <circle cx={11} cy={48} r={3.5} fill={C.sand} stroke={INK} strokeWidth={1.5} />
        <circle cx={23} cy={48} r={3.5} fill={C.sand} stroke={INK} strokeWidth={1.5} />
      </g>
      {/* Saathi */}
      <g className="animate-float" style={{ transformOrigin: '180px 170px' }}>
        <path d="M180 58 V44" {...s} />
        <path d="M180 26 C181 34 186 39 194 40 C186 41 181 46 180 54 C179 46 174 41 166 40 C174 39 179 34 180 26Z" fill={C.haldi} {...s} strokeWidth={2} />
        <ellipse cx={180} cy={150} rx={78} ry={84} fill={C.haldi} {...s} />
        <ellipse cx={156} cy={108} rx={18} ry={9} fill={C.white} opacity={0.45} />
        <g stroke={INK} strokeWidth={3} strokeLinecap="round" fill="none">
          <circle cx={156} cy={140} r={5} fill={INK} stroke="none" />
          <circle cx={204} cy={140} r={5} fill={INK} stroke="none" />
          <path d="M164 160 Q180 174 196 160" />
        </g>
        <circle cx={140} cy={158} r={7} fill={C.mirchi} opacity={0.5} />
        <circle cx={220} cy={158} r={7} fill={C.mirchi} opacity={0.5} />
        <circle cx={180} cy={120} r={3.5} fill={C.mirchi} />
        {/* gamcha with check pattern */}
        <path d="M110 186 Q180 214 250 186 L246 204 Q180 232 114 204 Z" fill={C.peacock} {...s} />
        <path d="M140 196 v18 M164 202 v20 M196 202 v20 M220 196 v18" stroke={C.cream} strokeWidth={2} opacity={0.6} />
        <path d="M232 200 l10 34 l-16 2z" fill={C.peacock} {...s} />
        {/* spanner arm */}
        <path d="M104 150 Q84 140 78 118" fill="none" {...s} strokeWidth={6} />
        <path d="M104 150 Q84 140 78 118" fill="none" stroke={C.haldi} strokeWidth={3} strokeLinecap="round" />
        <g transform="rotate(-30 76 108)">
          <rect x={72} y={86} width={9} height={34} rx={3} fill="#B9B3A8" {...s} strokeWidth={2} />
          <path d="M66 86 a11 11 0 1 1 21 0 l-5 -2 v-8 h-11 v8z" fill="#B9B3A8" {...s} strokeWidth={2} />
        </g>
        <path d="M256 150 Q276 160 280 176" fill="none" {...s} strokeWidth={6} />
        <path d="M256 150 Q276 160 280 176" fill="none" stroke={C.haldi} strokeWidth={3} strokeLinecap="round" />
      </g>
      <g transform="translate(300 150) scale(1.1)">
        <path d="M12 2 C12.8 8 16 11.2 22 12 C16 12.8 12.8 16 12 22 C11.2 16 8 12.8 2 12 C8 11.2 11.2 8 12 2Z" fill={C.leaf} stroke={INK} strokeWidth={1.4} />
      </g>
      <g transform="translate(22 150) scale(0.8)">
        <path d="M12 2 C12.8 8 16 11.2 22 12 C16 12.8 12.8 16 12 22 C11.2 16 8 12.8 2 12 C8 11.2 11.2 8 12 2Z" fill={C.mirchi} stroke={INK} strokeWidth={1.4} />
      </g>
    </svg>
  );
}

/** Small apartment-balcony doodle with drying clothes, used for empty states and section headers. */
export function BalconyDoodle({ className = 'h-24 w-36' }: { className?: string }) {
  const s = { stroke: INK, strokeWidth: 2.2, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
  return (
    <svg viewBox="0 0 180 120" className={className} aria-hidden="true">
      <path d="M10 20 H170" {...s} />
      <path d="M30 20 q0 6 -6 8 h20 q-6 -2 -6 -8" fill="none" {...s} />
      <path d="M24 28 h20 l4 30 h-28z" fill={C.mirchi} {...s} />
      <path d="M70 20 v4 h26 v-4" fill="none" {...s} />
      <path d="M70 24 h26 v34 h-10 v-16 h-6 v16 h-10z" fill={C.peacock} {...s} />
      <path d="M120 20 l-2 6 h28 l-2 -6" fill="none" {...s} />
      <rect x={118} y={26} width={28} height={22} rx={3} fill={C.haldi} {...s} />
      <path d="M10 70 H170 M10 110 H170" {...s} />
      {Array.from({ length: 9 }).map((_, i) => (
        <path key={i} d={`M${22 + i * 17} 70 V110`} {...s} />
      ))}
      <circle cx={160} cy={92} r={9} fill={C.leaf} {...s} />
      <path d="M160 83 v-8 M154 78 l6 4 6 -4" fill="none" {...s} />
    </svg>
  );
}
