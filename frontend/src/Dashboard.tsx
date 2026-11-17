import { API } from './auth'
import { useState, useEffect } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js'
import { Bar, Pie, Doughnut } from 'react-chartjs-2'
import './Dashboard.css'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
)

interface AnalyticsData {
  total: number
  by_province: { name: string; count: number }[]
  by_city: { name: string; count: number }[]
  by_cuisine: { name: string; count: number }[]
  by_category: { name: string; count: number }[]
  by_source: { name: string; count: number }[]
  by_confidence: { name: string; count: number }[]
  with_coords: number
  with_phone: number
  with_rating: number
  with_address: number
  gf_count: number
  veg_count: number
  vegan_count: number
  null_name: number
  null_province: number
  null_city: number
}

interface DashboardProps {
  onBack: () => void
}

const COLORS = ['#7A8B6F', '#C4815A', '#E8DDD3', '#95A88A', '#D49A78', '#8B7E74', '#FDF6EC', '#3D3229']

export default function Dashboard({ onBack }: DashboardProps) {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'overview' | 'geography' | 'quality'>('overview')

  const API_BASE = API

  useEffect(() => {
    fetchAnalytics()
  }, [])

  const fetchAnalytics = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/analytics`)
      const analyticsData = await res.json()
      setData(analyticsData)
    } catch (err) {
      console.error('Failed to fetch analytics:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="loading">Cargando datos...</div>
  }

  if (!data) {
    return <div className="loading">Error al cargar datos</div>
  }

  const completenessPercent = Math.round(((data.with_coords + data.with_phone + data.with_address) / (data.total * 3)) * 100)

  return (
    <div className="dashboard">
      <header className="dash-header">
        <button className="back-btn" onClick={onBack}>Volver al Asistente</button>
        <h1>Dashboard Analitico</h1>
        <p>GastronomIA - Análisis de datos</p>
      </header>

      <nav className="dash-tabs">
        <button className={activeTab === 'overview' ? 'active' : ''} onClick={() => setActiveTab('overview')}>Resumen</button>
        <button className={activeTab === 'geography' ? 'active' : ''} onClick={() => setActiveTab('geography')}>Geografia</button>
        <button className={activeTab === 'quality' ? 'active' : ''} onClick={() => setActiveTab('quality')}>Calidad</button>
      </nav>

      {activeTab === 'overview' && (
        <section className="dash-section">
          <div className="kpi-grid">
            <div className="kpi-card">
              <h3>Total Restaurantes</h3>
              <p className="kpi-value">{data.total.toLocaleString()}</p>
            </div>
            <div className="kpi-card">
              <h3>Provincias</h3>
              <p className="kpi-value">{data.by_province.length}</p>
            </div>
            <div className="kpi-card">
              <h3>Ciudades</h3>
              <p className="kpi-value">{data.by_city.length}</p>
            </div>
            <div className="kpi-card">
              <h3>Tipos de Cocina</h3>
              <p className="kpi-value">{data.by_cuisine.length}</p>
            </div>
            <div className="kpi-card">
              <h3>Con Coordenadas</h3>
              <p className="kpi-value">{data.with_coords} <span className="kpi-sub">({Math.round(data.with_coords/data.total*100)}%)</span></p>
            </div>
            <div className="kpi-card">
              <h3>Sin TACC</h3>
              <p className="kpi-value">{data.gf_count}</p>
            </div>
            <div className="kpi-card">
              <h3>Vegetariano</h3>
              <p className="kpi-value">{data.veg_count}</p>
            </div>
            <div className="kpi-card">
              <h3>Vegano</h3>
              <p className="kpi-value">{data.vegan_count}</p>
            </div>
          </div>

          <div className="chart-row">
            <div className="chart-card">
              <h3>Restaurantes por Provincia</h3>
              <Bar data={{
                labels: data.by_province.map(p => p.name),
                datasets: [{
                  label: 'Restaurantes',
                  data: data.by_province.map(p => p.count),
                  backgroundColor: COLORS.slice(0, data.by_province.length),
                }]
              }} options={{ responsive: true, plugins: { legend: { display: false } } }} />
            </div>
            <div className="chart-card">
              <h3>Por Tipo de Cocina</h3>
              <Doughnut data={{
                labels: data.by_cuisine.slice(0, 8).map(c => c.name),
                datasets: [{
                  data: data.by_cuisine.slice(0, 8).map(c => c.count),
                  backgroundColor: COLORS,
                }]
              }} options={{ responsive: true, plugins: { legend: { position: 'right' } } }} />
            </div>
          </div>

          <div className="chart-row">
            <div className="chart-card">
              <h3>Por Categoria</h3>
              <Bar data={{
                labels: data.by_category.map(c => c.name),
                datasets: [{
                  label: 'Restaurantes',
                  data: data.by_category.map(c => c.count),
                  backgroundColor: '#7A8B6F',
                }]
              }} options={{ responsive: true, indexAxis: 'y', plugins: { legend: { display: false } } }} />
            </div>
            <div className="chart-card">
              <h3>Por Fuente de Datos</h3>
              <Pie data={{
                labels: data.by_source.map(s => s.name),
                datasets: [{
                  data: data.by_source.map(s => s.count),
                  backgroundColor: COLORS,
                }]
              }} options={{ responsive: true, plugins: { legend: { position: 'right' } } }} />
            </div>
          </div>
        </section>
      )}

      {activeTab === 'geography' && (
        <section className="dash-section">
          <h2>Distribucion Geografica</h2>
          <div className="chart-row">
            <div className="chart-card wide">
              <h3>Top 15 Ciudades</h3>
              <Bar data={{
                labels: data.by_city.map(c => c.name),
                datasets: [{
                  label: 'Restaurantes',
                  data: data.by_city.map(c => c.count),
                  backgroundColor: '#C4815A',
                }]
              }} options={{ responsive: true, plugins: { legend: { display: false } } }} />
            </div>
          </div>
        </section>
      )}

      {activeTab === 'quality' && (
        <section className="dash-section">
          <h2>Indicadores de Calidad</h2>
          <div className="kpi-grid">
            <div className="kpi-card quality">
              <h3>Completitud General</h3>
              <p className="kpi-value">{completenessPercent}%</p>
            </div>
            <div className="kpi-card">
              <h3>Con Telefono</h3>
              <p className="kpi-value">{Math.round(data.with_phone/data.total*100)}%</p>
            </div>
            <div className="kpi-card">
              <h3>Con Coordenadas</h3>
              <p className="kpi-value">{Math.round(data.with_coords/data.total*100)}%</p>
            </div>
            <div className="kpi-card">
              <h3>Sin Rating</h3>
              <p className="kpi-value warning">0%</p>
            </div>
          </div>

          <div className="chart-row">
            <div className="chart-card">
              <h3>Nivel de Confianza</h3>
              <Pie data={{
                labels: data.by_confidence.map(c => c.name),
                datasets: [{
                  data: data.by_confidence.map(c => c.count),
                  backgroundColor: ['#7A8B6F', '#C4815A', '#E8DDD3'],
                }]
              }} options={{ responsive: true }} />
            </div>
            <div className="chart-card">
              <h3>Campos con Nulos</h3>
              <Bar data={{
                labels: ['Nombre', 'Provincia', 'Ciudad'],
                datasets: [{
                  label: 'Registros nulos',
                  data: [data.null_name, data.null_province, data.null_city],
                  backgroundColor: '#C4815A',
                }]
              }} options={{ responsive: true, plugins: { legend: { display: false } } }} />
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
