import { Link } from 'react-router-dom'
import { Clock, Tag, EyeOff } from 'lucide-react'
import { useAllDimensions } from '../api'

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

  // Group by model
  const byModel = dimensions?.reduce((acc, dim) => {
    if (!acc[dim.model]) acc[dim.model] = []
    acc[dim.model].push(dim)
    return acc
  }, {} as Record<string, typeof dimensions>)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Dimensions</h1>
        <span className="text-gray-400">{dimensions?.length} total</span>
      </div>

      {byModel && Object.entries(byModel).map(([model, dims]) => (
        <div key={model} className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-4 py-3 bg-gray-800/50 border-b border-gray-800">
            <Link to={`/models/${model}`} className="font-medium text-white hover:text-blue-400">
              {model}
            </Link>
            <span className="text-gray-500 ml-2">({dims?.length})</span>
          </div>
          <div className="divide-y divide-gray-800">
            {dims?.map((dim) => (
              <div key={`${model}-${dim.name}`} className="px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-white">{dim.name}</span>
                  {dim.type === 'time' && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-purple-500/10 text-purple-400 rounded">
                      <Clock size={10} /> {dim.granularity || 'time'}
                    </span>
                  )}
                  {dim.type === 'categorical' && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-green-500/10 text-green-400 rounded">
                      <Tag size={10} /> categorical
                    </span>
                  )}
                  {dim.hidden && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-gray-700 text-gray-400 rounded">
                      <EyeOff size={10} /> hidden
                    </span>
                  )}
                </div>
                {dim.group && <span className="text-xs text-gray-500">{dim.group}</span>}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
