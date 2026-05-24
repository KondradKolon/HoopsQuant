'use client'

import { useState } from 'react'
import { getTeam } from '@/lib/teams'

interface TeamLogoProps {
  abbr: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
  showName?: 'none' | 'short' | 'full' | 'abbr'
  layout?: 'horizontal' | 'vertical'
  subtitle?: string
  className?: string
}

const SIZE_PX: Record<NonNullable<TeamLogoProps['size']>, number> = {
  sm: 24,
  md: 36,
  lg: 56,
  xl: 80,
}

export default function TeamLogo({
  abbr,
  size = 'md',
  showName = 'short',
  layout = 'horizontal',
  subtitle,
  className = '',
}: TeamLogoProps) {
  const team = getTeam(abbr)
  const [imgFailed, setImgFailed] = useState(false)
  const px = SIZE_PX[size]

  const labelText =
    showName === 'full' ? team.fullName :
    showName === 'short' ? team.shortName :
    showName === 'abbr' ? team.abbr :
    null

  const logo = team.logoUrl && !imgFailed ? (
    <img
      src={team.logoUrl}
      alt={`${team.fullName} logo`}
      width={px}
      height={px}
      onError={() => setImgFailed(true)}
      style={{ width: px, height: px }}
      className="object-contain flex-shrink-0"
    />
  ) : (
    <div
      style={{ width: px, height: px }}
      className="flex items-center justify-center rounded-full bg-slate-700 text-slate-300 text-xs font-bold flex-shrink-0"
    >
      {team.abbr.slice(0, 3)}
    </div>
  )

  if (layout === 'vertical') {
    return (
      <div className={`flex flex-col items-center gap-2 ${className}`}>
        {logo}
        {labelText && (
          <div className="text-center">
            <div className="text-white font-bold leading-tight">{labelText}</div>
            {subtitle && <div className="text-xs text-gray-400 mt-0.5">{subtitle}</div>}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className={`flex items-center gap-3 min-w-0 ${className}`}>
      {logo}
      {labelText && (
        <div className="min-w-0">
          <div className="text-white font-semibold truncate">{labelText}</div>
          {subtitle && <div className="text-xs text-gray-400">{subtitle}</div>}
        </div>
      )}
    </div>
  )
}
