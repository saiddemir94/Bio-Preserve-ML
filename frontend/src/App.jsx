import { startTransition, useDeferredValue, useRef, useState } from "react";

const API_BASE_URL = "http://127.0.0.1:8000";
const SAMPLE_CSV = "sequence\nKWKLFKKIGAVLKVL\nLLKKLLKKLLKK\nRWKRLKRLKRLK\n";

const summaryCards = [
  { key: "totalSequences", label: "Total sequences" },
  { key: "approvedCount", label: "Approved" },
  { key: "rejectedCount", label: "Rejected" },
  { key: "averageProbability", label: "Average ML probability" },
];

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [summary, setSummary] = useState(null);
  const [results, setResults] = useState([]);
  const [downloadUrl, setDownloadUrl] = useState("");
  const [query, setQuery] = useState("");
  const [approvedOnly, setApprovedOnly] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);
  const deferredQuery = useDeferredValue(query);

  const filteredResults = results.filter((row) => {
    if (approvedOnly && row.final_status !== "Approved") {
      return false;
    }

    if (!deferredQuery.trim()) {
      return true;
    }

    const normalizedQuery = deferredQuery.trim().toLowerCase();
    return (
      row.sequence.toLowerCase().includes(normalizedQuery) ||
      row.final_status.toLowerCase().includes(normalizedQuery) ||
      row.compatible_foods.toLowerCase().includes(normalizedQuery) ||
      row.rule_notes.toLowerCase().includes(normalizedQuery)
    );
  });

  async function handleSubmit(event) {
    event.preventDefault();

    if (!selectedFile) {
      setErrorMessage("Please choose a CSV file before running the pipeline.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage("");

    const formData = new FormData();
    formData.append("sequence_file", selectedFile);

    try {
      const response = await fetch(`${API_BASE_URL}/api/run-pipeline`, {
        method: "POST",
        body: formData,
      });

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.detail || "Pipeline request failed.");
      }

      startTransition(() => {
        setSummary(payload.summary);
        setResults(payload.results);
        setDownloadUrl(`${API_BASE_URL}${payload.downloadUrl}`);
      });
    } catch (error) {
      setSummary(null);
      setResults([]);
      setDownloadUrl("");
      setErrorMessage(error.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleReset() {
    setSelectedFile(null);
    setSummary(null);
    setResults([]);
    setDownloadUrl("");
    setQuery("");
    setApprovedOnly(false);
    setErrorMessage("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  function handleFileSelection(nextFile) {
    if (!nextFile) {
      return;
    }

    const isCsv = nextFile.name.toLowerCase().endsWith(".csv");
    if (!isCsv) {
      setErrorMessage("Only CSV files are supported.");
      return;
    }

    setErrorMessage("");
    setSelectedFile(nextFile);
  }

  function handleDrop(event) {
    event.preventDefault();
    setDragActive(false);
    const nextFile = event.dataTransfer.files?.[0];
    handleFileSelection(nextFile);
  }

  const sampleCsvHref = `data:text/csv;charset=utf-8,${encodeURIComponent(SAMPLE_CSV)}`;

  return (
    <main className="page-shell">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">BioPreserve AI</p>
          <h1>Upload peptide candidates and get a clean screening report in one pass</h1>
          <p className="lede">
            This local dashboard is designed for quick lab-side review. Upload a CSV with
            a <code>sequence</code> column, run the pipeline, inspect approvals, and
            download a ready-to-share report.
          </p>

          <div className="steps">
            <div className="step">
              <span>1</span>
              <p>Download the sample CSV format if you need a template.</p>
            </div>
            <div className="step">
              <span>2</span>
              <p>Upload your peptide list and run the screening pipeline.</p>
            </div>
            <div className="step">
              <span>3</span>
              <p>Filter approved candidates and export the final CSV report.</p>
            </div>
          </div>
        </div>

        <form className="upload-panel" onSubmit={handleSubmit}>
          <div
            className={`dropzone ${dragActive ? "active" : ""}`}
            onDragEnter={(event) => {
              event.preventDefault();
              setDragActive(true);
            }}
            onDragOver={(event) => {
              event.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={(event) => {
              event.preventDefault();
              setDragActive(false);
            }}
            onDrop={handleDrop}
          >
            <p className="dropzone-label">Sequence CSV</p>
            <strong>Drag and drop your file here</strong>
            <p className="dropzone-copy">or choose it manually from your computer</p>

            <input
              id="sequenceFile"
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={(event) => {
                const nextFile = event.target.files?.[0] ?? null;
                handleFileSelection(nextFile);
              }}
            />

            <div className="dropzone-actions">
              <button className="primary-button" type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Running pipeline..." : "Run pipeline"}
              </button>

              <button className="secondary-button" type="button" onClick={handleReset}>
                Clear
              </button>
            </div>
          </div>

          <div className="helper-row">
            <a className="text-link" href={sampleCsvHref} download="sample_sequences.csv">
              Download sample CSV
            </a>
            <p className="hint">
              Expected header: <code>sequence</code>
            </p>
          </div>

          {selectedFile ? (
            <p className="file-chip">{selectedFile.name}</p>
          ) : (
            <p className="file-chip muted">No file selected yet</p>
          )}
        </form>
      </section>

      {errorMessage ? <section className="alert error">{errorMessage}</section> : null}

      {summary ? (
        <>
          <section className="summary-grid">
            {summaryCards.map((card) => (
              <article className="summary-card" key={card.key}>
                <span>{card.label}</span>
                <strong>{summary[card.key]}</strong>
              </article>
            ))}
          </section>

          <section className="toolbar">
            <div className="toolbar-copy">
              <h2>Candidate report</h2>
              <p>Use the filters below to focus on approved peptides or search specific rows.</p>
            </div>

            <div className="toolbar-actions">
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={approvedOnly}
                  onChange={(event) => setApprovedOnly(event.target.checked)}
                />
                <span>Approved only</span>
              </label>

              <input
                aria-label="Search results"
                className="search-input"
                placeholder="Search by sequence, status, note, or food"
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />

              <a className="primary-button" href={downloadUrl}>
                Download report
              </a>
            </div>
          </section>
        </>
      ) : null}

      {filteredResults.length > 0 ? (
        <section className="table-shell">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Sequence</th>
                  <th>Status</th>
                  <th>ML Probability</th>
                  <th>Length</th>
                  <th>Charge</th>
                  <th>Hydrophobicity</th>
                  <th>Key AA Ratio</th>
                  <th>Compatible Foods</th>
                  <th>Rule Notes</th>
                  <th>Food Notes</th>
                </tr>
              </thead>
              <tbody>
                {filteredResults.map((row) => (
                  <tr key={`${row.sequence}-${row.ml_probability}-${row.final_status}`}>
                    <td className="sequence">{row.sequence}</td>
                    <td>
                      <span className={`status-pill ${row.final_status.toLowerCase()}`}>
                        {row.final_status}
                      </span>
                    </td>
                    <td>{row.ml_probability}</td>
                    <td>{row.length}</td>
                    <td>{row.net_charge}</td>
                    <td>{row.hydrophobic_ratio}</td>
                    <td>{row.key_amino_acid_ratio}</td>
                    <td>{row.compatible_foods || "-"}</td>
                    <td>{row.rule_notes}</td>
                    <td>{row.food_notes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : summary ? (
        <section className="empty-state">
          <h2>No rows matched your current filter.</h2>
          <p>Try clearing the search or turning off the approved-only filter.</p>
        </section>
      ) : null}
    </main>
  );
}

export default App;
