// Config types mirroring Python SPConfig

export interface OptionsConfig {
  dialect: string
  pop_strategy: string
  date_selector: boolean
  convert_tz: boolean
  view_prefix: string
  explore_prefix: string
}

export interface ModelConfig {
  name: string
  connection: string
  label?: string
}

export interface ExploreConfig {
  fact: string
  name?: string
  label?: string
  description?: string
  join_exclusions: string[]
  joined_facts: string[]
}

export interface LookerConfig {
  enabled: boolean
  model: ModelConfig
  explores: ExploreConfig[]
  repo: string
  branch: string
  path: string
  protected_branches: string[]
  commit_message: string
  base_url: string
  project_id: string
  sync_dev: boolean
}

export interface OutputOptionsConfig {
  clean?: string
  manifest: boolean
}

export interface SPConfig {
  input: string
  output: string
  schema: string
  format: string
  project: string
  options: OptionsConfig
  output_options: OutputOptionsConfig
  looker: LookerConfig
}

export interface ConfigResponse {
  path: string
  config: SPConfig
}

export interface ValidateResult {
  valid: boolean
  errors: string[]
  warnings: string[]
}

export interface BuildResult {
  success: boolean
  message: string
  files: string[]
  stats: Record<string, number>
  errors: string[]
}
