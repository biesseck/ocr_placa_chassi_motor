import { useRef, useState } from "react";
import "./App.css";

// const API_URL = "http://192.168.1.112:8080"; // <-- your IP
// const API_URL = "https://vistoria-ocr-api-531790625129.us-east1.run.app";
const API_URL = "https://vistoria-ocr-api-531790625129.us-central1.run.app";

function App() {
  const fileInputRef = useRef(null);

  const [resultImage, setResultImage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleFileChange(event) {
    const file = event.target.files[0];
    if (!file) return;

    setLoading(true);
    setError("");
    setResultImage(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_URL}/predict`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text);
      }

      const data = await response.json();

      const base64 = data?.plates?.[0]?.annotated_image;

      if (!base64) {
        throw new Error("Nenhuma placa detectada na imagem.");
      }

      setResultImage(`data:image/jpeg;base64,${base64}`);
    } catch (err) {
      setError("API error: " + err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container">
      <h1>License Plate OCR</h1>

      <div className="center">
        <button
          className="upload-button"
          onClick={() => fileInputRef.current.click()}
        >
          Capturar Imagem
        </button>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleFileChange}
          hidden
        />
      </div>

      {loading && <p className="status">Processing...</p>}
      {error && <p className="error">{error}</p>}

      {resultImage && (
        <div className="result">
          <img src={resultImage} alt="Result" />
        </div>
      )}
    </main>
  );
}

export default App;