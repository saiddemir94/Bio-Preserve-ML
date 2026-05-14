import { startTransition, useDeferredValue, useEffect, useRef, useState } from "react";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
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
    description: "Tüm adayları genel biyolojik uygunluk ve ML skoruna göre değerlendirir.",
  },
  {
    value: "food",
    label: "Gıda odaklı",
    description: "Adayları seçilen gıda matrisi için filtreler.",
  },
  {
    value: "pathogen",
    label: "Patojen odaklı",
    description: "Adayları seçilen hedef mikroorganizmaya göre değerlendirir.",
  },
  {
    value: "combined",
    label: "Gıda + patojen",
    description: "Hem gıda matrisi hem hedef patojen birlikte dikkate alınır.",
  },
];
const DATA_SOURCES = [
  {
    value: "system",
    label: "Sistem peptit havuzu",
    description: "DBAASP tabanlı mevcut aday havuzu analiz edilir.",
  },
  {
    value: "csv",
    label: "Kendi CSV dosyam",
    description: "sequence sütununa sahip CSV dosyasıyla özel analiz yapılır.",
  },
];

const summaryCards = [
  { key: "totalSequences", label: "Toplam peptit" },
  { key: "approvedCount", label: "Uygun aday" },
  { key: "rejectedCount", label: "Elenen aday" },
  {
    key: "averageProbability",
    label: "Ortalama ML skoru",
    tooltip:
      "0–1 arasında bir değer. Yalnızca biyolojik filtreleri geçen peptitlerin Random Forest tahmin olasılıklarının ortalamasıdır. Yüksek değer, modelin o adayı antimikrobiyal peptit olarak görme olasılığının yüksek olduğunu gösterir.",
  },
];

const EMPTY_FOOD_FORM = { product: "", pH: "", salt_ratio: "", temperature: "", fat_content: "medium" };
const EMPTY_PATHOGEN_FORM = { name: "", min_charge: "", hydrophobicity_min: "", hydrophobicity_max: "", gram_type: "negative" };

