'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/hooks/useAuth'
import { useEffect } from 'react'

export default function Home() {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && user) {
      router.push('/dashboard')
    }
  }, [user, loading, router])

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 bg-slate-900/80 backdrop-blur-sm border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-white">HoopsQuant</h1>
          <div className="flex gap-4">
            <Link
              href="/login"
              className="text-gray-400 hover:text-white transition font-medium"
            >
              Sign In
            </Link>
            <Link
              href="/login"
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg transition font-medium"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="pt-32 pb-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          {/* Hero Section with Animation */}
          <div className="space-y-12">
            {/* Animated Hero */}
            <div className="space-y-6 text-center animate-fade-in-up">
              <h2 className="text-6xl md:text-7xl font-bold text-white leading-tight">
                Smart NBA
                <span className="block text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400">
                  Betting Made Simple
                </span>
              </h2>
              <p className="text-xl text-gray-300 max-w-3xl mx-auto">
                AI-powered predictions meet guaranteed arbitrage opportunities. Get consistent wins backed by data science.
              </p>
            </div>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center mt-12 animate-fade-in-up-delay">
              <Link
                href="/login"
                className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white px-8 py-4 rounded-lg font-semibold text-lg transition transform hover:scale-105"
              >
                Start Free Trial
              </Link>
              <button className="border-2 border-gray-400 hover:border-white text-white px-8 py-4 rounded-lg font-semibold text-lg transition">
                Watch Demo
              </button>
            </div>

            {/* Feature Highlights */}
            <div className="grid md:grid-cols-3 gap-8 mt-20 pt-12 border-t border-slate-700">
              <div className="bg-slate-800/50 backdrop-blur rounded-lg p-8 border border-slate-700 hover:border-blue-500 transition transform hover:scale-105">
                <div className="text-4xl mb-4">🎯</div>
                <h3 className="text-xl font-bold text-white mb-2">AI Predictions</h3>
                <p className="text-gray-400">
                  ML model trained on 2,000+ games with 65% accuracy. Get confidence scores for every pick.
                </p>
              </div>

              <div className="bg-slate-800/50 backdrop-blur rounded-lg p-8 border border-slate-700 hover:border-green-500 transition transform hover:scale-105">
                <div className="text-4xl mb-4">💰</div>
                <h3 className="text-xl font-bold text-white mb-2">Guaranteed Profits</h3>
                <p className="text-gray-400">
                  Arbitrage scanning across 5+ bookmakers. Find guaranteed ROI opportunities instantly.
                </p>
              </div>

              <div className="bg-slate-800/50 backdrop-blur rounded-lg p-8 border border-slate-700 hover:border-purple-500 transition transform hover:scale-105">
                <div className="text-4xl mb-4">📊</div>
                <h3 className="text-xl font-bold text-white mb-2">ROI Tracking</h3>
                <p className="text-gray-400">
                  Real-time statistics, win rates, and profit tracking. Prove your edge with data.
                </p>
              </div>
            </div>

            {/* Pricing Preview */}
            <div className="mt-20 pt-12 border-t border-slate-700">
              <h3 className="text-3xl font-bold text-white text-center mb-12">Simple Pricing</h3>
              <div className="grid md:grid-cols-3 gap-8">
                {/* Free Tier */}
                <div className="bg-slate-800 rounded-lg p-8 border border-slate-700">
                  <h4 className="text-xl font-bold text-white mb-4">Free</h4>
                  <div className="text-3xl font-bold text-white mb-6">$0<span className="text-sm text-gray-400">/mo</span></div>
                  <ul className="space-y-3 text-gray-300 mb-8">
                    <li>✓ Today's top picks</li>
                    <li>✓ AI predictions</li>
                    <li>✓ Basic stats</li>
                    <li>✗ Arbitrage scanner</li>
                    <li>✗ Advanced alerts</li>
                  </ul>
                  <button className="w-full border border-gray-400 text-white py-2 rounded-lg hover:bg-gray-700 transition">
                    Get Started
                  </button>
                </div>

                {/* Pro Tier - Highlighted */}
                <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-lg p-8 border-2 border-blue-400 transform scale-105">
                  <div className="bg-blue-500 text-white px-3 py-1 rounded-full text-sm font-bold w-fit mb-4">
                    Most Popular
                  </div>
                  <h4 className="text-xl font-bold text-white mb-4">Pro</h4>
                  <div className="text-3xl font-bold text-white mb-6">$9.99<span className="text-sm text-blue-100">/mo</span></div>
                  <ul className="space-y-3 text-white mb-8">
                    <li>✓ Everything in Free</li>
                    <li>✓ Arbitrage scanner</li>
                    <li>✓ Real-time alerts</li>
                    <li>✓ Line tracking</li>
                    <li>✗ SMS notifications</li>
                  </ul>
                  <button className="w-full bg-white text-blue-600 font-semibold py-2 rounded-lg hover:bg-gray-100 transition">
                    Start Free Trial
                  </button>
                </div>

                {/* Premium Tier */}
                <div className="bg-slate-800 rounded-lg p-8 border border-slate-700">
                  <h4 className="text-xl font-bold text-white mb-4">Premium</h4>
                  <div className="text-3xl font-bold text-white mb-6">$29.99<span className="text-sm text-gray-400">/mo</span></div>
                  <ul className="space-y-3 text-gray-300 mb-8">
                    <li>✓ Everything in Pro</li>
                    <li>✓ SMS notifications</li>
                    <li>✓ API access</li>
                    <li>✓ Priority support</li>
                    <li>✓ Custom alerts</li>
                  </ul>
                  <button className="w-full border border-gray-400 text-white py-2 rounded-lg hover:bg-gray-700 transition">
                    Coming Soon
                  </button>
                </div>
              </div>
            </div>

            {/* Stats */}
            <div className="mt-20 pt-12 border-t border-slate-700 grid md:grid-cols-4 gap-8 text-center">
              <div>
                <div className="text-4xl font-bold text-blue-400">1,310+</div>
                <div className="text-gray-400 mt-2">Games Covered</div>
              </div>
              <div>
                <div className="text-4xl font-bold text-blue-400">65%</div>
                <div className="text-gray-400 mt-2">Win Rate</div>
              </div>
              <div>
                <div className="text-4xl font-bold text-green-400">5+</div>
                <div className="text-gray-400 mt-2">Bookmakers</div>
              </div>
              <div>
                <div className="text-4xl font-bold text-purple-400">2,000+</div>
                <div className="text-gray-400 mt-2">Training Games</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-700 mt-20 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto text-center text-gray-400">
          <p>© 2026 HoopsQuant. All rights reserved. | Responsible Gambling</p>
        </div>
      </footer>

      {/* Animations */}
      <style>{`
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes fadeInUpDelay {
          0% {
            opacity: 0;
            transform: translateY(20px);
          }
          50% {
            opacity: 0;
            transform: translateY(20px);
          }
          100% {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .animate-fade-in-up {
          animation: fadeInUp 0.8s ease-out;
        }

        .animate-fade-in-up-delay {
          animation: fadeInUpDelay 1.2s ease-out;
        }
      `}</style>
    </div>
  )
}
