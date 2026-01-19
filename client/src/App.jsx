// App.jsx
import React, { useState } from "react";
import "./App.css";

function App() {
  const [githubUrl, setGithubUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [error, setError] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!githubUrl.trim()) {
      setError("Please enter a GitHub URL.");
      return;
    }

    setLoading(true);
    setResults([]);
    setError(null);

    try {
      const resp = await fetch(
        `/api/similar?url=${encodeURIComponent(githubUrl)}`
      );

      // If the backend crashes / returns HTML, this prevents `.json()` from throwing a confusing error
      const contentType = resp.headers.get("content-type") || "";
      const data = contentType.includes("application/json")
        ? await resp.json()
        : { error: await resp.text() };

      if (!resp.ok) {
        throw new Error(
          data?.error || `Request failed (${resp.status} ${resp.statusText})`
        );
      }

      // Map backend -> UI
      const realResults = (data.results || []).map((r) => ({
        repo_name: r.full_name,
        cosine_similarity: r.score,
        html_url: r.html_url,
      }));

      setResults(realResults);
    } catch (err) {
      setError(err?.message || "Failed to fetch repositories. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const renderStars = (similarity) => {
    const starCount = Math.max(1, Math.round((similarity || 0) * 5));
    return Array.from({ length: starCount }, () => "⭐").join("");
  };

  return (
    <div className="container">
      <header className="header">
        <h1>RepoFinder</h1>
        <p>Enter a GitHub repository URL to discover similar projects.</p>
      </header>

      <form onSubmit={handleSubmit} className="form">
        <input
          type="text"
          className="url-input"
          value={githubUrl}
          onChange={(e) => setGithubUrl(e.target.value)}
          placeholder="e.g., https://github.com/facebook/react"
        />
        <button type="submit" className="generate-button" disabled={loading}>
          {loading ? "Generating..." : "Generate"}
        </button>
      </form>

      {loading && (
        <div className="loading">
          <div className="spinner"></div>
          <p>Analyzing repositories...</p>
        </div>
      )}

      {error && <div className="error-message">{error}</div>}

      {results.length > 0 && (
        <div className="results-container">
          <h2>Top 5 Similar Repositories</h2>
          <ul className="results-list">
            {results.map((repo) => (
              <li key={repo.repo_name} className="result-item">
                <span className="repo-name">
                  {repo.html_url ? (
                    <a href={repo.html_url} target="_blank" rel="noreferrer">
                      {repo.repo_name}
                    </a>
                  ) : (
                    repo.repo_name
                  )}
                </span>
                <span className="stars">
                  {renderStars(repo.cosine_similarity)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default App;