function App() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [summary, setSummary] = useState(null);
  const [results, setResults] = useState([]);
  const [downloadUrl, setDownloadUrl] = useState("");
  const [query, setQuery] = useState("");
  const [approvedOnly, setApprovedOnly] = useState(false);
  const [options, setOptions] = useState(DEFAULT_OPTIONS);
  const [analysisMode, setAnalysisMode] = useState("general");
  const [selectedFood, setSelectedFood] = useState("");
  const [targetPathogen, setTargetPathogen] = useState("");
  const [dataSource, setDataSource] = useState("system");
  const [selectedFile, setSelectedFile] = useState(null);
  const fileInputRef = useRef(null);
  const deferredQuery = useDeferredValue(query);

  const [showFoodForm, setShowFoodForm] = useState(false);
  const [showPathogenForm, setShowPathogenForm] = useState(false);
  const [foodForm, setFoodForm] = useState(EMPTY_FOOD_FORM);
  const [pathogenForm, setPathogenForm] = useState(EMPTY_PATHOGEN_FORM);
  const [addMessage, setAddMessage] = useState("");

  async function loadOptions() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/options`);
      if (!response.ok) return;
      const payload = await response.json();
      setOptions(payload);
    } catch {
      setOptions(DEFAULT_OPTIONS);
    }
  }

  useEffect(() => { loadOptions(); }, []);

  async function handleAddFood(event) {
    event.preventDefault();
    setAddMessage("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/food-matrices`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product: foodForm.product,
          pH: parseFloat(foodForm.pH),
          salt_ratio: parseFloat(foodForm.salt_ratio),
          temperature: parseFloat(foodForm.temperature),
          fat_content: foodForm.fat_content,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail);
      setAddMessage(payload.message);
      setFoodForm(EMPTY_FOOD_FORM);
      setShowFoodForm(false);
      await loadOptions();
    } catch (err) {
      setAddMessage(err.message);
    }
  }

  async function handleAddPathogen(event) {
    event.preventDefault();
    setAddMessage("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/pathogens`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: pathogenForm.name,
          min_charge: parseInt(pathogenForm.min_charge),
          hydrophobicity_min: parseFloat(pathogenForm.hydrophobicity_min),
          hydrophobicity_max: parseFloat(pathogenForm.hydrophobicity_max),
          gram_type: pathogenForm.gram_type,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail);
      setAddMessage(payload.message);
      setPathogenForm(EMPTY_PATHOGEN_FORM);
      setShowPathogenForm(false);
      await loadOptions();
    } catch (err) {
      setAddMessage(err.message);
    }
  }

  const filteredResults = results.filter((row) => {
    if (approvedOnly && row.final_status !== "Approved") return false;
    if (!deferredQuery.trim()) return true;
    const q = deferredQuery.trim().toLowerCase();
    return (
      row.sequence.toLowerCase().includes(q) ||
      row.final_status.toLowerCase().includes(q) ||
      row.target_food.toLowerCase().includes(q) ||
      row.target_pathogen.toLowerCase().includes(q) ||
      row.compatible_foods.toLowerCase().includes(q) ||
      row.rule_notes.toLowerCase().includes(q)
    );
  });

  async function handleSubmit(event) {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage("");

    const shouldUseFood = analysisMode === "food" || analysisMode === "combined";
    const shouldUsePathogen = analysisMode === "pathogen" || analysisMode === "combined";

    try {
      let response;

      if (dataSource === "system") {
        const params = new URLSearchParams();
        if (shouldUseFood) params.set("selected_food", selectedFood || options.foods[0]);
        if (shouldUsePathogen) params.set("target_pathogen", targetPathogen || options.pathogens[0]);
        response = await fetch(`${API_BASE_URL}/api/run-pipeline?${params}`);
      } else {
        if (!selectedFile) {
          setErrorMessage("Lütfen bir CSV dosyası seçin.");
          setIsSubmitting(false);
          return;
        }
        const formData = new FormData();
        formData.append("sequence_file", selectedFile);
        if (shouldUseFood) formData.append("selected_food", selectedFood || options.foods[0]);
        if (shouldUsePathogen) formData.append("target_pathogen", targetPathogen || options.pathogens[0]);
        response = await fetch(`${API_BASE_URL}/api/run-pipeline`, { method: "POST", body: formData });
      }

      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Pipeline request failed.");
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
    setSummary(null);
    setResults([]);
    setDownloadUrl("");
    setQuery("");
    setApprovedOnly(false);
    setAnalysisMode("general");
    setSelectedFood("");
    setTargetPathogen("");
    setErrorMessage("");
    setDataSource("system");
    setSelectedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  const showFoodSelect = analysisMode === "food" || analysisMode === "combined";
  const showPathogenSelect = analysisMode === "pathogen" || analysisMode === "combined";

  return (
    <main className="page-shell">
      <section className="hero">
        <form className="upload-panel" onSubmit={handleSubmit}>
          <div className="dropzone">
            <strong>Peptit adaylarını tarayın</strong>
            <p className="dropzone-copy">
              Sistem peptit havuzunu veya kendi CSV dosyanızı analiz edin. Veri kaynağını ve analiz odağını seçin.
            </p>

            <div className="target-grid">
              <fieldset className="analysis-mode">
                <legend>Veri kaynağı</legend>
                <div className="mode-options">
                  {DATA_SOURCES.map((source) => (
                    <label
                      className={`mode-card ${dataSource === source.value ? "selected" : ""}`}
                      key={source.value}
                    >
                      <input
                        type="radio"
                        name="dataSource"
                        value={source.value}
                        checked={dataSource === source.value}
                        onChange={(event) => {
                          setDataSource(event.target.value);
                          setSelectedFile(null);
                          if (fileInputRef.current) fileInputRef.current.value = "";
                        }}
                      />
                      <span>{source.label}</span>
                      <small>{source.description}</small>
                    </label>
                  ))}
                </div>
              </fieldset>

              {dataSource === "csv" ? (
                <label className="file-label">
                  <span>CSV dosyası</span>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv"
                    onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                  />
                  {selectedFile ? (
                    <p className="file-chip">{selectedFile.name}</p>
                  ) : (
                    <p className="hint">sequence sütunu içeren bir CSV seçin.</p>
                  )}
                </label>
              ) : null}

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
                <div className="select-with-add">
                  <label>
                    <span>Hedef gıda</span>
                    <select
                      value={selectedFood || options.foods?.[0] || DEFAULT_OPTIONS.foods[0]}
                      onChange={(event) => setSelectedFood(event.target.value)}
                    >
                      {options.foods.map((food) => (
                        <option key={food} value={food}>{food}</option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="button"
                    className="add-entry-btn"
                    onClick={() => { setShowFoodForm((v) => !v); setShowPathogenForm(false); setAddMessage(""); }}
                  >
                    {showFoodForm ? "İptal" : "+ Yeni gıda"}
                  </button>
                  {showFoodForm ? (
                    <form className="entry-form" onSubmit={handleAddFood}>
                      <p className="entry-form-title">Yeni gıda matrisi ekle</p>
                      <label>Ürün adı<input required placeholder="örn. Süt" value={foodForm.product} onChange={(e) => setFoodForm({ ...foodForm, product: e.target.value })} /></label>
                      <label>pH<input required type="number" step="0.1" min="0" max="14" placeholder="örn. 6.5" value={foodForm.pH} onChange={(e) => setFoodForm({ ...foodForm, pH: e.target.value })} /></label>
                      <label>Tuz oranı (%)<input required type="number" step="0.1" min="0" placeholder="örn. 1.5" value={foodForm.salt_ratio} onChange={(e) => setFoodForm({ ...foodForm, salt_ratio: e.target.value })} /></label>
                      <label>Sıcaklık (°C)<input required type="number" step="1" placeholder="örn. 4" value={foodForm.temperature} onChange={(e) => setFoodForm({ ...foodForm, temperature: e.target.value })} /></label>
                      <label>Yağ içeriği
                        <select value={foodForm.fat_content} onChange={(e) => setFoodForm({ ...foodForm, fat_content: e.target.value })}>
                          <option value="low">Düşük</option>
                          <option value="medium">Orta</option>
                          <option value="high">Yüksek</option>
                        </select>
                      </label>
                      <button type="submit" className="primary-button">Kaydet</button>
                      {addMessage ? <p className="entry-msg">{addMessage}</p> : null}
                    </form>
                  ) : null}
                </div>
              ) : null}

              {showPathogenSelect ? (
                <div className="select-with-add">
                  <label>
                    <span>Hedef patojen</span>
                    <select
                      value={targetPathogen || options.pathogens?.[0] || DEFAULT_OPTIONS.pathogens[0]}
                      onChange={(event) => setTargetPathogen(event.target.value)}
                    >
                      {options.pathogens.map((pathogen) => (
                        <option key={pathogen} value={pathogen}>{pathogen}</option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="button"
                    className="add-entry-btn"
                    onClick={() => { setShowPathogenForm((v) => !v); setShowFoodForm(false); setAddMessage(""); }}
                  >
                    {showPathogenForm ? "İptal" : "+ Yeni patojen"}
                  </button>
                  {showPathogenForm ? (
                    <form className="entry-form" onSubmit={handleAddPathogen}>
                      <p className="entry-form-title">Yeni patojen ekle</p>
                      <label>Patojen adı<input required placeholder="örn. Staphylococcus aureus" value={pathogenForm.name} onChange={(e) => setPathogenForm({ ...pathogenForm, name: e.target.value })} /></label>
                      <label>Min. net yük<input required type="number" step="1" min="0" placeholder="örn. 3" value={pathogenForm.min_charge} onChange={(e) => setPathogenForm({ ...pathogenForm, min_charge: e.target.value })} /></label>
                      <label>Hidrofobisite min.<input required type="number" step="0.01" min="0" max="1" placeholder="örn. 0.35" value={pathogenForm.hydrophobicity_min} onChange={(e) => setPathogenForm({ ...pathogenForm, hydrophobicity_min: e.target.value })} /></label>
                      <label>Hidrofobisite maks.<input required type="number" step="0.01" min="0" max="1" placeholder="örn. 0.65" value={pathogenForm.hydrophobicity_max} onChange={(e) => setPathogenForm({ ...pathogenForm, hydrophobicity_max: e.target.value })} /></label>
                      <label>Gram tipi
                        <select value={pathogenForm.gram_type} onChange={(e) => setPathogenForm({ ...pathogenForm, gram_type: e.target.value })}>
                          <option value="positive">Gram-pozitif</option>
                          <option value="negative">Gram-negatif</option>
                        </select>
                      </label>
                      <button type="submit" className="primary-button">Kaydet</button>
                      {addMessage ? <p className="entry-msg">{addMessage}</p> : null}
                    </form>
                  ) : null}
                </div>
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
        </form>
      </section>

      {errorMessage ? <section className="alert error">{errorMessage}</section> : null}

      {summary ? (
        <>
          <section className="summary-grid">
            {summaryCards.map((card) => (
              <article className="summary-card" key={card.key}>
                <span>
                  {card.label}
                  {card.tooltip ? (
                    <small className="card-hint">{card.tooltip}</small>
                  ) : null}
                </span>
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
