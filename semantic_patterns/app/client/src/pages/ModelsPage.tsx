import { Link } from 'react-router-dom'
import { Key, Ruler, Calculator, Target, Database } from 'lucide-react'
import { useModels } from '../api'
import type { ModelSummary } from '../types'

/** Convert snake_case to Title Case */
function toTitleCase(str: string): string {
  return str
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

interface StatBadgeProps {
  icon: React.ReactNode
  value: number
  label: string
}

function StatBadge({ icon, value, label }: StatBadgeProps) {
  return (
    <div className="flex items-center gap-1.5 text-gray-400" title={label}>
      {icon}
      <span className="text-sm font-medium text-gray-300">{value}</span>
    </div>
  )
}

interface ModelCardProps {
  model: ModelSummary
}

function ModelCard({ model }: ModelCardProps) {
  const displayName = model.label || toTitleCase(model.name)

  return (
    <Link
      to={`/models/${model.name}`}
      className="group flex flex-col bg-gray-900/50 border border-gray-800 rounded-xl p-5 hover:bg-gray-900 hover:border-gray-700 hover:shadow-lg hover:shadow-black/20 transition-all duration-200"
    >
      {/* Header - Title takes full width */}
      <div className="flex items-center gap-2 mb-1">
        <Database size={16} className="text-gray-500 shrink-0" />
        <h3 className="font-semibold text-white text-lg group-hover:text-blue-400 transition-colors">
          {displayName}
        </h3>
      </div>

      {/* Technical name */}
      <p className="text-xs text-gray-500 ml-6 mb-2">{model.name}</p>

      {/* Description */}
      {model.description && (
        <p className="text-sm text-gray-400 line-clamp-2 mb-3">
          {model.description}
        </p>
      )}

      {/* Stats + Primary Entity */}
      <div className="flex items-center justify-between mt-auto pt-3 border-t border-gray-800/50">
        <div className="flex items-center gap-4">
          <StatBadge
            icon={<Ruler size={14} />}
            value={model.dimensions}
            label="Dimensions"
          />
          <StatBadge
            icon={<Calculator size={14} />}
            value={model.measures}
            label="Measures"
          />
          <StatBadge
            icon={<Target size={14} />}
            value={model.metrics}
            label="Metrics"
          />
        </div>
        {model.entity_group && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-blue-500/10 text-blue-400 rounded">
            <Key size={10} />
            {model.entity_group}
          </span>
        )}
      </div>
    </Link>
  )
}

export function ModelsPage() {
  const { data: models, isLoading } = useModels()

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-gray-800 rounded w-32 animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-32 bg-gray-900/50 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  // Group models by entity_group if present
  const groupedModels = models?.reduce((acc, model) => {
    const group = model.entity_group || 'Other'
    if (!acc[group]) acc[group] = []
    acc[group].push(model)
    return acc
  }, {} as Record<string, ModelSummary[]>)

  const groups = Object.keys(groupedModels || {}).sort((a, b) => {
    if (a === 'Other') return 1
    if (b === 'Other') return -1
    return a.localeCompare(b)
  })

  // Only show groups if at least one group has 2+ models (meaningful grouping)
  const hasGroups = groups.some((g) => (groupedModels?.[g]?.length || 0) >= 2)

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Models</h1>
        <p className="text-gray-400 mt-1">
          {models?.length} semantic model{models?.length !== 1 ? 's' : ''}
        </p>
      </div>

      {hasGroups ? (
        // Grouped view
        groups.map((group) => (
          <section key={group}>
            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-4">
              {group}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {groupedModels?.[group].map((model) => (
                <ModelCard key={model.name} model={model} />
              ))}
            </div>
          </section>
        ))
      ) : (
        // Flat grid view
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {models?.map((model) => (
            <ModelCard key={model.name} model={model} />
          ))}
        </div>
      )}
    </div>
  )
}
