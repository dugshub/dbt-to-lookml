import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Database,
  Ruler,
  Calculator,
  Target,
  GitBranch,
  Settings,
  RefreshCw,
  Play,
} from 'lucide-react'
import { useReload, useBuild } from '../../api'

interface NavItem {
  to: string
  icon: React.ReactNode
  label: string
}

const navItems: NavItem[] = [
  { to: '/', icon: <LayoutDashboard size={18} />, label: 'Dashboard' },
  { to: '/models', icon: <Database size={18} />, label: 'Models' },
  { to: '/dimensions', icon: <Ruler size={18} />, label: 'Dimensions' },
  { to: '/measures', icon: <Calculator size={18} />, label: 'Measures' },
  { to: '/metrics', icon: <Target size={18} />, label: 'Metrics' },
  { to: '/explores', icon: <GitBranch size={18} />, label: 'Explores' },
  { to: '/config', icon: <Settings size={18} />, label: 'Config' },
]

function NavLink({ to, icon, label }: NavItem) {
  const location = useLocation()
  const isActive = location.pathname === to ||
    (to !== '/' && location.pathname.startsWith(to))

  return (
    <Link
      to={to}
      className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
        isActive
          ? 'bg-blue-600 text-white'
          : 'text-gray-400 hover:text-white hover:bg-gray-800'
      }`}
    >
      {icon}
      {label}
    </Link>
  )
}

export function Shell({ children }: { children: React.ReactNode }) {
  const reload = useReload()
  const build = useBuild()

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-56 bg-gray-900 border-r border-gray-800 flex flex-col">
        {/* Logo */}
        <div className="p-4 border-b border-gray-800">
          <h1 className="text-lg font-semibold text-white">semantic-patterns</h1>
          <p className="text-xs text-gray-500">Semantic Layer UI</p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => (
            <NavLink key={item.to} {...item} />
          ))}
        </nav>

        {/* Actions */}
        <div className="p-3 border-t border-gray-800 space-y-2">
          <button
            onClick={() => reload.mutate()}
            disabled={reload.isPending}
            className="flex items-center justify-center gap-2 w-full px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw size={16} className={reload.isPending ? 'animate-spin' : ''} />
            Reload
          </button>
          <button
            onClick={() => build.mutate(false)}
            disabled={build.isPending}
            className="flex items-center justify-center gap-2 w-full px-3 py-2 text-sm bg-blue-600 text-white hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50"
          >
            <Play size={16} />
            {build.isPending ? 'Building...' : 'Build'}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="max-w-6xl mx-auto p-6">
          {children}
        </div>
      </main>
    </div>
  )
}
