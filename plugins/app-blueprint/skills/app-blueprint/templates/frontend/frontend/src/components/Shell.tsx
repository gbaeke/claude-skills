{{#auth}}
import { House, LogOut, Monitor, Moon, Sun } from 'lucide-react'
{{/auth}}
{{^auth}}
import { House, Monitor, Moon, Sun } from 'lucide-react'
{{/auth}}
import { NavLink, Outlet } from 'react-router'
import { useQuery } from '@tanstack/react-query'
{{#auth}}
import { healthOptions, meOptions } from '@/client/@tanstack/react-query.gen'
{{/auth}}
{{^auth}}
import { healthOptions } from '@/client/@tanstack/react-query.gen'
{{/auth}}
import { useTheme } from '@/lib/theme-context'
import { cn } from '@/lib/utils'

const nav = [{ to: '/', label: 'Home', icon: House }]

function ApiStatus() {
  const { data, isError } = useQuery({ ...healthOptions(), refetchInterval: 30_000 })
  const ok = data?.status === 'ok'
  return (
    <span className="flex items-center gap-2 text-xs text-fg-muted">
      <span className={cn('size-2 rounded-full', ok ? 'bg-ok' : isError ? 'bg-danger' : 'bg-fg-muted')} />
      {ok ? 'API connected' : isError ? 'API offline' : 'Connecting'}
    </span>
  )
}

function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const next = { system: 'light', light: 'dark', dark: 'system' } as const
  const Icon = { system: Monitor, light: Sun, dark: Moon }[theme]
  return (
    <button className="btn-ghost p-1.5" onClick={() => setTheme(next[theme])} title={`Theme: ${theme}`} aria-label={`Theme: ${theme}`}>
      <Icon className="size-4" />
    </button>
  )
}
{{#auth}}

/** Who is signed in and the way out; nothing when the app runs without sign-in. */
function UserMenu() {
  const { data } = useQuery({ ...meOptions(), staleTime: Infinity })
  if (!data?.user) return null
  return (
    <span className="flex items-center gap-1 text-xs text-fg-muted">
      <span className="hidden sm:inline">{data.user.email}</span>
      <a href="/auth/logout" className="btn-ghost p-1.5" title="Sign out" aria-label="Sign out">
        <LogOut className="size-4" />
      </a>
    </span>
  )
}
{{/auth}}

export function Shell() {
  return (
    <div className="flex h-full">
      <aside className="flex w-52 shrink-0 flex-col border-r border-border bg-surface">
        <div className="flex h-14 items-center border-b border-border px-4 font-semibold">{{title}}</div>
        <nav className="flex flex-1 flex-col gap-0.5 p-2">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                cn('flex items-center gap-3 rounded-md px-3 py-1.5', isActive ? 'bg-accent-soft text-accent' : 'text-fg-muted hover:bg-muted hover:text-fg')
              }
            >
              <Icon className="size-4" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-end gap-3 border-b border-border bg-surface px-6">
          <ApiStatus />
          <ThemeToggle />
{{#auth}}
          <UserMenu />
{{/auth}}
        </header>
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
