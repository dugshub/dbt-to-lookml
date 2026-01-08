import { Link } from 'react-router-dom'
import { Layers } from 'lucide-react'
import { useAllMetrics } from '../api'
import type { MetricVariant } from '../types'

// Format variant suffix for display
function formatVariantLabel(v: MetricVariant): string {
  if (v.kind === 'base') return 'Base'
  if (v.kind === 'pop' && v.params && 'comparison' in v.params) {
    const comp = v.params.comparison
    const output = v.params.output
    const compLabels: Record<string, string> = {
      py: 'Prior Year',
      pm: 'Prior Month',
      pq: 'Prior Quarter',
      pw: 'Prior Week',
      pp: 'Prior Period',
    }
    const outputLabels: Record<string, string> = {
      previous: '',
      change: 'Change',
      pct_change: '% Change',
    }
    const compLabel = compLabels[comp] || comp.toUpperCase()
    const outLabel = outputLabels[output] || output
    return outLabel ? `${compLabel} ${outLabel}` : compLabel
  }
  if (v.kind === 'benchmark' && v.params && 'label' in v.params) {
    return v.params.label || 'Benchmark'
  }
  return v.suffix ? v.suffix.replace(/_/g, ' ').trim() : v.kind
}

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
          <div className="grid gap-4 p-4 md:grid-cols-2">
            {items?.map((metric) => {
              const displayName = metric.label || metric.name
              return (
                <div
                  key={`${model}-${metric.name}`}
                  className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4"
                >
                  {/* Header */}
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="font-semibold text-white">{displayName}</h3>
                      <code className="text-xs text-gray-500">{metric.name}</code>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 text-xs bg-purple-500/20 text-purple-300 rounded">
                        {metric.type}
                      </span>
                      {metric.format && (
                        <span className="px-2 py-0.5 text-xs bg-blue-500/20 text-blue-300 rounded">
                          {metric.format}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Variants */}
                  {metric.variants.length > 0 && (
                    <div className="border-t border-gray-700/50 pt-3 mt-3">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs text-gray-500 uppercase tracking-wide">
                          {metric.variant_count} Variant{metric.variant_count !== 1 ? 's' : ''}
                        </span>
                        {metric.has_pop && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-orange-500/20 text-orange-300 rounded">
                            <Layers size={10} /> PoP
                          </span>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {metric.variants.map((v, i) => (
                          <div
                            key={i}
                            className={`text-xs px-2.5 py-1 rounded-md border ${
                              v.kind === 'base'
                                ? 'bg-gray-700/50 border-gray-600 text-gray-200'
                                : v.kind === 'pop'
                                ? 'bg-orange-500/10 border-orange-500/30 text-orange-300'
                                : 'bg-cyan-500/10 border-cyan-500/30 text-cyan-300'
                            }`}
                          >
                            <div className="font-medium">{formatVariantLabel(v)}</div>
                            <div className="text-[10px] opacity-70">{metric.name}{v.suffix || ''}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
