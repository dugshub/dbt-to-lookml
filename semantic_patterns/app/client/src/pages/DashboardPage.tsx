import { Link } from 'react-router-dom'
import {
  Database,
  Ruler,
  Calculator,
  Target,
  GitBranch,
  Key,
  Layers,
} from 'lucide-react'
import { useStats, useModels, useConfig } from '../api'

interface StatCardProps {
  icon: React.ReactNode
  label: string
  value: number
  to?: string
  color: string
}

function StatCard({ icon, label, value, to, color }: StatCardProps) {
  const content = (
    <div className={`bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-colors`}>
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${color}`}>
          {icon}
        </div>
        <div>
          <p className="text-2xl font-bold text-white">{value}</p>
          <p className="text-sm text-gray-400">{label}</p>
        </div>
      </div>
    </div>
  )

  if (to) {
    return <Link to={to}>{content}</Link>
  }
  return content
}

export function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useStats()
  const { data: models, isLoading: modelsLoading } = useModels()
  const { data: configData } = useConfig()

  if (statsLoading || modelsLoading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-8 bg-gray-800 rounded w-48" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-900 rounded-xl" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        {configData && (
          <p className="text-gray-400 mt-1">
            Project: <span className="text-gray-300">{configData.config.project}</span>
            {' · '}
            Format: <span className="text-gray-300">{configData.config.format}</span>
          </p>
        )}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon={<Database size={20} className="text-blue-400" />}
          label="Models"
          value={stats?.models ?? 0}
          to="/models"
          color="bg-blue-500/10"
        />
        <StatCard
          icon={<Ruler size={20} className="text-green-400" />}
          label="Dimensions"
          value={stats?.dimensions ?? 0}
          to="/dimensions"
          color="bg-green-500/10"
        />
        <StatCard
          icon={<Calculator size={20} className="text-yellow-400" />}
          label="Measures"
          value={stats?.measures ?? 0}
          to="/measures"
          color="bg-yellow-500/10"
        />
        <StatCard
          icon={<Target size={20} className="text-purple-400" />}
          label="Metrics"
          value={stats?.metrics ?? 0}
          to="/metrics"
          color="bg-purple-500/10"
        />
        <StatCard
          icon={<Layers size={20} className="text-pink-400" />}
          label="Metric Variants"
          value={stats?.metric_variants ?? 0}
          color="bg-pink-500/10"
        />
        <StatCard
          icon={<Key size={20} className="text-orange-400" />}
          label="Entities"
          value={stats?.entities ?? 0}
          color="bg-orange-500/10"
        />
        <StatCard
          icon={<GitBranch size={20} className="text-cyan-400" />}
          label="Explores"
          value={stats?.explores ?? 0}
          to="/explores"
          color="bg-cyan-500/10"
        />
      </div>

      {/* Models List */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Semantic Models</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {models?.map((model) => (
            <Link
              key={model.name}
              to={`/models/${model.name}`}
              className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-blue-600 transition-colors"
            >
              <h3 className="font-semibold text-white">{model.name}</h3>
              {model.description && (
                <p className="text-sm text-gray-400 mt-1 line-clamp-2">{model.description}</p>
              )}
              <div className="flex gap-4 mt-3 text-xs text-gray-500">
                <span>{model.dimensions} dims</span>
                <span>{model.measures} measures</span>
                <span>{model.metrics} metrics</span>
              </div>
              {model.primary_entity && (
                <div className="mt-2">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-blue-500/10 text-blue-400 rounded">
                    <Key size={10} />
                    {model.primary_entity}
                  </span>
                </div>
              )}
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
