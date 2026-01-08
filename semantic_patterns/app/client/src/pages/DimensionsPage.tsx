import { Link } from 'react-router-dom'
import { Clock, EyeOff } from 'lucide-react'
import { useAllDimensions } from '../api'
import { GroupedList } from '../components/common'

export function DimensionsPage() {
  const { data: dimensions, isLoading } = useAllDimensions()

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-gray-800 rounded w-40" />
        <div className="h-64 bg-gray-900 rounded-xl" />
      </div>
    )
  }

  // Group by entity first
  const byEntity = dimensions?.reduce((acc, dim) => {
    const entity = dim.entity || 'Other'
    if (!acc[entity]) acc[entity] = []
    acc[entity].push(dim)
    return acc
  }, {} as Record<string, typeof dimensions>)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Dimensions</h1>
        <span className="text-gray-400">{dimensions?.length} total</span>
      </div>

      {byEntity && Object.entries(byEntity).sort(([a], [b]) => a.localeCompare(b)).map(([entity, dims]) => (
        <div key={entity} className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-4 py-3 bg-gray-800/50 border-b border-gray-800">
            <span className="font-medium text-white">{entity}</span>
            <span className="text-gray-500 ml-2">({dims?.length})</span>
          </div>
          <div className="p-4">
            <GroupedList
              items={dims || []}
              groupBy={(dim) => dim.group}
              renderItem={(dim) => {
                const displayName = dim.label || dim.name
                const showTechnicalName = dim.label && dim.label !== dim.name
                return (
                  <div
                    key={`${dim.model}-${dim.name}`}
                    className="flex items-start justify-between py-2 border-b border-gray-800/50 last:border-0"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-white font-medium">{displayName}</span>
                        {dim.type === 'time' && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-purple-500/10 text-purple-400 rounded">
                            <Clock size={10} /> {dim.granularity || 'time'}
                          </span>
                        )}
                        {dim.hidden && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-gray-700 text-gray-400 rounded">
                            <EyeOff size={10} /> hidden
                          </span>
                        )}
                        <Link
                          to={`/models/${dim.model}`}
                          className="text-xs text-gray-500 hover:text-blue-400"
                        >
                          {dim.model}
                        </Link>
                      </div>
                      {showTechnicalName && (
                        <code className="text-xs text-gray-500 mt-0.5 block">{dim.name}</code>
                      )}
                    </div>
                  </div>
                )
              }}
              emptyMessage="No dimensions"
            />
          </div>
        </div>
      ))}
    </div>
  )
}
