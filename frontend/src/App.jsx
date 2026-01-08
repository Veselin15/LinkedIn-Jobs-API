import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [jobs, setJobs] = useState([])
  const [filters, setFilters] = useState({
    skills: '',
    seniority: '',
    salary_min: ''
  })
  const [loading, setLoading] = useState(false)
  const [scrapeLoading, setScrapeLoading] = useState(false)
  const [scrapeMessage, setScrapeMessage] = useState('')

  // 1. Function to Fetch Jobs
  const fetchJobs = async () => {
    setLoading(true)
    setScrapeMessage('') // Clear old messages
    try {
      // Build query string (e.g. ?skills=Python&seniority=Junior)
      const params = new URLSearchParams(filters)
      // Remove empty keys
      for (const [key, value] of params.entries()) {
        if (!value) params.delete(key)
      }

      const response = await fetch(`http://127.0.0.1:8000/api/jobs/?${params}`)
      const data = await response.json()

      setJobs(data.results || [])
    } catch (error) {
      console.error("Failed to fetch jobs:", error)
    } finally {
      setLoading(false)
    }
  }

  // 2. Initial Fetch on Load
  useEffect(() => {
    fetchJobs()
  }, [])

  // 3. Function to Trigger Scraper
  const handleScrape = async () => {
    setScrapeLoading(true)
    try {
      const response = await fetch('http://127.0.0.1:8000/api/scrape/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          keyword: filters.skills || 'Python',
          location: 'Europe' // Default
        })
      })
      const data = await response.json()
      setScrapeMessage(data.message + " " + (data.note || ""))
    } catch (error) {
      setScrapeMessage("Failed to start scraper.")
    } finally {
      setScrapeLoading(false)
    }
  }

  const handleInputChange = (e) => {
    setFilters({ ...filters, [e.target.name]: e.target.value })
  }

  return (
    <div className="container">
      <h1>🚀 Remote Jobs Board</h1>

      {/* --- Filter Section --- */}
      <div className="filters">
        <input
          name="skills"
          placeholder="Skill (e.g. Python)"
          value={filters.skills}
          onChange={handleInputChange}
        />
        <select name="seniority" value={filters.seniority} onChange={handleInputChange}>
          <option value="">Any Level</option>
          <option value="Junior">Junior</option>
          <option value="Mid-Level">Mid-Level</option>
          <option value="Senior">Senior</option>
          <option value="Lead">Lead / Manager</option>
        </select>
        <input
          name="salary_min"
          type="number"
          placeholder="Min Salary ($)"
          value={filters.salary_min}
          onChange={handleInputChange}
        />
        <button className="search-btn" onClick={fetchJobs}>Search</button>
      </div>

      {/* --- Jobs List --- */}
      {loading ? (
        <p style={{textAlign: 'center'}}>Loading jobs...</p>
      ) : (
        <div>
          {jobs.length > 0 ? (
            jobs.map(job => (
              <div key={job.id} className="job-card">
                <div className="job-header">
                  <div>
                    <h2 className="job-title">{job.title}</h2>
                    <div className="job-company">{job.company} • {job.location}</div>
                  </div>
                  <a href={job.url} target="_blank" rel="noopener noreferrer" className="apply-btn">
                    Apply Now ↗
                  </a>
                </div>

                <div className="badges">
                  <span className="badge badge-seniority">{job.seniority || 'Not Specified'}</span>
                  {job.salary_min && (
                    <span className="badge badge-salary">
                      {job.currency} {job.salary_min.toLocaleString()}
                      {job.salary_max && ` - ${job.salary_max.toLocaleString()}`}
                    </span>
                  )}
                  {job.skills.slice(0, 5).map(skill => (
                    <span key={skill} className="badge badge-skill">{skill}</span>
                  ))}
                </div>
              </div>
            ))
          ) : (
            // --- Empty State (Trigger Scraper) ---
            <div className="empty-state">
              <h3>No jobs found matching your criteria.</h3>
              <p>Would you like to ask our bots to find some?</p>

              <button
                className="scrape-btn"
                onClick={handleScrape}
                disabled={scrapeLoading}
              >
                {scrapeLoading ? "Bot is Starting..." : "🔎 Start Live Scraper"}
              </button>

              {scrapeMessage && (
                <div style={{marginTop: '20px', padding: '10px', background: '#e0f2fe', borderRadius: '8px', color: '#0369a1'}}>
                  {scrapeMessage}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default App