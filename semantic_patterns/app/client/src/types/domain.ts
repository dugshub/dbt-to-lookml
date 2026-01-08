// Domain types mirroring Python models

export type DimensionType = 'categorical' | 'time'
export type TimeGranularity = 'hour' | 'day' | 'week' | 'month' | 'quarter' | 'year'
export type MetricType = 'simple' | 'derived' | 'ratio'
export type VariantKind = 'base' | 'pop' | 'benchmark'
export type AggregationType = 'sum' | 'count' | 'count_distinct' | 'average' | 'min' | 'max' | 'median' | 'percentile'

export interface Dimension {
  name: string
  type: DimensionType
  label?: string
  description?: string
  expr?: string
  granularity?: TimeGranularity
  primary_variant?: string
  variants?: Record<string, string>
  group?: string
  hidden: boolean
}

export interface Measure {
  name: string
  agg: AggregationType
  expr: string
  label?: string
  description?: string
  format?: string
  group?: string
  hidden: boolean
}

export interface PopParams {
  comparison: string
  output: string
}

export interface BenchmarkParams {
  slice: string
  label?: string
}

export interface MetricVariant {
  kind: VariantKind
  params?: PopParams | BenchmarkParams
  value_format?: string
  suffix: string
}

export interface Filter {
  conditions: Array<{
    field: string
    operator: string
    value: string | number | boolean | Array<string | number>
  }>
}

export interface Metric {
  name: string
  type: MetricType
  label?: string
  description?: string
  measure?: string
  expr?: string
  metrics?: string[]
  numerator?: string
  denominator?: string
  filter?: Filter
  pop?: {
    comparisons: string[]
    outputs: string[]
  }
  benchmarks?: BenchmarkParams[]
  variants: MetricVariant[]
  format?: string
  group?: string
  entity?: string
  variant_count: number
  has_pop: boolean
  has_benchmark: boolean
}

export interface Entity {
  name: string
  type: 'primary' | 'foreign' | 'unique'
  expr: string
  label?: string
  complete: boolean
}

export interface DataModel {
  name: string
  catalog?: string
  schema_name: string
  table: string
  connection: string
}

export interface ProcessedModel {
  name: string
  description?: string
  data_model?: DataModel
  dimensions: Dimension[]
  measures: Measure[]
  metrics: Metric[]
  entities: Entity[]
  time_dimension?: string
  primary_entity?: Entity
  foreign_entities: Entity[]
  total_variant_count: number
}

export interface ModelSummary {
  name: string
  description?: string
  dimensions: number
  measures: number
  metrics: number
  metric_variants: number
  entities: number
  primary_entity?: string
  time_dimension?: string
}

export interface Stats {
  models: number
  dimensions: number
  measures: number
  metrics: number
  metric_variants: number
  entities: number
  explores: number
}
