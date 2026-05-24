interface InfoIconProps {
  title?: string
  className?: string
  size?: number
}

export default function InfoIcon({ title, className = 'text-slate-500 hover:text-slate-300 transition', size = 14 }: InfoIconProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      width={size}
      height={size}
      className={`inline-block cursor-help ${className}`}
      role="img"
      aria-label={title || 'Information'}
    >
      {title && <title>{title}</title>}
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  )
}
