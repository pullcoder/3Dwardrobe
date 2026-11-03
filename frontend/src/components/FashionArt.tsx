export function FashionArt({
  kind = "hero",
}: {
  kind?: "hero" | "body" | "garment";
}) {
  return (
    <svg
      className={`fashion-art ${kind}`}
      viewBox="0 0 400 430"
      role="img"
      aria-label={
        kind === "body"
          ? "마네킹 화면을 위한 컨셉 일러스트, 실제 3D 모델 아님"
          : "셔츠와 바지의 스타일 컨셉 일러스트"
      }
    >
      <defs>
        <linearGradient id={`fabric-${kind}`} x1="0" x2="1" y2="1">
          <stop stopColor="#fffdfa" />
          <stop offset="1" stopColor="#ddd3c3" />
        </linearGradient>
        <linearGradient id={`pants-${kind}`} x1="0" x2="1">
          <stop stopColor="#4d5160" />
          <stop offset="1" stopColor="#292d38" />
        </linearGradient>
      </defs>
      <ellipse
        cx="200"
        cy="397"
        rx="120"
        ry="14"
        fill="#302353"
        opacity=".09"
      />
      <path
        d="M172 219 L224 219 L241 378 L207 380 L195 285 L182 380 L149 377 Z"
        fill={`url(#pants-${kind})`}
      />
      <path
        d="M190 237 L195 285 M164 250 L179 258 M224 250 L210 258"
        stroke="#8b8d98"
        strokeWidth="1.2"
        fill="none"
      />
      <path
        d="M169 78 L143 90 L98 172 L127 189 L156 143 L151 245 Q195 256 238 245 L233 143 L261 189 L290 172 L246 90 L219 78 Z"
        fill={`url(#fabric-${kind})`}
        stroke="#c8bdac"
        strokeWidth="1.5"
      />
      <path
        d="M169 78 L193 98 L181 117 L160 86 M219 78 L193 98 L207 117 L230 86 M193 100 L193 249"
        fill="none"
        stroke="#bfb3a2"
        strokeWidth="1.5"
      />
      <path
        d="M207 130 L229 130 L229 153 Q218 162 207 153 Z"
        stroke="#c3b7a6"
        fill="none"
      />
      {[126, 153, 180, 207, 233].map((cy) => (
        <circle key={cy} cx="198" cy={cy} r="2" fill="#a69987" />
      ))}
      <path
        d="M151 219 Q171 224 184 220 M210 233 L235 230 M142 163 L153 151 M237 154 L248 174"
        stroke="#d2c7b7"
        fill="none"
      />
      {kind === "body" ? (
        <>
          <ellipse cx="194" cy="49" rx="23" ry="28" fill="#c9bbae" />
          <path d="M183 73 L183 83 L194 96 L207 83 L207 73" fill="#c9bbae" />
        </>
      ) : (
        <>
          <path
            d="M177 64 Q194 43 212 64"
            stroke="#6d5f80"
            fill="none"
            strokeWidth="2"
          />
          <path
            d="M194 52 L194 38 Q207 29 194 23"
            stroke="#6d5f80"
            fill="none"
            strokeWidth="2"
          />
        </>
      )}
    </svg>
  );
}
