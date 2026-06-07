import os
import sys
import json
import uuid
import shutil
import uvicorn
import tempfile 
from dotenv import load_dotenv
import fitz 
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
import zipfile
import io
from sqlalchemy import create_engine, Column, String, DateTime, Text, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from core.main_idp2 import process_simple_document
from core.pdfa_generator import create_searchable_pdf

#env variables
load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#DB connection 
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

#Database model
class DocumentRecord(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, index=True)
    status = Column(String, default="processing")
    file_name = Column(String)
    result_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

#Database initialization
Base.metadata.create_all(bind=engine)


#File converter;
def ensure_image_format(file_path: str) -> str:
    if file_path.lower().endswith('.pdf'):
        doc = fitz.open(file_path)
        page = doc.load_page(0) 
        pix = page.get_pixmap(dpi=300) 
        new_path = file_path + ".png"
        pix.save(new_path)
        doc.close()
        os.remove(file_path)
        return new_path
    return file_path

#API initialization
app = FastAPI(title="IDP Enterprise API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://idp-scanner.vercel.app", 
        "http://localhost:5173", 
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#DB Session 
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

#Background ML Pipeline
def run_background_pipeline(task_id: str, file_path: str):
    db = SessionLocal()
    db_record = db.query(DocumentRecord).filter(DocumentRecord.id == task_id).first()
    try:
        safe_image_path = ensure_image_format(file_path)
        result_data = process_simple_document(safe_image_path, task_id)
        if result_data:
            db_record.status = "completed"
            db_record.result_data = result_data
        else:
            db_record.status = "error"
            db_record.error_message = "Błąd systemu: silnik IDP nie zwrócił danych."
    except Exception as e:
        db_record.status = "error"
        db_record.error_message = str(e)
    finally:
        db.commit()
        db.close()
        if 'safe_image_path' in locals() and os.path.exists(safe_image_path):
            os.remove(safe_image_path)
        elif os.path.exists(file_path):
            os.remove(file_path)

#Endpoint - upload; 
@app.post("/api/v1/scan")
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db)):
    task_id = str(uuid.uuid4())
    new_doc = DocumentRecord(id=task_id, status="processing", file_name=file.filename)
    db.add(new_doc)
    db.commit()
    fd, temp_file_path = tempfile.mkstemp(suffix=f"_{file.filename}")
    with os.fdopen(fd, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    background_tasks.add_task(run_background_pipeline, task_id, temp_file_path)
    return {"message": "Zadanie przyjęte do kolejki", "task_id": task_id}

#Endpoint - status;
@app.get("/api/v1/status/{task_id}")
async def get_task_status(task_id: str, db: Session = Depends(get_db)):
    record = db.query(DocumentRecord).filter(DocumentRecord.id == task_id).first()
    if not record: raise HTTPException(status_code=404, detail="Brak zadania.")
    response = {"task_id": record.id, "status": record.status, "file_name": record.file_name, "created_at": record.created_at}
    if record.status == "completed": response["result"] = record.result_data
    elif record.status == "error": response["error_message"] = record.error_message
    return response

#endpoint - zip export;
@app.get("/api/v1/download/{task_id}")
async def download_results(task_id: str, db: Session = Depends(get_db)):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "data", "output")
    
    orig_path = os.path.join(output_dir, f"{task_id}_oryginal.jpg")
    proc_path = os.path.join(output_dir, f"{task_id}_przetworzony.jpg")
    pdf_path = os.path.join(output_dir, f"{task_id}_archival.pdf")
    
    zip_buffer = io.BytesIO()
    
    record = db.query(DocumentRecord).filter(DocumentRecord.id == task_id).first()
    
    if record and record.result_data:
        geo = record.result_data.get("Geometria_OCR", [])
        text = record.result_data.get("Pelny_Tekst_OCR", "")
        create_searchable_pdf(orig_path, text, geo, pdf_path)

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        if os.path.exists(orig_path): zip_file.write(orig_path, arcname=f"{task_id}_oryginal.jpg")
        if os.path.exists(proc_path): zip_file.write(proc_path, arcname=f"{task_id}_przetworzony.jpg")
        if os.path.exists(pdf_path): zip_file.write(pdf_path, arcname=f"{task_id}_archival.pdf") # PDF w paczce
        
        if record and record.result_data:
            json_string = json.dumps(record.result_data, indent=4, ensure_ascii=False)
            zip_file.writestr(f"{task_id}_pelny_zrzut.json", json_string.encode('utf-8'))
            
            surowy_ocr = record.result_data.get("Pelny_Tekst_OCR", "")
            if surowy_ocr: zip_file.writestr(f"{task_id}_tekst_surowy_OCR.txt", surowy_ocr.encode('utf-8'))
                
            llm_text = record.result_data.get("Wyodrebnione_Informacje", {}).get("Pelny_Zrekonstruowany_Tekst", "")
            if llm_text: zip_file.writestr(f"{task_id}_tekst_zrekonstruowany_LLM.txt", llm_text.encode('utf-8'))

    zip_buffer.seek(0)
    return StreamingResponse(zip_buffer, media_type="application/zip", headers={"Content-Disposition": f"attachment; filename=IDP_Pakiet_{task_id}.zip"})


#endpoint - image showcase
@app.get("/api/v1/image/{task_id}")
async def get_image(task_id: str):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_dir, "data", "output", f"{task_id}_oryginal.jpg")
    
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Obraz nie istnieje w folderze output")

#Server entry point
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)