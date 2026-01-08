import { Link } from 'react-router-dom'
import { EyeOff } from 'lucide-react'
import { useAllMeasures } from '../api'
import { GroupedList } from '../components/common'

export function MeasuresPage() {
  const { data: measures, isLoading } = useAllMeasures()

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-gray-800 rounded w-40" />
        <div className="h-64 bg-gray-900 rounded-xl" />
      </div>
    )
  }

  // Group by entity first
  const byEntity = measures?.reduce((acc, measure) => {
    const entity = measure.entity || 'Other'
    if (!acc[entity]) acc[entity] = []
    acc[entity].push(measure)
    return acc
  }, {} as Record<string, typeof measures>)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Measures</h1>
        <span className="text-gray-400">{measures?.length} total</span>
      </div>

      {byEntity && Object.entries(byEntity).sort(([a], [b]) => a.localeCompare(b)).map(([entity, items]) => (
        <div key={entity} className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-4 py-3 bg-gray-800/50 border-b border-gray-800">
            <span className="font-medium text-white">{entity}</span>
            <span className="text-gray-500 ml-2">({items?.length})</span>
          </div>
          <div className="p-4">
            <GroupedList
              items={items || []}
              groupBy={(m) => m.group}
              renderItem={(measure) => {
                const displayName = measure.label || measure.name
                const showTechnicalName = measure.label && measure.label !== measure.name
                return (
                  <div
                    key={`${measure.model}-${measure.name}`}
                    className="flex items-start justify-between py-2 border-b border-gray-800/50 last:border-0"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-white font-medium">{displayName}</span>
                        <span className="px-2 py-0.5 text-xs bg-yellow-500/10 text-yellow-400 rounded">
                          {measure.agg}
                        </span>
                        {measure.format && (
                          <span className="px-2 py-0.5 text-xs bg-blue-500/10 text-blue-400 rounded">
                            {measure.format}
                          </span>
                        )}
                        {measure.hidden && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-gray-700 text-gray-400 rounded">
                            <EyeOff size={10} /> hidden
                          </span>
                        )}
                        <Link
                          to={`/models/${measure.model}`}
                          className="text-xs text-gray-500 hover:text-blue-400"
                        >
                          {measure.model}
                        </Link>
                      </div>
                      {showTechnicalName && (
                        <code className="text-xs text-gray-500 mt-0.5 block">{measure.name}</code>
                      )}
                    </div>
                    <code className="text-xs text-gray-500 bg-gray-800/50 px-2 py-1 rounded max-w-[200px] truncate ml-4 flex-shrink-0">
                      {measure.expr}
                    </code>
                  </div>
                )
              }}
              emptyMessage="No measures"
            />
          </div>
        </div>
      ))}
    </div>
  )
}
