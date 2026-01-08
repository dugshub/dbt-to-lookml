import { useParams, Link } from 'react-router-dom'
import { useState } from 'react'
import { ArrowLeft, Key, Clock, Tag, EyeOff, Layers } from 'lucide-react'
import { useModel } from '../api'
import type { Dimension, Measure, Metric, Entity } from '../types'

type Tab = 'dimensions' | 'measures' | 'metrics' | 'entities'

function Badge({ children, color }: { children: React.ReactNode; color: string }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded ${color}`}>
      {children}
    </span>
  )
}

function DimensionRow({ dimension }: { dimension: Dimension }) {
  return (
    <div className="flex items-start justify-between py-3 border-b border-gray-800 last:border-0">
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="font-medium text-white">{dimension.name}</span>
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
          {dimension.type === 'categorical' && (
            <Badge color="bg-green-500/10 text-green-400">
              <Tag size={10} /> categorical
            </Badge>
          )}
        </div>
        {dimension.label && (
          <p className="text-sm text-gray-400 mt-0.5">{dimension.label}</p>
        )}
        {dimension.group && (
          <p className="text-xs text-gray-500 mt-1">Group: {dimension.group}</p>
        )}
      </div>
      <code className="text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded max-w-xs truncate">
        {dimension.expr || '—'}
      </code>
    </div>
  )
}

function MeasureRow({ measure }: { measure: Measure }) {
  return (
    <div className="flex items-start justify-between py-3 border-b border-gray-800 last:border-0">
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="font-medium text-white">{measure.name}</span>
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
        {measure.label && (
          <p className="text-sm text-gray-400 mt-0.5">{measure.label}</p>
        )}
        {measure.group && (
          <p className="text-xs text-gray-500 mt-1">Group: {measure.group}</p>
        )}
      </div>
      <code className="text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded max-w-xs truncate">
        {measure.expr}
      </code>
    </div>
  )
}

function MetricRow({ metric }: { metric: Metric }) {
  return (
    <div className="py-3 border-b border-gray-800 last:border-0">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-white">{metric.name}</span>
            <Badge color="bg-purple-500/10 text-purple-400">{metric.type}</Badge>
            {metric.format && (
              <Badge color="bg-blue-500/10 text-blue-400">{metric.format}</Badge>
            )}
            {metric.has_pop && (
              <Badge color="bg-orange-500/10 text-orange-400">
                <Layers size={10} /> PoP
              </Badge>
            )}
          </div>
          {metric.label && (
            <p className="text-sm text-gray-400 mt-0.5">{metric.label}</p>
          )}
          {metric.group && (
            <p className="text-xs text-gray-500 mt-1">Group: {metric.group}</p>
          )}
        </div>
        <span className="text-sm text-gray-500">{metric.variant_count} variants</span>
      </div>
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
  )
}

function EntityRow({ entity }: { entity: Entity }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-gray-800 last:border-0">
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
          <div>
            {model.dimensions.map((dim) => (
              <DimensionRow key={dim.name} dimension={dim} />
            ))}
          </div>
        )}
        {activeTab === 'measures' && (
          <div>
            {model.measures.map((measure) => (
              <MeasureRow key={measure.name} measure={measure} />
            ))}
          </div>
        )}
        {activeTab === 'metrics' && (
          <div>
            {model.metrics.map((metric) => (
              <MetricRow key={metric.name} metric={metric} />
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
