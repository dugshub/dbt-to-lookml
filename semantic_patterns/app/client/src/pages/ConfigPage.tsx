import { useState } from 'react'
import { Save, AlertCircle, CheckCircle, RefreshCw } from 'lucide-react'
import { useConfigRaw, useUpdateConfigRaw, useValidate } from '../api'

export function ConfigPage() {
  const { data: configData, isLoading } = useConfigRaw()
  const updateConfig = useUpdateConfigRaw()
  const validate = useValidate()
  const [content, setContent] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  // Use local state if edited, otherwise use server data
  const displayContent = content ?? configData?.content ?? ''
  const hasChanges = content !== null && content !== configData?.content

  const handleSave = async () => {
    if (!content) return
    try {
      await updateConfig.mutateAsync(content)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
      setContent(null) // Reset to server state
    } catch {
      // Error handled by mutation
    }
  }

  const handleValidate = async () => {
    await validate.mutateAsync()
  }

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-gray-800 rounded w-40" />
        <div className="h-96 bg-gray-900 rounded-xl" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Configuration</h1>
          {configData?.path && (
            <p className="text-sm text-gray-500 mt-1">{configData.path}</p>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleValidate}
            disabled={validate.isPending}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-gray-800 text-gray-300 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw size={16} className={validate.isPending ? 'animate-spin' : ''} />
            Validate
          </button>
          <button
            onClick={handleSave}
            disabled={!hasChanges || updateConfig.isPending}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-600 text-white hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50"
          >
            {saved ? <CheckCircle size={16} /> : <Save size={16} />}
            {saved ? 'Saved' : 'Save'}
          </button>
        </div>
      </div>

      {/* Validation results */}
      {validate.data && (
        <div
          className={`p-4 rounded-lg border ${
            validate.data.valid
              ? 'bg-green-500/10 border-green-500/20'
              : 'bg-red-500/10 border-red-500/20'
          }`}
        >
          <div className="flex items-center gap-2 mb-2">
            {validate.data.valid ? (
              <>
                <CheckCircle size={18} className="text-green-400" />
                <span className="font-medium text-green-400">Valid</span>
              </>
            ) : (
              <>
                <AlertCircle size={18} className="text-red-400" />
                <span className="font-medium text-red-400">Invalid</span>
              </>
            )}
          </div>
          {validate.data.errors.length > 0 && (
            <ul className="list-disc list-inside text-sm text-red-400 space-y-1">
              {validate.data.errors.map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          )}
          {validate.data.warnings.length > 0 && (
            <ul className="list-disc list-inside text-sm text-yellow-400 space-y-1 mt-2">
              {validate.data.warnings.map((warn, i) => (
                <li key={i}>{warn}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Update error */}
      {updateConfig.error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
          <div className="flex items-center gap-2">
            <AlertCircle size={18} className="text-red-400" />
            <span className="text-red-400">
              {(updateConfig.error as Error).message || 'Failed to save'}
            </span>
          </div>
        </div>
      )}

      {/* Editor */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <textarea
          value={displayContent}
          onChange={(e) => setContent(e.target.value)}
          className="w-full h-[600px] p-4 bg-transparent text-gray-100 font-mono text-sm resize-none focus:outline-none"
          spellCheck={false}
        />
      </div>
    </div>
  )
}
