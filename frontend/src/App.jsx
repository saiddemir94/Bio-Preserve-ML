import { startTransition, useDeferredValue, useEffect, useRef, useState } from "react";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const SAMPLE_CSV = "sequence\nKWKLFKKIGAVLKVL\nLLKKLLKKLLKK\nRWKRLKRLKRLK\n";
const DEFAULT_OPTIONS = {
  foods: [
    "Peynir",
    "Yogurt",
    "Taze Et",
    "Fermente Et (Sucuk)",
    "Meyve Suyu",
    "Bitkisel Protein Bazli Urun",
  ],
  pathogens: ["Listeria monocytogenes", "Salmonella", "E. coli"],
};
const ANALYSIS_MODES = [
  {
    value: "general",
    label: "Genel tarama",
    description: "Gıda veya patojen zorunlu olmadan tüm adayları değerlendirir.",
  },
  {
    value: "food",
    label: "Gıda odaklı",
    description: "Adayları seçilen gıda matrisi için filtreler.",
  },
  {
    value: "pathogen",
    label: "Patojen odaklı",
    description: "Adayları seçilen hedef mikroorganizmaya göre filtreler.",
  },
  {
    value: "combined",
    label: "Gıda + patojen",
    description: "Hem gıda matrisi hem hedef patojen birlikte değerlendirilir.",
  },
];

