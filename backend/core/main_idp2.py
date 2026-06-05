import os
import cv2
import json
import requests
import easyocr
import time

from core import page_scanner


#configuration 
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
OLLAMA_MODEL = "SpeakLeash/bielik-11b-v3.0-instruct:Q4_K_M"

#utilities
def clean_json_string(raw_string):
    return raw_string.replace("```json", "").replace("```", "").strip()

#LLM data extraction
def extract_document_data_with_llm(raw_text):
    if not raw_text.strip(): return {}
    system_prompt = (
        "Jesteś parserem EZD.\n"
        "1. 'Daty': Szukaj daty złożenia. Format ISO (YYYY-MM-DD).\n"
        "2. 'Podmioty': Lista stringów.\n"
        "3. 'Status_Podpisu': Imię i nazwisko lub 'Brak podpisu'.\n"
        "Zwróć TYLKO JSON:\n"
        "{\"Pelny_Zrekonstruowany_Tekst\": \"...\",\"Metadane\": {\"Rodzaj_Dokumentu\": \"...\",\"Daty\": [],\"Podmioty\": [],\"Status_Podpisu\": \"...\",\"Streszczenie\": \"...\"}}"
    )
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"{system_prompt}\n\nSurowy tekst OCR:\n{raw_text}",
        "format": "json", "stream": False,
        "options": {"temperature": 0.0, "top_k": 1, "top_p": 0.1, "num_predict": 1024}
    }
    try:
        res = requests.post(OLLAMA_URL, json=payload, timeout=300).json().get("response", "{}")
        return json.loads(clean_json_string(res))
    except:
        return {}

# main processing pipeline;
def process_simple_document(image_path, task_id):
    total_start_time = time.time()

    #OCR initialization
    detector = easyocr.Reader(['pl'], gpu=True)
    raw_img = cv2.imread(image_path)
    
    # image alignment
    img = page_scanner.get_page_orientation(raw_img, detector)

    # text extraction
    crnn_start_time = time.time()
    full_text, words_geometry = page_scanner.scan_header_text(img, detector, task_id)
    crnn_duration = time.time() - crnn_start_time

    # semantic parsing
    llm_start_time = time.time()
    final_extracted_data = extract_document_data_with_llm(full_text)
    llm_duration = time.time() - llm_start_time

    #Result compilation
    final_document = {
        "Status": "Sukces",
        "Typ_Analizy": "Dokument_Tekstowy_Ciągły",
        "Czasy_Wykonania_Sekundy": {
            "CRNN": round(crnn_duration, 2),
            "LLM": round(llm_duration, 2),
            "Calkowity": round(time.time() - total_start_time, 2)
        },
        "Pelny_Tekst_OCR": full_text, 
        "Wyodrebnione_Informacje": final_extracted_data,
        "Geometria_OCR": words_geometry
    }

    #local debug output 
    # output_path = os.path.join(CURRENT_DIR, "wyciag_z_dokumentu_prosty.json")
    # with open(output_path, "w", encoding="utf-8") as f:
    #     json.dump(final_document, f, ensure_ascii=False, indent=4)

    return final_document