import { useParams, Link } from 'react-router-dom'
import { useState } from 'react'
import { ArrowLeft, Key, Clock, EyeOff, Layers } from 'lucide-react'
import { useModel } from '../api'
import { GroupedList } from '../components/common'
import type { Dimension, Measure, Metric, MetricVariant, Entity } from '../types'

type Tab = 'dimensions' | 'measures' | 'metrics' | 'entities'

function Badge({ children, color }: { children: React.ReactNode; color: string }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded ${color}`}>
      {children}
    </span>
  )
}

function DimensionRow({ dimension }: { dimension: Dimension }) {
  const displayName = dimension.label || dimension.name
  const showTechnicalName = dimension.label && dimension.label !== dimension.name

  return (
    <div className="flex items-start justify-between py-2.5 border-b border-gray-800/50 last:border-0">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-white">{displayName}</span>
          {dimension.hidden && (
            <Badge color="bg-gray-700 text-gray-400">
              <EyeOff size={10} /> hidden
            </Badge>
          )}
          {dimension.type === 'time' && (
            <Badge color="bg-purple-500/10 text-purple-400">
              <Clock size={10} /> {dimension.granularity || 'time'}
            </Badge>
          )}
        </div>
        {showTechnicalName && (
          <code className="text-xs text-gray-500 mt-0.5 block">{dimension.name}</code>
        )}
      </div>
      <code className="text-xs text-gray-500 bg-gray-800/50 px-2 py-1 rounded max-w-[200px] truncate ml-4 flex-shrink-0">
        {dimension.expr || '—'}
      </code>
    </div>
  )
}

function MeasureRow({ measure }: { measure: Measure }) {
  const displayName = measure.label || measure.name
  const showTechnicalName = measure.label && measure.label !== measure.name

  return (
    <div className="flex items-start justify-between py-2.5 border-b border-gray-800/50 last:border-0">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-white">{displayName}</span>
          <Badge color="bg-yellow-500/10 text-yellow-400">{measure.agg}</Badge>
          {measure.hidden && (
            <Badge color="bg-gray-700 text-gray-400">
              <EyeOff size={10} /> hidden
            </Badge>
          )}
          {measure.format && (
            <Badge color="bg-blue-500/10 text-blue-400">{measure.format}</Badge>
          )}
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
}

function MetricCard({ metric }: { metric: Metric }) {
  const displayName = metric.label || metric.name

  // Format variant suffix for display (e.g., "_py" -> "Prior Year")
  const formatVariantLabel = (v: MetricVariant): string => {
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

  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4 hover:border-gray-600 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div>
          <h3 className="font-semibold text-white text-lg">{displayName}</h3>
          <code className="text-xs text-gray-500">{metric.name}</code>
        </div>
        <div className="flex items-center gap-2">
          <Badge color="bg-purple-500/20 text-purple-300">{metric.type}</Badge>
          {metric.format && (
            <Badge color="bg-blue-500/20 text-blue-300">{metric.format}</Badge>
          )}
        </div>
      </div>

      {/* Description */}
      {metric.description && (
        <p className="text-sm text-gray-400 mb-3">{metric.description}</p>
      )}

      {/* Measure reference */}
      {metric.measure && (
        <p className="text-xs text-gray-500 mb-3">
          Measure: <code className="text-gray-400">{metric.measure}</code>
        </p>
      )}

      {/* Variants */}
      {metric.variants.length > 0 && (
        <div className="border-t border-gray-700/50 pt-3 mt-3">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs text-gray-500 uppercase tracking-wide">
              {metric.variant_count} Variant{metric.variant_count !== 1 ? 's' : ''}
            </span>
            {metric.has_pop && (
              <Badge color="bg-orange-500/20 text-orange-300">
                <Layers size={10} /> Period over Period
              </Badge>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {metric.variants.map((v, i) => (
              <div
                key={i}
                className={`text-xs px-3 py-1.5 rounded-md border ${
                  v.kind === 'base'
                    ? 'bg-gray-700/50 border-gray-600 text-gray-200'
                    : v.kind === 'pop'
                    ? 'bg-orange-500/10 border-orange-500/30 text-orange-300'
                    : 'bg-cyan-500/10 border-cyan-500/30 text-cyan-300'
                }`}
              >
                <div className="font-medium">{formatVariantLabel(v)}</div>
                <div className="text-[10px] opacity-70 mt-0.5">
                  {metric.name}{v.suffix || ''}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function EntityRow({ entity }: { entity: Entity }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-800/50 last:border-0">
      <div className="flex items-center gap-3">
        <span className="font-medium text-white">{entity.name}</span>
        <Badge
          color={
            entity.type === 'primary'
              ? 'bg-blue-500/10 text-blue-400'
              : entity.type === 'foreign'
              ? 'bg-yellow-500/10 text-yellow-400'
              : 'bg-gray-700 text-gray-400'
          }
        >
          <Key size={10} /> {entity.type}
        </Badge>
        {entity.type === 'foreign' && !entity.complete && (
          <Badge color="bg-red-500/10 text-red-400">incomplete</Badge>
        )}
      </div>
      <code className="text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded">
        {entity.expr}
      </code>
    </div>
  )
}

export function ModelDetailPage() {
  const { name } = useParams<{ name: string }>()
  const { data: model, isLoading } = useModel(name || '')
  const [activeTab, setActiveTab] = useState<Tab>('dimensions')

  if (isLoading || !model) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-6 bg-gray-800 rounded w-24" />
        <div className="h-10 bg-gray-800 rounded w-64" />
        <div className="h-64 bg-gray-900 rounded-xl" />
      </div>
    )
  }

  const tabs: { key: Tab; label: string; count: number }[] = [
    { key: 'dimensions', label: 'Dimensions', count: model.dimensions.length },
    { key: 'measures', label: 'Measures', count: model.measures.length },
    { key: 'metrics', label: 'Metrics', count: model.metrics.length },
    { key: 'entities', label: 'Entities', count: model.entities.length },
  ]

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link
        to="/models"
        className="inline-flex items-center gap-1 text-sm text-gray-400 hover:text-white"
      >
        <ArrowLeft size={16} /> Back to Models
      </Link>

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">{model.name}</h1>
        {model.description && (
          <p className="text-gray-400 mt-1">{model.description}</p>
        )}
        <div className="flex gap-4 mt-3 text-sm text-gray-500">
          {model.primary_entity && (
            <span className="inline-flex items-center gap-1">
              <Key size={14} className="text-blue-400" />
              {model.primary_entity.name}
            </span>
          )}
          {model.time_dimension && (
            <span className="inline-flex items-center gap-1">
              <Clock size={14} className="text-purple-400" />
              {model.time_dimension}
            </span>
          )}
          <span>{model.total_variant_count} total metric variants</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-800">
        <div className="flex gap-6">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'text-white border-blue-500'
                  : 'text-gray-400 border-transparent hover:text-white'
              }`}
            >
              {tab.label}
              <span className="ml-2 text-gray-500">({tab.count})</span>
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        {activeTab === 'dimensions' && (
          <GroupedList
            items={model.dimensions}
            groupBy={(dim) => dim.group}
            renderItem={(dim) => <DimensionRow key={dim.name} dimension={dim} />}
            emptyMessage="No dimensions"
          />
        )}
        {activeTab === 'measures' && (
          <GroupedList
            items={model.measures}
            groupBy={(m) => m.group}
            renderItem={(m) => <MeasureRow key={m.name} measure={m} />}
            emptyMessage="No measures"
          />
        )}
        {activeTab === 'metrics' && (
          <div className="grid gap-4 md:grid-cols-2">
            {model.metrics.map((metric) => (
              <MetricCard key={metric.name} metric={metric} />
            ))}
          </div>
        )}
        {activeTab === 'entities' && (
          <div>
            {model.entities.map((entity) => (
              <EntityRow key={entity.name} entity={entity} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
