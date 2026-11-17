import { API } from './auth'
import { useState, useEffect } from 'react'
import './Downloads.css'

interface DownloadFile {
  name: string
  path: string
  type: string
  size: number
}

interface DownloadsProps {
  onBack: () => void
}

export default function Downloads({ onBack }: DownloadsProps) {
  const [files, setFiles] = useState<DownloadFile[]>([])
  const [loading, setLoading] = useState(true)

  const API_BASE = API

  useEffect(() => {
    fetchFiles()
  }, [])

  const fetchFiles = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/downloads`)
      const data = await res.json()
      setFiles(data.files || [])
    } catch (err) {
      console.error('Failed to fetch files:', err)
    } finally {
      setLoading(false)
    }
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'csv': return '📊'
      case 'xlsx': return '📈'
      case 'pdf': return '📄'
      case 'markdown': return '📝'
      default: return '📁'
    }
  }

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'csv': return 'CSV'
      case 'xlsx': return 'Excel'
      case 'pdf': return 'PDF'
      case 'markdown': return 'Markdown'
      default: return type
    }
  }

  if (loading) {
    return <div className="loading">Cargando archivos...</div>
  }

  return (
    <div className="downloads">
      <header className="downloads-header">
        <button className="back-btn" onClick={onBack}>Volver al Asistente</button>
        <h1>Archivos Descargables</h1>
        <p>Datos y documentacion para analisis</p>
      </header>

      <div className="downloads-content">
        <section className="download-section">
          <h2>Documentacion</h2>
          <div className="file-grid">
            {files.filter(f => f.type === 'pdf' || f.type === 'markdown').map((file) => (
              <div key={file.path} className="file-card">
                <div className="file-icon">{getTypeIcon(file.type)}</div>
                <div className="file-info">
                  <h3>{file.name}</h3>
                  <p>{getTypeLabel(file.type)} - {formatSize(file.size)}</p>
                </div>
                <a
                  href={`${API_BASE}/api/downloads/${file.path}`}
                  download
                  className="download-btn"
                >
                  Descargar
                </a>
              </div>
            ))}
          </div>
        </section>

        <section className="download-section">
          <h2>Datos para Power BI</h2>
          <div className="file-grid">
            {files.filter(f => f.type === 'xlsx').map((file) => (
              <div key={file.path} className="file-card featured">
                <div className="file-icon">{getTypeIcon(file.type)}</div>
                <div className="file-info">
                  <h3>{file.name}</h3>
                  <p>{getTypeLabel(file.type)} - {formatSize(file.size)}</p>
                </div>
                <a
                  href={`${API_BASE}/api/downloads/${file.path}`}
                  download
                  className="download-btn"
                >
                  Descargar
                </a>
              </div>
            ))}
          </div>
        </section>

        <section className="download-section">
          <h2>CSV (para Power BI)</h2>
          <div className="file-grid">
            {files.filter(f => f.type === 'csv').map((file) => (
              <div key={file.path} className="file-card">
                <div className="file-icon">{getTypeIcon(file.type)}</div>
                <div className="file-info">
                  <h3>{file.name}</h3>
                  <p>{getTypeLabel(file.type)} - {formatSize(file.size)}</p>
                </div>
                <a
                  href={`${API_BASE}/api/downloads/${file.path}`}
                  download
                  className="download-btn"
                >
                  Descargar
                </a>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
