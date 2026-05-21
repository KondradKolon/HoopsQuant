'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/hooks/useAuth'
import { createClient } from '@/lib/supabase/client'
import apiClient from '@/lib/api'
import Link from 'next/link'

interface Prediction {
  home_win_prob: number
  away_win_prob: number
  confidence: number
  min_home_odds_decimal: number
  min_away_odds_decimal: number
  min_home_odds_american: number
  min_away_odds_american: number
}

interface Game {
  game_id: string
  home_team: string
  away_team: string
  game_date: string
  prediction?: Prediction
  best_odds?: { home: number; away: number }
}

interface BetRating {
  tier: 'elite' | 'great' | 'decent' | 'risky' | 'pass'
  label: string
  color: string
  barColor: string
  bgColor: string
  explanation: string
}

function rateBet(prob: number, minOdds: number, bestOdds: number | null): BetRating {
  if (!bestOdds) return {
    tier: 'pass', label: 'N/A', color: 'text-gray-500', barColor: 'bg-gray-600', bgColor: 'bg-gray-800/50',
    explanation: 'No odds available to evaluate this bet.',
  }

  const ev = prob * bestOdds - 1
  const b = bestOdds - 1
  const kelly = ev > 0 ? (prob * b - (1 - prob)) / b : 0

  if (ev <= 0 || prob < 0.5) return {
    tier: 'pass', label: 'PASS', color: 'text-red-400', barColor: 'bg-red-500', bgColor: 'bg-red-900/30',
    explanation: 'Negative expected value or below 50% probability. Stay away.',
  }
  if (prob >= 0.65 && ev >= 0.05 && kelly >= 0.02) return {
    tier: 'elite', label: 'ELITE', color: 'text-emerald-300', barColor: 'bg-emerald-400', bgColor: 'bg-emerald-900/40',
    explanation: 'High confidence with strong expected value. Top-tier opportunity.',
  }
  if (prob >= 0.60 && ev >= 0.02 && kelly >= 0.01) return {
    tier: 'great', label: 'GREAT', color: 'text-emerald-400', barColor: 'bg-emerald-500', bgColor: 'bg-emerald-900/30',
    explanation: 'Good confidence and solid positive EV. Smart bet.',
  }
  if (prob >= 0.55 && ev > 0) return {
    tier: 'decent', label: 'DECENT', color: 'text-yellow-400', barColor: 'bg-yellow-500', bgColor: 'bg-yellow-900/30',
    explanation: 'Moderate edge. Worth a small bet if you like the matchup.',
  }
  return {
    tier: 'risky', label: 'RISKY', color: 'text-orange-400', barColor: 'bg-orange-500', bgColor: 'bg-orange-900/30',
    explanation: 'Low confidence or thin edge. Only for high-risk tolerance.',
  }
}

function computeEv(prob: number, odds: number | null): number | null {
  if (!odds) return null
  return prob * odds - 1
}

function computeKelly(prob: number, odds: number | null): number | null {
  if (!odds || odds <= 1) return null
  const ev = computeEv(prob, odds)
  if (!ev || ev <= 0) return null
  return (prob * (odds - 1) - (1 - prob)) / (odds - 1)
}