const summaryCards = [
  { key: "totalSequences", label: "Toplam peptit" },
  { key: "approvedCount", label: "Uygun aday" },
  { key: "rejectedCount", label: "Elenen aday" },
  { key: "averageProbability", label: "Ortalama ML skoru" },
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
  const [options, setOptions] = useState(DEFAULT_OPTIONS);
  const [analysisMode, setAnalysisMode] = useState("general");
  const [selectedFood, setSelectedFood] = useState("");
  const [targetPathogen, setTargetPathogen] = useState("");
  const fileInputRef = useRef(null);
  const deferredQuery = useDeferredValue(query);

  useEffect(() => {
    async function loadOptions() {
      try {
        const response = await fetch(`${API_BASE_URL}/api/options`);
        if (!response.ok) {
          return;
        }

        const payload = await response.json();
        setOptions(payload);
      } catch {
        setOptions(DEFAULT_OPTIONS);
      }
    }

    loadOptions();
  }, []);

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
      row.target_food.toLowerCase().includes(normalizedQuery) ||
      row.target_pathogen.toLowerCase().includes(normalizedQuery) ||
      row.compatible_foods.toLowerCase().includes(normalizedQuery) ||
      row.rule_notes.toLowerCase().includes(normalizedQuery)
    );
  });

  async function handleSubmit(event) {
    event.preventDefault();

    if (!selectedFile) {
      setErrorMessage("Taramayı başlatmadan önce bir CSV dosyası seçmelisiniz.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage("");

    const shouldUseFood = analysisMode === "food" || analysisMode === "combined";
    const shouldUsePathogen = analysisMode === "pathogen" || analysisMode === "combined";

    const formData = new FormData();
    formData.append("sequence_file", selectedFile);
    formData.append("selected_food", shouldUseFood ? selectedFood : "");
    formData.append("target_pathogen", shouldUsePathogen ? targetPathogen : "");

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
    setAnalysisMode("general");
    setSelectedFood("");
    setTargetPathogen("");
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
      setErrorMessage("Sadece CSV dosyaları destekleniyor.");
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
  const showFoodSelect = analysisMode === "food" || analysisMode === "combined";
  const showPathogenSelect = analysisMode === "pathogen" || analysisMode === "combined";

  return (
    <main className="page-shell">
      <section className="hero">
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
            <strong>Peptit listenizi CSV olarak yükleyin</strong>
            <p className="dropzone-copy">
              Dosyada <code>sequence</code> adlı bir sütun olmalı ve her satırda tek bir
              peptit sekansı bulunmalıdır.
            </p>

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

            <div className="target-grid">
              <fieldset className="analysis-mode">
                <legend>Analiz odağı</legend>
                <div className="mode-options">
                  {ANALYSIS_MODES.map((mode) => (
                    <label
                      className={`mode-card ${analysisMode === mode.value ? "selected" : ""}`}
                      key={mode.value}
                    >
                      <input
                        type="radio"
                        name="analysisMode"
                        value={mode.value}
                        checked={analysisMode === mode.value}
                        onChange={(event) => {
                          setAnalysisMode(event.target.value);
                          setSelectedFood(options.foods?.[0] ?? DEFAULT_OPTIONS.foods[0]);
                          setTargetPathogen(options.pathogens?.[0] ?? DEFAULT_OPTIONS.pathogens[0]);
                        }}
                      />
                      <span>{mode.label}</span>
                      <small>{mode.description}</small>
                    </label>
                  ))}
                </div>
              </fieldset>

              {showFoodSelect ? (
                <label>
                  <span>Hedef gıda</span>
                  <select
                    value={selectedFood || options.foods?.[0] || DEFAULT_OPTIONS.foods[0]}
                    onChange={(event) => setSelectedFood(event.target.value)}
                  >
                    {options.foods.map((food) => (
                      <option key={food} value={food}>
                        {food}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}

              {showPathogenSelect ? (
                <label>
                  <span>Hedef patojen</span>
                  <select
                    value={targetPathogen || options.pathogens?.[0] || DEFAULT_OPTIONS.pathogens[0]}
                    onChange={(event) => setTargetPathogen(event.target.value)}
                  >
                    {options.pathogens.map((pathogen) => (
                      <option key={pathogen} value={pathogen}>
                        {pathogen}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
            </div>

            <div className="dropzone-actions">
              <button className="primary-button" type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Tarama çalışıyor..." : "Taramayı başlat"}
              </button>

              <button className="secondary-button" type="button" onClick={handleReset}>
                Temizle
              </button>
            </div>
          </div>

          <div className="helper-row">
            <a className="text-link" href={sampleCsvHref} download="sample_sequences.csv">
              Örnek CSV indir
            </a>
            <p className="hint">
              Beklenen sütun: <code>sequence</code>
            </p>
          </div>

          {selectedFile ? (
            <p className="file-chip">{selectedFile.name}</p>
          ) : (
            <p className="file-chip muted">Henüz dosya seçilmedi</p>
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
              <h2>Aday raporu</h2>
              <p>Uygun adayları filtreleyin veya belirli satırlar içinde arama yapın.</p>
            </div>

            <div className="toolbar-actions">
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={approvedOnly}
                  onChange={(event) => setApprovedOnly(event.target.checked)}
                />
                <span>Sadece uygunlar</span>
              </label>

              <input
                aria-label="Search results"
                className="search-input"
                placeholder="Sekans, durum, not veya gıdaya göre ara"
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />

              <a className="primary-button" href={downloadUrl}>
                Raporu indir
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
                  <th>Sekans</th>
                  <th>Hedef gıda</th>
                  <th>Hedef patojen</th>
                  <th>Durum</th>
                  <th>ML skoru</th>
                  <th>Uzunluk</th>
                  <th>Yük</th>
                  <th>Hidrofobiklik</th>
                  <th>Kritik AA oranı</th>
                  <th>Uyumlu gıdalar</th>
                  <th>Kural notu</th>
                  <th>Gıda notu</th>
                </tr>
              </thead>
              <tbody>
                {filteredResults.map((row) => (
                  <tr key={`${row.sequence}-${row.ml_probability}-${row.final_status}`}>
                    <td className="sequence">{row.sequence}</td>
                    <td>{row.target_food}</td>
                    <td>{row.target_pathogen}</td>
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
          <h2>Filtreye uygun satır bulunamadı.</h2>
          <p>Aramayı temizlemeyi veya sadece uygunlar filtresini kapatmayı deneyin.</p>
        </section>
      ) : null}
    </main>
  );
}

export default App;
