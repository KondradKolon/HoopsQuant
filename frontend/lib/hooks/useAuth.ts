import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import type { User, AuthChangeEvent, Session } from '@supabase/supabase-js'

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const supabase = createClient()
    
    if (!supabase) {
      setLoading(false)
      return
    }

    const getSession = async () => {
      try {
        const result = await supabase.auth.getSession()
        if (result.error) {
          setError(result.error.message)
        } else {
          setUser(result.data?.session?.user ?? null)
        }
        setLoading(false)
      } catch (err) {
        setError('Failed to get session')
        setLoading(false)
      }
    }

    getSession()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event: AuthChangeEvent, session: Session | null) => {
      setUser(session?.user ?? null)
    })

    return () => {
      subscription?.unsubscribe()
    }
  }, [])

  return { user, loading, error }
}
