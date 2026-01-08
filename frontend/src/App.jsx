import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(false)
  const [expandedJob, setExpandedJob] = useState(null)

  // Pagination State
  const [nextPage, setNextPage] = useState(null)
  const [prevPage, setPrevPage] = useState(null)
  const [count, setCount] = useState(0)

  const [filters, setFilters] = useState({
    skills: '',
    seniority: '',
    salary_min: ''
  })

  // Scraper State
  const [scrapeLoading, setScrapeLoading] = useState(false)
  const [scrapeMessage, setScrapeMessage] = useState('')

  // --- 1. Fetch Jobs (Handles Pagination URL or Filters) ---
  const fetchJobs = async (url = null) => {
    setLoading(true)
    setExpandedJob(null) // Close any open jobs

    try {
      let fetchUrl = url

      // If no specific URL provided (e.g. Next button), build one from filters
      if (!fetchUrl) {
        const params = new URLSearchParams(filters)
        for (const [key, value] of params.entries()) {
          if (!value) params.delete(key)
        }
        fetchUrl = `http://127.0.0.1:8000/api/jobs/?${params}`
      }

      const response = await fetch(fetchUrl)
      const data = await response.json()

      setJobs(data.results || [])
      setNextPage(data.next)
      setPrevPage(data.previous)
      setCount(data.count)

    } catch (error) {
      console.error("Failed to fetch jobs:", error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchJobs()
  }, [])

  // --- 2. Helper: Format Date (e.g. "2 days ago") ---
  const formatDate = (dateString) => {
    if (!dateString) return ''
    const date = new Date(dateString)
    const now = new Date()
    const diffTime = Math.abs(now - date)
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))

    if (diffDays <= 1) return "🔥 Today"
    if (diffDays === 2) return "Yesterday"
    return `${diffDays} days ago`
  }

  // --- 3. Scraper Logic ---
  const handleScrape = async () => {
    setScrapeLoading(true)
    try {
      const response = await fetch('http://127.0.0.1:8000/api/scrape/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword: filters.skills || 'Python', location: 'Europe' })
      })
      const data = await response.json()
      setScrapeMessage(data.message)
    } catch (error) {
      setScrapeMessage("Failed to start scraper.")
    } finally {
      setScrapeLoading(false)
    }
  }

  const handleInputChange = (e) => setFilters({ ...filters, [e.target.name]: e.target.value })
  const toggleJob = (id) => setExpandedJob(expandedJob === id ? null : id)

  return (
    <div className="container">
      <h1>🚀 Remote Jobs Board <span style={{fontSize:'1rem', color:'#6b7280'}}>({count} active jobs)</span></h1>

      {/* --- Filter Bar --- */}
      <div className="filters">
        <input name="skills" placeholder="Skill (e.g. React)" value={filters.skills} onChange={handleInputChange} />
        <select name="seniority" value={filters.seniority} onChange={handleInputChange}>
          <option value="">Any Level</option>
          <option value="Junior">Junior</option>
          <option value="Mid-Level">Mid-Level</option>
          <option value="Senior">Senior</option>
          <option value="Lead">Lead</option>
        </select>
        <input name="salary_min" type="number" placeholder="Min Salary ($)" value={filters.salary_min} onChange={handleInputChange} />
        <button className="search-btn" onClick={() => fetchJobs()}>Search</button>
      </div>

      {/* --- Jobs List --- */}
      {loading ? (
        <div style={{textAlign: 'center', padding: '40px', color: '#6b7280'}}>Loading fresh jobs...</div>
      ) : (
        <div>
          {jobs.length > 0 ? (
            jobs.map(job => (
              <div key={job.id} className="job-card" onClick={() => toggleJob(job.id)}>
                <div className="job-header">
                  <div>
                    <h2 className="job-title">{job.title}</h2>
                    <div className="job-company">
                      <span>🏢 {job.company}</span>
                      <span>📍 {job.location}</span>
                    </div>
                  </div>
                  <span className="job-date">{formatDate(job.posted_at)}</span>
                </div>

                <div className="badges">
                  <span className="badge badge-seniority">{job.seniority}</span>
                  {job.salary_min && (
                    <span className="badge badge-salary">
                      {job.currency} {job.salary_min.toLocaleString()}
                    </span>
                  )}
                  {job.skills.slice(0, 4).map(skill => (
                    <span key={skill} className="badge badge-skill">{skill}</span>
                  ))}
                </div>

                {/* Expanded Details */}
                {expandedJob === job.id && (
                  <div className="job-description">
                    <p>{job.description}</p>
                    <div className="job-actions">
                      <a href={job.url} target="_blank" className="apply-btn">Apply on LinkedIn ↗</a>
                    </div>
                  </div>
                )}
              </div>
            ))
          ) : (
            <div style={{textAlign: 'center', padding: '40px', background: 'white', borderRadius: '12px'}}>
              <h3>No jobs found.</h3>
              <button className="search-btn" onClick={handleScrape} disabled={scrapeLoading}>
                {scrapeLoading ? "Bot is working..." : "Start Scraper"}
              </button>
              {scrapeMessage && <p>{scrapeMessage}</p>}
            </div>
          )}
        </div>
      )}

      {/* --- Pagination Controls --- */}
      <div className="pagination">
        <button className="page-btn" disabled={!prevPage} onClick={() => fetchJobs(prevPage)}>
          ← Previous
        </button>
        <span style={{color: '#6b7280', fontSize: '0.9rem'}}>
           Showing {jobs.length} results
        </span>
        <button className="page-btn" disabled={!nextPage} onClick={() => fetchJobs(nextPage)}>
          Next →
        </button>
      </div>
    </div>
  )
}

export default App