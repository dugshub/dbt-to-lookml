import { Link } from 'react-router-dom'
import { Key, ChevronRight } from 'lucide-react'
import { useModels } from '../api'

export function ModelsPage() {
  const { data: models, isLoading } = useModels()

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-gray-800 rounded w-32" />
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-24 bg-gray-900 rounded-xl" />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Models</h1>

      <div className="space-y-3">
        {models?.map((model) => (
          <Link
            key={model.name}
            to={`/models/${model.name}`}
            className="flex items-center justify-between bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-blue-600 transition-colors group"
          >
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <h3 className="font-semibold text-white">{model.name}</h3>
                {model.primary_entity && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-blue-500/10 text-blue-400 rounded">
                    <Key size={10} />
                    {model.primary_entity}
                  </span>
                )}
              </div>
              {model.description && (
                <p className="text-sm text-gray-400 mt-1">{model.description}</p>
              )}
              <div className="flex gap-6 mt-3 text-sm text-gray-500">
                <span>
                  <span className="text-gray-300">{model.dimensions}</span> dimensions
                </span>
                <span>
                  <span className="text-gray-300">{model.measures}</span> measures
                </span>
                <span>
                  <span className="text-gray-300">{model.metrics}</span> metrics
                  <span className="text-gray-600"> ({model.metric_variants} variants)</span>
                </span>
                <span>
                  <span className="text-gray-300">{model.entities}</span> entities
                </span>
              </div>
            </div>
            <ChevronRight className="text-gray-600 group-hover:text-blue-400 transition-colors" />
          </Link>
        ))}
      </div>
    </div>
  )
}
