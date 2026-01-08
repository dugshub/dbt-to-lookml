import { Link } from 'react-router-dom'
import { EyeOff } from 'lucide-react'
import { useAllMeasures } from '../api'

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

  // Group by model
  const byModel = measures?.reduce((acc, measure) => {
    if (!acc[measure.model]) acc[measure.model] = []
    acc[measure.model].push(measure)
    return acc
  }, {} as Record<string, typeof measures>)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Measures</h1>
        <span className="text-gray-400">{measures?.length} total</span>
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
            {items?.map((measure) => (
              <div key={`${model}-${measure.name}`} className="px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-white">{measure.name}</span>
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
                </div>
                <code className="text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded max-w-xs truncate">
                  {measure.expr}
                </code>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
