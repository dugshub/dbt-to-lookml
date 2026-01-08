import { Link } from 'react-router-dom'
import { Layers } from 'lucide-react'
import { useAllMetrics } from '../api'

export function MetricsPage() {
  const { data: metrics, isLoading } = useAllMetrics()

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-gray-800 rounded w-40" />
        <div className="h-64 bg-gray-900 rounded-xl" />
      </div>
    )
  }

  // Group by model
  const byModel = metrics?.reduce((acc, metric) => {
    if (!acc[metric.model]) acc[metric.model] = []
    acc[metric.model].push(metric)
    return acc
  }, {} as Record<string, typeof metrics>)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Metrics</h1>
        <span className="text-gray-400">{metrics?.length} total</span>
      </div>

      {byModel && Object.entries(byModel).map(([model, items]) => (
        <div key={model} className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-4 py-3 bg-gray-800/50 border-b border-gray-800">
            <Link to={`/models/${model}`} className="font-medium text-white hover:text-blue-400">
              {model}
            </Link>
            <span className="text-gray-500 ml-2">({items?.length})</span>
          </div>
          <div className="divide-y divide-gray-800">
            {items?.map((metric) => (
              <div key={`${model}-${metric.name}`} className="px-4 py-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-white font-medium">{metric.name}</span>
                    <span className="px-2 py-0.5 text-xs bg-purple-500/10 text-purple-400 rounded">
                      {metric.type}
                    </span>
                    {metric.format && (
                      <span className="px-2 py-0.5 text-xs bg-blue-500/10 text-blue-400 rounded">
                        {metric.format}
                      </span>
                    )}
                    {metric.has_pop && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-orange-500/10 text-orange-400 rounded">
                        <Layers size={10} /> PoP
                      </span>
                    )}
                  </div>
                  <span className="text-sm text-gray-500">{metric.variant_count} variants</span>
                </div>
                {metric.label && (
                  <p className="text-sm text-gray-400 mt-1">{metric.label}</p>
                )}
                {metric.variants.length > 1 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {metric.variants.map((v, i) => (
                      <span
                        key={i}
                        className={`text-xs px-2 py-0.5 rounded ${
                          v.kind === 'base'
                            ? 'bg-gray-800 text-gray-300'
                            : v.kind === 'pop'
                            ? 'bg-orange-500/10 text-orange-400'
                            : 'bg-cyan-500/10 text-cyan-400'
                        }`}
                      >
                        {metric.name}{v.suffix || ''}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
