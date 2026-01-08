import { Routes, Route } from 'react-router-dom'
import { Shell } from './components/layout'
import {
  DashboardPage,
  ModelsPage,
  ModelDetailPage,
  DimensionsPage,
  MeasuresPage,
  MetricsPage,
  ExploresPage,
  ConfigPage,
} from './pages'

function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/models" element={<ModelsPage />} />
        <Route path="/models/:name" element={<ModelDetailPage />} />
        <Route path="/dimensions" element={<DimensionsPage />} />
        <Route path="/measures" element={<MeasuresPage />} />
        <Route path="/metrics" element={<MetricsPage />} />
        <Route path="/explores" element={<ExploresPage />} />
        <Route path="/config" element={<ConfigPage />} />
      </Routes>
    </Shell>
  )
}

export default App
