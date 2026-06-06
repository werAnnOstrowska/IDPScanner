import { useState, useRef, useEffect } from 'react';
import type { ChangeEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';

import uploadArrow from './assets/arrow.svg';
import cameraIcon from './assets/camera.svg';
import clipIcon from './assets/clipIcon.svg';
import notesIcon from './assets/notesIcon.svg';

import './ScannerApp.css';

type ScanState = 'upload' | 'processing' | 'result' | 'edit';

interface OCRWord {
  text: string;
  box: { x: number; y: number; width: number; height: number };
}

interface IDPResponse {
  Status: string;
  Wyodrebnione_Informacje: Record<string, unknown>;
  Geometria_OCR?: OCRWord[];
}

const apiUrl = import.meta.env.VITE_API_URL || '';

export default function ScannerApp() {
  const [currentState, setCurrentState] = useState<ScanState>('upload');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [resultData, setResultData] = useState<IDPResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  
  const [imageScale, setImageScale] = useState({ x: 1, y: 1 });
  const imgRef = useRef<HTMLImageElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const updateScale = () => {
    if (imgRef.current) {
      const { naturalWidth, naturalHeight, clientWidth, clientHeight } = imgRef.current;
      if (naturalWidth && naturalHeight) {
        setImageScale({
          x: clientWidth / naturalWidth,
          y: clientHeight / naturalHeight
        });
      }
    }
  };

  useEffect(() => {
    window.addEventListener('resize', updateScale);
    return () => window.removeEventListener('resize', updateScale);
  }, []);

  const triggerFileSelect = () => fileInputRef.current?.click();

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setErrorMessage(null);
    }
  };

  const handleProcessDocument = async () => {
    if (!selectedFile) return;
    setCurrentState('processing');
    setErrorMessage(null);
    setCurrentTaskId(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      // DODANO NAGŁÓWEK OMIJAJĄCY BLOKADĘ NGROK
      const initResponse = await fetch(`${apiUrl}/api/v1/scan`, { 
        method: 'POST', 
        body: formData,
        headers: {
          'ngrok-skip-browser-warning': 'true'
        }
      });
      if (!initResponse.ok) throw new Error(`Błąd serwera: ${initResponse.status}`);
      const initData = await initResponse.json();
      const taskId = initData.task_id;
      setCurrentTaskId(taskId);

      const checkStatus = async () => {
        try {
          // DODANO NAGŁÓWEK OMIJAJĄCY BLOKADĘ NGROK
          const statusResponse = await fetch(`${apiUrl}/api/v1/status/${taskId}`, {
            headers: {
              'ngrok-skip-browser-warning': 'true'
            }
          });
          if (!statusResponse.ok) throw new Error("Błąd podczas odpytywania.");
          const statusData = await statusResponse.json();

          if (statusData.status === 'completed') {
            setResultData(statusData.result);
            setCurrentState('result');
          } else if (statusData.status === 'error') {
            throw new Error(statusData.error_message || "Błąd analizy ML.");
          } else {
            setTimeout(checkStatus, 5000);
          }
        } catch (err: unknown) {
          if (err instanceof Error) setErrorMessage(err.message);
          setCurrentState('upload');
        }
      };
      setTimeout(checkStatus, 5000);
    } catch (err: unknown) {
      if (err instanceof Error) setErrorMessage(err.message);
      setCurrentState('upload');
    }
  };

  const handleDownloadZip = async () => {
    if (!currentTaskId) return;
    try {
      // DODANO NAGŁÓWEK OMIJAJĄCY BLOKADĘ NGROK
      const response = await fetch(`${apiUrl}/api/v1/download/${currentTaskId}`, {
        headers: {
          'ngrok-skip-browser-warning': 'true'
        }
      });
      if (!response.ok) throw new Error(`Błąd pobierania: ${response.status}`);
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `IDP_Wyniki_${currentTaskId}.zip`; 
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      alert("Nie udało się pobrać paczki ZIP.");
    }
  };

  const handleResetFlow = () => {
      setCurrentState('upload'); 
      setSelectedFile(null); 
      setResultData(null);
  };

  return (
    <div className="scanner-page-container">
      <nav className="scanner-navbar">
        <Link to="/" className="scanner-logo">IDPScanner</Link>
        <span className="system-status">ENV: LOCAL_HOST // READY</span>
      </nav>

      <main className="scanner-layout">
        <section className="panel-sandbox" style={{ overflow: 'auto' }}>
          <AnimatePresence mode="wait">
            
            {currentState === 'upload' && (
              <motion.div key="upload" className="upload-dropzone" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <input type="file" ref={fileInputRef} style={{ display: 'none' }} onChange={handleFileChange} accept=".pdf, .png, .jpg, .jpeg" />
                <button className="upload-action-btn" onClick={triggerFileSelect}>
                  <img src={uploadArrow} alt="Upload" className="btn-icon-svg" />
                  <div className="btn-text">
                    <h4>PRZEŚLIJ PLIK</h4>
                    <p>PDF, PNG, JPG do 15MB</p>
                  </div>
                </button>
                
                <div className="dropzone-divider"><span>LUB</span></div>

                <button className="upload-action-btn" onClick={triggerFileSelect}>
                  <img src={cameraIcon} alt="Zrób zdjęcie" className="btn-icon-svg" />
                  <div className="btn-text">
                    <h4>ZRÓB ZDJĘCIE</h4>
                    <p>Użyj kamery urządzenia</p>
                  </div>
                </button>

              {selectedFile && (
                <div className="selected-file-badge">
                  <img src={clipIcon} alt="Załączone pliki" className="btn-icon-svg" />
                  Załadowano: {selectedFile.name}
                </div>
              )}
                {errorMessage && <div style={{ color: '#ef4444', marginTop: '1rem' }}>❌ {errorMessage}</div>}
              </motion.div>
            )}

            {currentState === 'processing' && (
              <motion.div key="processing" className="preview-box original-preview" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <div className="preview-label">PLIK SYGNALNY WPROWADZONY</div>
                <div className="mock-document-ascii">
                  [DOKUMENT: {selectedFile?.name}]<br/>
                  GAUSS_BLUR: PROCESSING...<br/>
                  CRNN_OCR_ENGINE: ACTIVE
                </div>
              </motion.div>
            )}

            {currentState === 'result' && (
              <motion.div key="result" className="preview-box result-preview" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <div className="preview-label-success">WYNIK PRZETWARZANIA</div>
                <div className="result-data-wrapper">
                  <pre className="extracted-text-area">{JSON.stringify(resultData?.Wyodrebnione_Informacje, null, 2)}</pre>
                </div>
              </motion.div>
            )}

          </AnimatePresence>
        </section>

        <section className="panel-controls">
          <AnimatePresence mode="wait">
            {currentState === 'upload' && (
              <motion.div key="ctrl-upload" className="control-group" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <button className={`action-trigger-btn ${!selectedFile ? 'disabled' : ''}`} disabled={!selectedFile} onClick={handleProcessDocument}>
                  PROCESUJ SYSTEMOWO
                </button>
              </motion.div>
            )}

            {currentState === 'processing' && (
              <motion.div key="ctrl-processing" className="control-group" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
                <h3 className="status-title alert-pulse">Twój plik jest generowany...</h3>
                <p className="status-task-id">
                  ZADANIE ID: <code>{currentTaskId ? `#${currentTaskId.split('-')[0]}` : "INICJALIZACJA..."}</code>
                </p>
                <div className="loader-bar-container"><div className="loader-bar-fill"></div></div>
                <p className="status-notice">Pozostaw stronę otwartą! Trwa ekstrakcja metadanych w wątku lokalnym.</p>
              </motion.div>
            )}

            {(currentState === 'result' || currentState === 'edit') && (
              <motion.div key="ctrl-result" className="control-group" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <h3 className="status-title-success">Twój plik jest gotowy!</h3>
                <div className="result-actions-stack">
                  <button className="action-trigger-btn" onClick={handleDownloadZip}>POBIERZ PACZKĘ WYNIKOWĄ</button>
                  <button className="secondary-action-btn" onClick={() => setCurrentState('edit')}>
                    <img src={notesIcon} alt="Edytuj plik" className="btn-icon-svg" />
                    OTWÓRZ EDYTOR WIZUALNY
                  </button>
                  <button className="reset-flow-btn" onClick={handleResetFlow}>
                    ↩ SKANUJ KOLEJNY PLIK
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </section>
      </main>

      <AnimatePresence>
        {currentState === 'edit' && currentTaskId && (
          <motion.div 
            key="fullscreen-edit" 
            initial={{ opacity: 0, y: 50 }} 
            animate={{ opacity: 1, y: 0 }} 
            exit={{ opacity: 0, y: 50 }}
            style={{
              position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
              backgroundColor: '#0a0a0a', zIndex: 9999,
              overflow: 'auto',
              padding: '2rem',
              textAlign: 'center' 
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', textAlign: 'left' }}>
              <h2 style={{ color: '#eab308', margin: 0, fontFamily: 'monospace' }}>KOREKTA WARSTWY WIZYJNEJ (RAW OCR)</h2>
              <button 
                onClick={() => setCurrentState('result')}
                style={{
                  background: '#333', color: '#fff', border: 'none', padding: '10px 20px', 
                  cursor: 'pointer', fontFamily: 'monospace', fontWeight: 'bold'
                }}
              >
                ✖ ZAMKNIJ EDYTOR
              </button>
            </div>
            
            <div style={{ position: 'relative', display: 'inline-block', textAlign: 'left' }}>
              <img 
                ref={imgRef}
                src={`${apiUrl}/api/v1/image/${currentTaskId}`}
                onLoad={updateScale}
                style={{ 
                  display: 'block', 
                  maxWidth: '100%', 
                  height: 'auto', 
                  border: '1px solid #333'
                }}
                alt="Edytowany dokument - podgląd z serwera"
              />
              
              {resultData?.Geometria_OCR?.map((item, idx) => {
                const scaledHeight = item.box.height * imageScale.y;
                const dynamicFontSize = Math.max(10, scaledHeight * 0.75);

                return (
                  <input
                    key={idx}
                    type="text"
                    defaultValue={item.text}
                    className="ocr-input-box" 
                    style={{
                      left: `${item.box.x * imageScale.x}px`,
                      top: `${item.box.y * imageScale.y}px`,
                      width: `${item.box.width * imageScale.x}px`,
                      height: `${scaledHeight}px`,
                      fontSize: `${dynamicFontSize}px`
                    }}
                  />
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}