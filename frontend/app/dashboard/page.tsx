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
  home_score?: number
  away_score?: number
  prediction?: Prediction
  best_odds?: {
    home: number
    away: number
  }
}

export default function DashboardPage() {
  const { user, loading: authLoading } = useAuth()
  const [games, setGames] = useState<Game[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()
  const supabase = createClient()

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login')
      return
    }

    if (user) {
      fetchUpcomingGames()
    }
  }, [user, authLoading, router])

  const fetchUpcomingGames = async () => {
    try {
      setLoading(true)
      const response = await apiClient.get('/dashboard/games/upcoming', {
        headers: {
          Authorization: `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`,
        },
      })
      setGames(Array.isArray(response.data) ? response.data : response.data.games || [])
      setError(null)
    } catch (err) {
      console.error('Error fetching games:', err)
      setError('Failed to load games')
    } finally {
      setLoading(false)
    }
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
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="flex items-center gap-8">
            <h1 className="text-2xl font-bold text-white">HoopsQuant</h1>
            <nav className="flex gap-6">
              <Link href="/dashboard" className="text-emerald-400 font-medium">
                Dashboard
              </Link>
              <Link href="/elo-ranking" className="text-gray-400 hover:text-white font-medium">
                Elo
              </Link>
              <Link href="/arbitrage" className="text-gray-400 hover:text-white font-medium">
                Arbitrage
              </Link>
              <Link href="/picks" className="text-gray-400 hover:text-white font-medium">
                My Picks
              </Link>
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-gray-400">{user?.email}</span>
            <button
              onClick={handleLogout}
              className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Hero Section */}
        <div className="mb-12">
          <h2 className="text-4xl font-bold text-white mb-2">Today's Picks</h2>
          <p className="text-gray-400">AI-powered predictions with confidence scores</p>
        </div>

        {error && (
          <div className="bg-red-900 border border-red-700 rounded-lg p-4 mb-8 text-red-200">
            {error}
          </div>
        )}

        {/* Games Grid */}
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
            {games.map((game) => (
              <div
                key={game.game_id}
                className="bg-slate-800 rounded-lg border border-slate-700 p-6 hover:border-emerald-500 transition"
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-4">
                    {/* Team matchup */}
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

                  {/* Prediction */}
                  {game.prediction && (
                    <div className="bg-emerald-900/40 rounded-lg p-4 text-right border border-emerald-800/30">
                      <div className="text-sm text-gray-300 mb-1">Win Probability</div>
                      <div className="flex gap-4 mb-3">
                        <div>
                          <div className="text-xl font-bold text-emerald-400">
                            {(game.prediction.home_win_prob * 100).toFixed(1)}%
                          </div>
                          <div className="text-xs text-gray-400">{game.home_team}</div>
                        </div>
                        <div>
                          <div className="text-xl font-bold text-emerald-400">
                            {(game.prediction.away_win_prob * 100).toFixed(1)}%
                          </div>
                          <div className="text-xs text-gray-400">{game.away_team}</div>
                        </div>
                      </div>
                      <div className="border-t border-emerald-800/30 pt-2 text-xs space-y-1">
                        <div className="text-emerald-300">
                          +EV if {game.home_team} &gt; {game.prediction.min_home_odds_decimal}x ({game.prediction.min_home_odds_american})
                        </div>
                        <div className="text-emerald-300">
                          +EV if {game.away_team} &gt; {game.prediction.min_away_odds_decimal}x ({game.prediction.min_away_odds_american})
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Game Date & Best Odds */}
                <div className="border-t border-slate-700 pt-4 grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-gray-400">Game Date</div>
                    <div className="text-white font-semibold">
                      {new Date(game.game_date).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </div>
                  </div>

                  {game.best_odds && game.best_odds.home && (
                    <div>
                      <div className="text-sm text-gray-400">Best Odds</div>
                      <div className="flex gap-2">
                        <div className="text-green-400 font-semibold">{game.best_odds.home.toFixed(2)}x</div>
                        <div className="text-red-400 font-semibold">{game.best_odds.away.toFixed(2)}x</div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Action Button */}
                <div className="mt-4 flex gap-2">
                  <button className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white py-2 rounded-lg transition font-semibold">
                    Place Pick
                  </button>
                  <button className="flex-1 bg-slate-700 hover:bg-slate-600 text-gray-300 py-2 rounded-lg transition">
                    View Details
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
