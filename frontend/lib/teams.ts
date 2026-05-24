/**
 * NBA team metadata: abbreviation → full name + NBA.com CDN team ID for logos.
 * Logo URL format: https://cdn.nba.com/logos/nba/{teamId}/global/L/logo.svg
 */

export interface TeamInfo {
  abbr: string
  fullName: string
  shortName: string
  teamId: string
  logoUrl: string
}

const TEAM_META: Record<string, { fullName: string; shortName: string; teamId: string }> = {
  ATL: { fullName: 'Atlanta Hawks', shortName: 'Hawks', teamId: '1610612737' },
  BOS: { fullName: 'Boston Celtics', shortName: 'Celtics', teamId: '1610612738' },
  BKN: { fullName: 'Brooklyn Nets', shortName: 'Nets', teamId: '1610612751' },
  CHA: { fullName: 'Charlotte Hornets', shortName: 'Hornets', teamId: '1610612766' },
  CHI: { fullName: 'Chicago Bulls', shortName: 'Bulls', teamId: '1610612741' },
  CLE: { fullName: 'Cleveland Cavaliers', shortName: 'Cavaliers', teamId: '1610612739' },
  DAL: { fullName: 'Dallas Mavericks', shortName: 'Mavericks', teamId: '1610612742' },
  DEN: { fullName: 'Denver Nuggets', shortName: 'Nuggets', teamId: '1610612743' },
  DET: { fullName: 'Detroit Pistons', shortName: 'Pistons', teamId: '1610612765' },
  GSW: { fullName: 'Golden State Warriors', shortName: 'Warriors', teamId: '1610612744' },
  HOU: { fullName: 'Houston Rockets', shortName: 'Rockets', teamId: '1610612745' },
  IND: { fullName: 'Indiana Pacers', shortName: 'Pacers', teamId: '1610612754' },
  LAC: { fullName: 'LA Clippers', shortName: 'Clippers', teamId: '1610612746' },
  LAL: { fullName: 'Los Angeles Lakers', shortName: 'Lakers', teamId: '1610612747' },
  MEM: { fullName: 'Memphis Grizzlies', shortName: 'Grizzlies', teamId: '1610612763' },
  MIA: { fullName: 'Miami Heat', shortName: 'Heat', teamId: '1610612748' },
  MIL: { fullName: 'Milwaukee Bucks', shortName: 'Bucks', teamId: '1610612749' },
  MIN: { fullName: 'Minnesota Timberwolves', shortName: 'Timberwolves', teamId: '1610612750' },
  NOP: { fullName: 'New Orleans Pelicans', shortName: 'Pelicans', teamId: '1610612740' },
  NYK: { fullName: 'New York Knicks', shortName: 'Knicks', teamId: '1610612752' },
  OKC: { fullName: 'Oklahoma City Thunder', shortName: 'Thunder', teamId: '1610612760' },
  ORL: { fullName: 'Orlando Magic', shortName: 'Magic', teamId: '1610612753' },
  PHI: { fullName: 'Philadelphia 76ers', shortName: '76ers', teamId: '1610612755' },
  PHX: { fullName: 'Phoenix Suns', shortName: 'Suns', teamId: '1610612756' },
  POR: { fullName: 'Portland Trail Blazers', shortName: 'Trail Blazers', teamId: '1610612757' },
  SAC: { fullName: 'Sacramento Kings', shortName: 'Kings', teamId: '1610612758' },
  SAS: { fullName: 'San Antonio Spurs', shortName: 'Spurs', teamId: '1610612759' },
  TOR: { fullName: 'Toronto Raptors', shortName: 'Raptors', teamId: '1610612761' },
  UTA: { fullName: 'Utah Jazz', shortName: 'Jazz', teamId: '1610612762' },
  WAS: { fullName: 'Washington Wizards', shortName: 'Wizards', teamId: '1610612764' },
}

// Aliases for prod data quirks (truncated names from broken odds pipeline).
const NAME_ALIASES: Record<string, string> = {
  'CLEVELAND': 'CLE',
  'NEW YORK K': 'NYK',
  'NEW YORK': 'NYK',
  'SAN ANTONI': 'SAS',
  'SAN ANTONIO': 'SAS',
  'OKLAHOMA C': 'OKC',
  'OKLAHOMA': 'OKC',
  'LOS ANGELE': 'LAL',
  'LA': 'LAC',
  'GOLDEN STA': 'GSW',
  'PORTLAND': 'POR',
  'PORTLAND T': 'POR',
  'PHILADELPH': 'PHI',
  'MINNESOTA': 'MIN',
  'WASHINGTON': 'WAS',
  'BROOKLYN': 'BKN',
  'CHARLOTTE': 'CHA',
  'INDIANA': 'IND',
  'MEMPHIS': 'MEM',
  'SACRAMENTO': 'SAC',
  'NEW ORLEAN': 'NOP',
  'MILWAUKEE': 'MIL',
}

function normalize(raw: string): string {
  return (raw || '').trim().toUpperCase()
}

/**
 * Resolve a team identifier (clean abbr, truncated name, or full name).
 * Returns TeamInfo with logo URL. Falls back to a placeholder when unknown.
 */
export function getTeam(raw: string): TeamInfo {
  const key = normalize(raw)
  const direct = TEAM_META[key]
  if (direct) {
    return {
      abbr: key,
      fullName: direct.fullName,
      shortName: direct.shortName,
      teamId: direct.teamId,
      logoUrl: `https://cdn.nba.com/logos/nba/${direct.teamId}/global/L/logo.svg`,
    }
  }
  const aliasAbbr = NAME_ALIASES[key]
  if (aliasAbbr && TEAM_META[aliasAbbr]) {
    const meta = TEAM_META[aliasAbbr]
    return {
      abbr: aliasAbbr,
      fullName: meta.fullName,
      shortName: meta.shortName,
      teamId: meta.teamId,
      logoUrl: `https://cdn.nba.com/logos/nba/${meta.teamId}/global/L/logo.svg`,
    }
  }
  return {
    abbr: key.slice(0, 3) || '???',
    fullName: raw || 'Unknown Team',
    shortName: raw || 'Unknown',
    teamId: '',
    logoUrl: '',
  }
}
