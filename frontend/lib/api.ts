import axios from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
const USE_MOCK_API = process.env.NEXT_PUBLIC_USE_MOCK_API === 'true'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

const mockUpcomingGames = {
  games: [
    {
      game_id: '002240001',
      home_team: 'BOS',
      away_team: 'NYK',
      game_date: new Date(Date.now() + 3600 * 1000 * 6).toISOString(),
      home_win_prob: 0.61,
      away_win_prob: 0.39,
      best_odds: {
        bookmaker: 'Pinnacle',
        home_win_odds: -145,
        away_win_odds: +128,
      },
    },
    {
      game_id: '002240002',
      home_team: 'DEN',
      away_team: 'LAL',
      game_date: new Date(Date.now() + 3600 * 1000 * 9).toISOString(),
      home_win_prob: 0.56,
      away_win_prob: 0.44,
      best_odds: {
        bookmaker: 'Bet365',
        home_win_odds: -120,
        away_win_odds: +110,
      },
    },
  ],
}

const mockArbitrage = {
  count: 2,
  updated_at: new Date().toISOString(),
  opportunities: [
    {
      game_id: '002240003',
      game_date: new Date(Date.now() + 3600 * 1000 * 4).toISOString(),
      home_team: 'MIA',
      away_team: 'PHI',
      type: 'home_arb',
      ev_percent: 1.8,
      bookmaker_1: 'DraftKings',
      bookmaker_2: 'FanDuel',
      bet_1: { side: 'home', odds: -105, implied_prob: 51.2 },
      bet_2: { side: 'away', odds: +115, implied_prob: 46.5 },
    },
    {
      game_id: '002240004',
      game_date: new Date(Date.now() + 3600 * 1000 * 7).toISOString(),
      home_team: 'PHX',
      away_team: 'DAL',
      type: 'away_arb',
      ev_percent: 1.2,
      bookmaker_1: 'PointsBet',
      bookmaker_2: 'BetMGM',
      bet_1: { side: 'away', odds: +120, implied_prob: 45.5 },
      bet_2: { side: 'home', odds: -105, implied_prob: 51.2 },
    },
  ],
}

const getMockResponse = (url?: string) => {
  if (!url) return null
  if (url.includes('/dashboard/games/upcoming')) return mockUpcomingGames
  if (url.includes('/dashboard/arbitrage')) return mockArbitrage
  if (url.includes('/arbitrage/opportunities')) return mockArbitrage
  if (url.includes('/games/upcoming')) return mockUpcomingGames.games
  return null
}

const getMockPostResponse = (url?: string, data?: any) => {
  if (!url) return null
  if (url.includes('/dashboard/picks')) {
    return { id: Math.floor(Math.random() * 10000), message: 'Pick saved', status: 'PENDING' }
  }
  return null
}

apiClient.interceptors.request.use((config) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('sb-token') : null
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  if (USE_MOCK_API && typeof window !== 'undefined') {
    const isPost = (config.method || 'get').toLowerCase() === 'post'
    const data = isPost ? getMockPostResponse(config.url, config.data) : getMockResponse(config.url)
    if (data) {
      config.adapter = async () => ({
        data,
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      })
    }
  }

  return config
})

export default apiClient
