import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type {
  Stats,
  ModelSummary,
  ProcessedModel,
  Dimension,
  Measure,
  Metric,
  Entity,
  DimensionWithContext,
  MeasureWithContext,
  MetricWithContext,
  ConfigResponse,
  ValidateResult,
  BuildResult,
} from '../types'

// Query keys
export const queryKeys = {
  stats: ['stats'] as const,
  models: ['models'] as const,
  model: (name: string) => ['models', name] as const,
  modelDimensions: (name: string) => ['models', name, 'dimensions'] as const,
  modelMeasures: (name: string) => ['models', name, 'measures'] as const,
  modelMetrics: (name: string) => ['models', name, 'metrics'] as const,
  modelEntities: (name: string) => ['models', name, 'entities'] as const,
  config: ['config'] as const,
  configRaw: ['config', 'raw'] as const,
  allDimensions: ['dimensions'] as const,
  allMeasures: ['measures'] as const,
  allMetrics: ['metrics'] as const,
  allEntities: ['entities'] as const,
}

// Stats
export function useStats() {
  return useQuery({
    queryKey: queryKeys.stats,
    queryFn: async () => {
      const { data } = await api.get<Stats>('/stats')
      return data
    },
  })
}

// Models
export function useModels() {
  return useQuery({
    queryKey: queryKeys.models,
    queryFn: async () => {
      const { data } = await api.get<ModelSummary[]>('/models')
      return data
    },
  })
}

export function useModel(name: string) {
  return useQuery({
    queryKey: queryKeys.model(name),
    queryFn: async () => {
      const { data } = await api.get<ProcessedModel>(`/models/${name}`)
      return data
    },
    enabled: !!name,
  })
}

export function useModelDimensions(name: string) {
  return useQuery({
    queryKey: queryKeys.modelDimensions(name),
    queryFn: async () => {
      const { data } = await api.get<Dimension[]>(`/models/${name}/dimensions`)
      return data
    },
    enabled: !!name,
  })
}

export function useModelMeasures(name: string) {
  return useQuery({
    queryKey: queryKeys.modelMeasures(name),
    queryFn: async () => {
      const { data } = await api.get<Measure[]>(`/models/${name}/measures`)
      return data
    },
    enabled: !!name,
  })
}

export function useModelMetrics(name: string) {
  return useQuery({
    queryKey: queryKeys.modelMetrics(name),
    queryFn: async () => {
      const { data } = await api.get<Metric[]>(`/models/${name}/metrics`)
      return data
    },
    enabled: !!name,
  })
}

export function useModelEntities(name: string) {
  return useQuery({
    queryKey: queryKeys.modelEntities(name),
    queryFn: async () => {
      const { data } = await api.get<Entity[]>(`/models/${name}/entities`)
      return data
    },
    enabled: !!name,
  })
}

// All dimensions/measures/metrics/entities across models
export function useAllDimensions() {
  return useQuery({
    queryKey: queryKeys.allDimensions,
    queryFn: async () => {
      const { data } = await api.get<DimensionWithContext[]>('/dimensions')
      return data
    },
  })
}

export function useAllMeasures() {
  return useQuery({
    queryKey: queryKeys.allMeasures,
    queryFn: async () => {
      const { data } = await api.get<MeasureWithContext[]>('/measures')
      return data
    },
  })
}

export function useAllMetrics() {
  return useQuery({
    queryKey: queryKeys.allMetrics,
    queryFn: async () => {
      const { data } = await api.get<MetricWithContext[]>('/metrics')
      return data
    },
  })
}

export function useAllEntities() {
  return useQuery({
    queryKey: queryKeys.allEntities,
    queryFn: async () => {
      const { data } = await api.get<(Entity & { model: string })[]>('/entities')
      return data
    },
  })
}

// Config
export function useConfig() {
  return useQuery({
    queryKey: queryKeys.config,
    queryFn: async () => {
      const { data } = await api.get<ConfigResponse>('/config')
      return data
    },
  })
}

export function useConfigRaw() {
  return useQuery({
    queryKey: queryKeys.configRaw,
    queryFn: async () => {
      const { data } = await api.get<{ content: string; path: string }>('/config/raw')
      return data
    },
  })
}

export function useUpdateConfigRaw() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (content: string) => {
      const { data } = await api.put<{ content: string; path: string }>('/config/raw', { content })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.config })
      queryClient.invalidateQueries({ queryKey: queryKeys.configRaw })
      queryClient.invalidateQueries({ queryKey: queryKeys.models })
      queryClient.invalidateQueries({ queryKey: queryKeys.stats })
    },
  })
}

// Build & Validate
export function useValidate() {
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<ValidateResult>('/validate')
      return data
    },
  })
}

export function useBuild() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (dryRun: boolean = false) => {
      const { data } = await api.post<BuildResult>(`/build?dry_run=${dryRun}`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.stats })
    },
  })
}

export function useReload() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<{ success: boolean; message: string; stats: Stats }>('/reload')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries()
    },
  })
}