export default function DashboardPage() {
  const { user, loading: authLoading } = useAuth()
  const [games, setGames] = useState<Game[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [detailGame, setDetailGame] = useState<Game | null>(null)
  const [pickTeam, setPickTeam] = useState<string>('')
  const [pickStake, setPickStake] = useState(100)
  const [pickSaving, setPickSaving] = useState(false)
  const [pickMessage, setPickMessage] = useState<string | null>(null)
  const router = useRouter()
  const supabase = createClient()

  useEffect(() => {
    if (!authLoading && !user) { router.push('/login'); return }
    if (user) fetchUpcomingGames()
  }, [user, authLoading, router])

  useEffect(() => {
    if (detailGame) {
      setPickTeam('')
      setPickStake(100)
      setPickMessage(null)
    }
  }, [detailGame])

  const authHeaders = async () => ({
    Authorization: `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`,
  })

  const fetchUpcomingGames = async () => {
    try {
      setLoading(true)
      const response = await apiClient.get('/dashboard/games/upcoming', { headers: await authHeaders() })
      setGames(Array.isArray(response.data) ? response.data : response.data.games || [])
      setError(null)
    } catch { setError('Failed to load games') }
    finally { setLoading(false) }
  }

  const savePick = async () => {
    if (!detailGame || !pickTeam) return
    setPickSaving(true)
    setPickMessage(null)
    try {
      const pred = detailGame.prediction
      const isHome = pickTeam === detailGame.home_team
      const odds = isHome ? detailGame.best_odds?.home : detailGame.best_odds?.away
      await apiClient.post('/dashboard/picks', {
        game_id: detailGame.game_id,
        pick_team: pickTeam,
        odds: odds || 2.0,
        stake: pickStake,
        pick_type: 'moneyline',
      }, { headers: await authHeaders() })
      setPickMessage('Pick saved! Track it under My Picks.')
    } catch { setPickMessage('Failed to save pick. Try again.') }
    finally { setPickSaving(false) }
  }

  const handleLogout = async () => {
    await supabase.auth.signOut()
    router.push('/login')
  }

  if (authLoading || (user && loading)) {
    return (
      <div className="flex items-center justify-center min-h-screen quant-grid">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500 mx-auto mb-4" />
          <p className="text-gray-400">Loading your dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen quant-grid">
      <header className="bg-slate-800 border-b border-slate-700 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="flex items-center gap-8">
            <h1 className="text-2xl font-bold text-white">HoopsQuant</h1>
            <nav className="flex gap-6">
              <Link href="/dashboard" className="text-emerald-400 font-medium">Dashboard</Link>
              <Link href="/elo-ranking" className="text-gray-400 hover:text-white font-medium">Elo</Link>
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
        <div className="mb-8">
          <h2 className="text-4xl font-bold text-white mb-2">Today's Picks</h2>
          <p className="text-gray-400">AI-powered predictions with confidence scores and bet ratings</p>
        </div>

        {error && <div className="bg-red-900 border border-red-700 rounded-lg p-4 mb-8 text-red-200">{error}</div>}

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500" />
          </div>
        ) : games.length === 0 ? (
          <div className="bg-slate-800 rounded-lg p-8 text-center border border-slate-700">
            <p className="text-gray-400 text-lg">No upcoming games at the moment</p>
          </div>
        ) : (
          <div className="grid gap-6">
            {games.map((game) => {
              const homeRate = game.prediction ? rateBet(game.prediction.home_win_prob, game.prediction.min_home_odds_decimal, game.best_odds?.home ?? null) : null
              const awayRate = game.prediction ? rateBet(game.prediction.away_win_prob, game.prediction.min_away_odds_decimal, game.best_odds?.away ?? null) : null
              return (
                <div key={game.game_id} className="bg-slate-800 rounded-lg border border-slate-700 p-6 hover:border-emerald-500 transition">
                  <div className="flex flex-wrap justify-between items-start gap-4 mb-4">
                    <div className="flex items-center gap-4">
                      <div className="text-center">
                        <div className="text-3xl font-bold text-white">{game.home_team}</div>
                        <div className="text-sm text-gray-400">Home</div>
                      </div>
                      <div className="text-gray-500 font-bold">vs</div>
                      <div className="text-center">
                        <div className="text-3xl font-bold text-white">{game.away_team}</div>
                        <div className="text-sm text-gray-400">Away</div>
                      </div>
                    </div>

                    {game.prediction && (
                      <div className="flex gap-3 items-start">
                        <div className={`px-3 py-1 rounded-lg text-xs font-bold uppercase ${homeRate?.bgColor} ${homeRate?.color}`}>
                          {game.home_team}: {homeRate?.label}
                        </div>
                        <div className={`px-3 py-1 rounded-lg text-xs font-bold uppercase ${awayRate?.bgColor} ${awayRate?.color}`}>
                          {game.away_team}: {awayRate?.label}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="border-t border-slate-700 pt-4 grid md:grid-cols-3 gap-4">
                    <div>
                      <div className="text-sm text-gray-400">Game Date</div>
                      <div className="text-white font-semibold">
                        {new Date(game.game_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>

                    {game.best_odds && game.best_odds.home && (
                      <div>
                        <div className="text-sm text-gray-400">Best Odds</div>
                        <div className="flex gap-3">
                          <span className="text-green-400 font-semibold">{game.best_odds.home.toFixed(2)}x</span>
                          <span className="text-red-400 font-semibold">{game.best_odds.away.toFixed(2)}x</span>
                        </div>
                      </div>
                    )}

                    {game.prediction && (
                      <div>
                        <div className="text-sm text-gray-400">Model Confidence</div>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-slate-700 rounded-full h-2">
                            <div className="bg-emerald-500 h-2 rounded-full" style={{ width: `${game.prediction.confidence * 100}%` }} />
                          </div>
                          <span className="text-white font-semibold text-sm">{(game.prediction.confidence * 100).toFixed(0)}%</span>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="mt-4 flex gap-2">
                    <button
                      onClick={() => setDetailGame(game)}
                      className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white py-2 rounded-lg transition font-semibold"
                    >
                      View Details
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </main>

      {/* Detail Modal */}
      {detailGame && detailGame.prediction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="quant-panel rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6 space-y-6">
            {/* Header */}
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-xl font-bold text-white">{detailGame.home_team} vs {detailGame.away_team}</h3>
                <p className="text-sm text-gray-500">
                  {new Date(detailGame.game_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
              <button onClick={() => setDetailGame(null)} className="text-gray-500 hover:text-white text-xl leading-none">&times;</button>
            </div>

            {/* Win Probability */}
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-300 font-semibold">Win Probability</span>
                <span className="text-gray-500 text-xs cursor-help" title="Model's estimated chance each team wins. Not a guarantee — it's a probability, not a prediction.">ⓘ</span>
              </div>
              <div className="space-y-2">
                <div>
                  <div className="flex justify-between text-xs mb-0.5">
                    <span className="text-white">{detailGame.home_team}</span>
                    <span className="text-emerald-400 font-bold">{(detailGame.prediction.home_win_prob * 100).toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-2">
                    <div className="bg-emerald-500 h-2 rounded-full" style={{ width: `${detailGame.prediction.home_win_prob * 100}%` }} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-xs mb-0.5">
                    <span className="text-white">{detailGame.away_team}</span>
                    <span className="text-emerald-400 font-bold">{(detailGame.prediction.away_win_prob * 100).toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-2">
                    <div className="bg-red-500/60 h-2 rounded-full" style={{ width: `${detailGame.prediction.away_win_prob * 100}%` }} />
                  </div>
                </div>
              </div>
              <p className="text-xs text-gray-500 mt-1">Model's estimated chance each team wins. Not a guarantee.</p>
            </div>

            {/* Confidence */}
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-300 font-semibold">Confidence Score</span>
                <span className="text-gray-500 text-xs cursor-help" title="How often the model is correct when predicting at this confidence level. 65% → right ~65 out of 100 times.">ⓘ</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex-1 bg-slate-700 rounded-full h-3">
                  <div className="bg-emerald-500 h-3 rounded-full" style={{ width: `${detailGame.prediction.confidence * 100}%` }} />
                </div>
                <span className="text-white font-bold text-lg">{(detailGame.prediction.confidence * 100).toFixed(0)}%</span>
              </div>
              <p className="text-xs text-gray-500 mt-1">Higher confidence means the model has stronger signals (wider Elo gap, clearer form difference).</p>
            </div>

            {/* Team Breakdown */}
            {[detailGame.home_team, detailGame.away_team].map((team) => {
              const isHome = team === detailGame.home_team
              const prob = isHome ? detailGame.prediction!.home_win_prob : detailGame.prediction!.away_win_prob
              const minOdds = isHome ? detailGame.prediction!.min_home_odds_decimal : detailGame.prediction!.min_away_odds_decimal
              const bestOdds = isHome ? (detailGame.best_odds?.home ?? null) : (detailGame.best_odds?.away ?? null)
              const rating = rateBet(prob, minOdds, bestOdds)
              const ev = computeEv(prob, bestOdds)
              const kelly = computeKelly(prob, bestOdds)

              return (
                <div key={team} className={`rounded-xl p-4 border ${rating.bgColor} border-slate-700`}>
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-white font-bold">{team}</h4>
                    <span className={`px-3 py-0.5 rounded-full text-xs font-bold uppercase ${rating.bgColor} ${rating.color}`}>
                      {rating.label}
                    </span>
                  </div>

                  {/* Bet Meter */}
                  <div className="mb-3">
                    <div className="flex justify-between text-xs text-gray-400 mb-1">
                      <span>Bet Meter</span>
                      <span className={rating.color}>{rating.label}</span>
                    </div>
                    <div className="w-full bg-slate-700 rounded-full h-2.5">
                      <div className={`${rating.barColor} h-2.5 rounded-full transition-all duration-500`}
                        style={{
                          width: rating.tier === 'elite' ? '100%' : rating.tier === 'great' ? '75%' : rating.tier === 'decent' ? '50%' : rating.tier === 'risky' ? '30%' : '10%',
                        }} />
                    </div>
                    <div className="flex justify-between text-[10px] text-gray-600 mt-0.5">
                      <span>Pass</span>
                      <span>Decent</span>
                      <span>Elite</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-3 text-sm">
                    <div>
                      <div className="text-gray-500 text-xs">Win Prob</div>
                      <div className="text-white font-semibold">{(prob * 100).toFixed(1)}%</div>
                    </div>
                    <div>
                      <div className="text-gray-500 text-xs">+EV at</div>
                      <div className="text-emerald-400 font-semibold">&gt; {minOdds}x</div>
                    </div>
                    <div>
                      <div className="text-gray-500 text-xs">Best Odds</div>
                      <div className={bestOdds && ev && ev > 0 ? 'text-green-400 font-semibold' : 'text-gray-400 font-semibold'}>
                        {bestOdds ? `${bestOdds.toFixed(2)}x` : '—'}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-500 text-xs">EV</div>
                      <div className={ev && ev > 0 ? 'text-green-400 font-bold' : 'text-red-400 font-bold'}>
                        {ev !== null ? `${(ev * 100).toFixed(2)}%` : '—'}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-500 text-xs">Kelly Stake</div>
                      <div className="text-white font-semibold">{kelly !== null ? `${(kelly * 100).toFixed(1)}%` : '0%'}</div>
                    </div>
                    <div>
                      <div className="text-gray-500 text-xs">Per $100</div>
                      <div className={ev && ev > 0 ? 'text-green-400 font-semibold' : 'text-gray-500'}>
                        {ev !== null ? `${ev >= 0 ? '+' : ''}$${(ev * 100).toFixed(2)}` : '—'}
                      </div>
                    </div>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">{rating.explanation}</p>
                  <p className="text-[10px] text-gray-600 mt-1">
                    ⓘ EV (Expected Value) = average profit per bet. Positive = profitable long-term.
                    Kelly = recommended % of bankroll to bet based on edge size.
                  </p>
                </div>
              )
            })}

            {/* Place Pick */}
            <div className="border-t border-slate-700 pt-4">
              <h4 className="text-white font-semibold mb-3">Place a Pick</h4>
              <div className="flex gap-3 mb-3">
                <select
                  value={pickTeam}
                  onChange={(e) => setPickTeam(e.target.value)}
                  className="flex-1 bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm"
                >
                  <option value="">Select team...</option>
                  <option value={detailGame.home_team}>{detailGame.home_team} (Home)</option>
                  <option value={detailGame.away_team}>{detailGame.away_team} (Away)</option>
                </select>
                <input
                  type="number"
                  value={pickStake}
                  onChange={(e) => setPickStake(Number(e.target.value))}
                  className="w-24 bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm text-right"
                  placeholder="Stake $"
                  min={1}
                />
              </div>

              {pickTeam && detailGame.prediction && (
                <div className="bg-slate-700/50 rounded-lg p-3 mb-3 text-sm">
                  <div className="flex justify-between text-gray-300">
                    <span>Stake</span>
                    <span className="text-white font-semibold">${pickStake}</span>
                  </div>
                  <div className="flex justify-between text-gray-300">
                    <span>To Win</span>
                    <span className="text-green-400 font-semibold">
                      +${(pickStake * ((detailGame.best_odds?.home && pickTeam === detailGame.home_team ? detailGame.best_odds.home : detailGame.best_odds?.away || 2.0) - 1)).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between text-gray-300">
                    <span>Total Payout</span>
                    <span className="text-white font-semibold">
                      ${(pickStake * (detailGame.best_odds?.home && pickTeam === detailGame.home_team ? detailGame.best_odds.home : detailGame.best_odds?.away || 2.0)).toFixed(2)}
                    </span>
                  </div>
                </div>
              )}

              {pickMessage && (
                <div className={`text-sm mb-3 ${pickMessage.includes('saved') ? 'text-emerald-400' : 'text-red-400'}`}>
                  {pickMessage}
                </div>
              )}

              <button
                onClick={savePick}
                disabled={!pickTeam || pickSaving}
                className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white py-3 rounded-lg font-semibold transition"
              >
                {pickSaving ? 'Saving...' : 'Place Pick'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
