import { Database, GitBranch } from 'lucide-react'
import { useConfig } from '../api'

export function ExploresPage() {
  const { data: configData, isLoading } = useConfig()

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-gray-800 rounded w-40" />
        <div className="h-64 bg-gray-900 rounded-xl" />
      </div>
    )
  }

  const explores = configData?.config.looker.explores || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Explores</h1>
        <span className="text-gray-400">{explores.length} configured</span>
      </div>

      {explores.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
          <GitBranch className="mx-auto text-gray-600 mb-3" size={32} />
          <p className="text-gray-400">No explores configured</p>
          <p className="text-sm text-gray-500 mt-1">
            Add explores to your sp.yml under <code className="text-gray-400">looker.explores</code>
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {explores.map((explore, i) => (
            <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-white">
                    {explore.name || explore.fact}
                  </h3>
                  {explore.label && (
                    <p className="text-sm text-gray-400 mt-0.5">{explore.label}</p>
                  )}
                  {explore.description && (
                    <p className="text-sm text-gray-500 mt-1">{explore.description}</p>
                  )}
                </div>
                <span className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-blue-500/10 text-blue-400 rounded">
                  <Database size={12} />
                  {explore.fact}
                </span>
              </div>

              {explore.joined_facts.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs text-gray-500 mb-2">Joined Facts</p>
                  <div className="flex flex-wrap gap-2">
                    {explore.joined_facts.map((fact) => (
                      <span
                        key={fact}
                        className="px-2 py-1 text-xs bg-gray-800 text-gray-300 rounded"
                      >
                        {fact}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {explore.join_exclusions.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs text-gray-500 mb-2">Join Exclusions</p>
                  <div className="flex flex-wrap gap-2">
                    {explore.join_exclusions.map((exclusion) => (
                      <span
                        key={exclusion}
                        className="px-2 py-1 text-xs bg-red-500/10 text-red-400 rounded"
                      >
                        {exclusion}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
