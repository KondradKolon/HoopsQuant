'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/hooks/useAuth'
import { createClient } from '@/lib/supabase/client'
import { cachedGet } from '@/lib/api'
import Link from 'next/link'
import TeamLogo from '@/components/TeamLogo'
import InfoIcon from '@/components/InfoIcon'
import { getTeam } from '@/lib/teams'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface TeamRanking {
  rank: number
  team: string
  elo: number
  conference: string
  wins: number
  losses: number
  win_pct: number
}

interface TrendPoint {
  date: string
  elo: number
}

interface UpcomingGame {
  game_id: string
  game_date: string
  home_team: string
  away_team: string
  prediction: {
    home_win_prob: number
    away_win_prob: number
    home_elo: number
    away_elo: number
  } | null
}

const CONFERENCES = [
  { key: 'all', label: 'Combined' },
  { key: 'east', label: 'Eastern' },
  { key: 'west', label: 'Western' },
]

export default function EloRankingPage() {
  const { user, loading: authLoading } = useAuth()
  const [teams, setTeams] = useState<TeamRanking[]>([])
  const [conference, setConference] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null)
  const [trend, setTrend] = useState<TrendPoint[]>([])
  const [trendLoading, setTrendLoading] = useState(false)
  const [upcomingGames, setUpcomingGames] = useState<UpcomingGame[]>([])
  const [upcomingLoading, setUpcomingLoading] = useState(true)
  const [detailGame, setDetailGame] = useState<UpcomingGame | null>(null)
  const router = useRouter()
  const supabase = createClient()

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login')
      return
    }
    if (user) {
      fetchRankings()
      fetchUpcoming()
    }
  }, [user, authLoading, router, conference])

  useEffect(() => {
    if (selectedTeam) fetchTrend(selectedTeam)
  }, [selectedTeam])

  const authHeaders = async () => ({
    Authorization: `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`,
  })

  const fetchRankings = async () => {
    try {
      setLoading(true)
      const data = await cachedGet<{ teams: TeamRanking[] }>(`/elo/rankings?conference=${conference}`, {
        headers: await authHeaders(),
        ttlMs: 300_000,
      })
      setTeams(data.teams || [])
      setError(null)
    } catch (err) {
      console.error('Error fetching Elo rankings:', err)
      setError('Failed to load rankings')
    } finally {
      setLoading(false)
    }
  }

  const fetchUpcoming = async () => {
    try {
      setUpcomingLoading(true)
      const data = await cachedGet<{ games: UpcomingGame[] }>('/elo/upcoming', {
        headers: await authHeaders(),
        ttlMs: 60_000,
      })
      setUpcomingGames(data.games || [])
    } catch (err) {
      console.error('Error fetching upcoming:', err)
    } finally {
      setUpcomingLoading(false)
    }
  }

  const fetchTrend = async (team: string) => {
    try {
      setTrendLoading(true)
      const data = await cachedGet<{ points: TrendPoint[] }>(`/elo/trend?team=${team}`, {
        headers: await authHeaders(),
        ttlMs: 300_000,
      })
      setTrend(data.points || [])
    } catch (err) {
      console.error('Error fetching trend:', err)
      setTrend([])
    } finally {
      setTrendLoading(false)
    }
  }

  const handleLogout = async () => {
    await supabase.auth.signOut()
    router.push('/login')
  }

  const toggleTeam = (team: string) => {
    setSelectedTeam(selectedTeam === team ? null : team)
  }

  return (
    <div className="min-h-screen quant-grid">
      <header className="bg-slate-800 border-b border-slate-700 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="flex items-center gap-8">
            <h1 className="text-2xl font-bold text-white">HoopsQuant</h1>
            <nav className="flex gap-6">
              <Link href="/dashboard" className="text-gray-400 hover:text-white font-medium">Dashboard</Link>
              <Link href="/elo-ranking" className="text-emerald-400 font-medium">Elo</Link>
              <Link href="/arbitrage" className="text-gray-400 hover:text-white font-medium">Arbitrage</Link>
              <Link href="/picks" className="text-gray-400 hover:text-white font-medium">My Picks</Link>
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-gray-400">{user?.email}</span>
            <button onClick={handleLogout} className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition">Logout</button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="bg-red-900 border border-red-700 rounded-lg p-4 mb-8 text-red-200">{error}</div>
        )}

        {/* Upcoming Games with Elo Predictions */}
        <div className="mb-10">
          <h2 className="text-2xl font-bold text-white mb-1">Upcoming Games</h2>
          <p className="text-gray-400 text-sm mb-4">Elo-based win probabilities for upcoming matchups</p>
          {upcomingLoading ? (
            <div className="flex gap-4 overflow-x-auto pb-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="min-w-[260px] bg-slate-800 rounded-xl p-5 border border-slate-700 animate-pulse">
                  <div className="h-4 bg-slate-700 rounded w-24 mb-3" />
                  <div className="h-6 bg-slate-700 rounded w-32 mb-2" />
                  <div className="h-6 bg-slate-700 rounded w-28" />
                </div>
              ))}
            </div>
          ) : upcomingGames.length === 0 ? (
            <div className="bg-slate-800/50 rounded-xl p-6 text-center border border-slate-700">
              <p className="text-gray-500">No upcoming games found</p>
            </div>
          ) : (
            <div className="flex gap-4 overflow-x-auto pb-2">
              {upcomingGames.map((g) => (
                <button
                  key={g.game_id}
                  onClick={() => setDetailGame(g)}
                  className="min-w-[280px] bg-slate-800 rounded-xl p-5 border border-slate-700 hover:border-emerald-500 transition flex-shrink-0 text-left focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <div className="text-xs text-gray-500 mb-3">{g.game_date}</div>
                  <div className="flex justify-between items-center mb-4">
                    <TeamLogo abbr={g.home_team} size="md" showName="abbr" layout="vertical" />
                    <span className="text-gray-500 text-sm font-mono">vs</span>
                    <TeamLogo abbr={g.away_team} size="md" showName="abbr" layout="vertical" />
                  </div>
                  {g.prediction ? (
                    <div className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-400">{getTeam(g.home_team).shortName}</span>
                        <span className="text-emerald-400 font-semibold">{(g.prediction.home_win_prob * 100).toFixed(0)}%</span>
                      </div>
                      <div className="w-full bg-slate-700 rounded-full h-1.5">
                        <div
                          className="bg-emerald-500 h-1.5 rounded-full"
                          style={{ width: `${g.prediction.home_win_prob * 100}%` }}
                        />
                      </div>
                      <div className="flex justify-between text-xs text-gray-500 mt-1">
                        <span>Elo: {g.prediction.home_elo.toFixed(0)}</span>
                        <span>Elo: {g.prediction.away_elo.toFixed(0)}</span>
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs text-gray-500">No prediction available</div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Elo Rankings Table */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">Elo Rankings</h2>
            <p className="text-gray-400 text-sm">Click a team to see their Elo trend over the season</p>
          </div>
          <div className="flex gap-2">
            {CONFERENCES.map((c) => (
              <button
                key={c.key}
                onClick={() => setConference(c.key)}
                className={`px-4 py-1.5 rounded-lg text-sm font-semibold transition ${
                  conference === c.key
                    ? 'bg-emerald-600 text-white'
                    : 'bg-slate-800 text-gray-400 hover:text-white border border-slate-700'
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500" />
          </div>
        ) : teams.length === 0 ? (
          <div className="bg-slate-800 rounded-lg p-8 text-center border border-slate-700">
            <p className="text-gray-400 text-lg">No rankings available yet</p>
            <p className="text-gray-500 text-sm mt-2">Completed games are needed to compute Elo ratings</p>
          </div>
        ) : (
          <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
            <table className="w-full">
              <thead className="border-b border-slate-700 bg-slate-700">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-300 w-16">Rank</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-300">Team</th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-300">Elo</th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-300">Record</th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-300">Win %</th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-gray-300 w-20" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {teams.map((t) => (
                  <>
                    <tr
                      key={t.team}
                      onClick={() => toggleTeam(t.team)}
                      className="hover:bg-slate-700 transition cursor-pointer"
                    >
                      <td className="px-6 py-4">
                        <span className={`text-lg font-bold ${t.rank <= 3 ? 'text-emerald-400' : 'text-gray-400'}`}>
                          #{t.rank}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <TeamLogo abbr={t.team} size="sm" showName="full" />
                          <span className={`text-xs uppercase px-2 py-0.5 rounded-full ${
                            t.conference === 'east'
                              ? 'bg-blue-900/40 text-blue-400'
                              : 'bg-orange-900/40 text-orange-400'
                          }`}>
                            {t.conference === 'east' ? 'East' : 'West'}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className="text-emerald-400 font-bold text-lg">{t.elo.toFixed(1)}</span>
                      </td>
                      <td className="px-6 py-4 text-right text-gray-300 font-semibold">
                        {t.wins}-{t.losses}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className="text-gray-300 font-semibold">{(t.win_pct * 100).toFixed(1)}%</span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className={`text-xs transition ${selectedTeam === t.team ? 'text-emerald-400' : 'text-gray-600'}`}>
                          {selectedTeam === t.team ? '▲' : '▼'}
                        </span>
                      </td>
                    </tr>
                    {selectedTeam === t.team && (
                      <tr key={`${t.team}-trend`}>
                        <td colSpan={6} className="px-6 py-6 bg-slate-900/50">
                          <div className="mb-4">
                            <h3 className="text-white font-semibold mb-1">{getTeam(t.team).fullName} — Elo Trend</h3>
                            <p className="text-gray-500 text-xs">Season {conference === 'all' ? '2025-26' : `${conference === 'east' ? 'Eastern' : 'Western'} Conference`}</p>
                          </div>
                          {trendLoading ? (
                            <div className="h-[200px] flex items-center justify-center">
                              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500" />
                            </div>
                          ) : trend.length === 0 ? (
                            <p className="text-gray-500 text-sm text-center py-8">No trend data available</p>
                          ) : (
                            <div className="h-[220px]">
                              <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={trend} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                                  <XAxis
                                    dataKey="date"
                                    tick={{ fill: '#94a3b8', fontSize: 11 }}
                                    tickLine={false}
                                    axisLine={{ stroke: '#334155' }}
                                    interval="preserveStartEnd"
                                  />
                                  <YAxis
                                    domain={['auto', 'auto']}
                                    tick={{ fill: '#94a3b8', fontSize: 11 }}
                                    tickLine={false}
                                    axisLine={{ stroke: '#334155' }}
                                    width={60}
                                  />
                                  <Tooltip
                                    contentStyle={{
                                      backgroundColor: '#0f1626',
                                      border: '1px solid #1a263b',
                                      borderRadius: '8px',
                                      color: '#e8eef7',
                                      fontSize: '12px',
                                    }}
                                    labelStyle={{ color: '#9fb1c6' }}
                                  />
                                  <Line
                                    type="monotone"
                                    dataKey="elo"
                                    stroke="#47f3a3"
                                    strokeWidth={2}
                                    dot={{ fill: '#47f3a3', r: 3 }}
                                    activeDot={{ r: 5, fill: '#47f3a3' }}
                                  />
                                </LineChart>
                              </ResponsiveContainer>
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      {detailGame && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="quant-panel rounded-2xl w-full max-w-md p-6 space-y-6">
            <div className="flex justify-between items-start gap-4">
              <div className="text-sm text-gray-500">{detailGame.game_date}</div>
              <button
                onClick={() => setDetailGame(null)}
                className="text-gray-500 hover:text-white text-xl leading-none"
                aria-label="Close"
              >
                &times;
              </button>
            </div>

            <div className="flex items-center justify-between gap-4">
              <TeamLogo abbr={detailGame.home_team} size="xl" showName="full" subtitle="Home" layout="vertical" />
              <div className="text-gray-500 font-bold text-mono">vs</div>
              <TeamLogo abbr={detailGame.away_team} size="xl" showName="full" subtitle="Away" layout="vertical" />
            </div>

            {detailGame.prediction ? (
              <>
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-gray-300 font-semibold">Elo Win Probability</span>
                    <InfoIcon title="Probability computed from current Elo ratings + home court advantage (50 Elo points)." />
                  </div>
                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-white">{getTeam(detailGame.home_team).shortName}</span>
                        <span className="text-emerald-400 font-bold">{(detailGame.prediction.home_win_prob * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-slate-700 rounded-full h-2">
                        <div className="bg-emerald-500 h-2 rounded-full" style={{ width: `${detailGame.prediction.home_win_prob * 100}%` }} />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-white">{getTeam(detailGame.away_team).shortName}</span>
                        <span className="text-emerald-400 font-bold">{(detailGame.prediction.away_win_prob * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-slate-700 rounded-full h-2">
                        <div className="bg-red-500/60 h-2 rounded-full" style={{ width: `${detailGame.prediction.away_win_prob * 100}%` }} />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 border-t border-slate-700 pt-4">
                  <div className="bg-slate-800/60 rounded-lg p-3">
                    <div className="text-xs text-gray-500 mb-1">{getTeam(detailGame.home_team).shortName} Elo</div>
                    <div className="text-emerald-400 font-bold text-xl">{detailGame.prediction.home_elo.toFixed(0)}</div>
                  </div>
                  <div className="bg-slate-800/60 rounded-lg p-3">
                    <div className="text-xs text-gray-500 mb-1">{getTeam(detailGame.away_team).shortName} Elo</div>
                    <div className="text-emerald-400 font-bold text-xl">{detailGame.prediction.away_elo.toFixed(0)}</div>
                  </div>
                </div>
              </>
            ) : (
              <p className="text-center text-gray-500 py-6">No prediction data available for this matchup.</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
