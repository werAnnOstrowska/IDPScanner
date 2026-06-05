import fitz 

def create_searchable_pdf(image_path, text_data, geometry_data, output_pdf_path):
    doc = fitz.open()
    #initialize PDF
    page = doc.new_page(width=2500, height=3500)

    # base image layer 
    page.insert_image(page.rect, filename=image_path)
    
    # hidden ocr layer
    for item in geometry_data:
        box = item["box"]
        rect = fitz.Rect(box["x"], box["y"], box["x"] + box["width"], box["y"] + box["height"])
        page.insert_text(rect.tl, item["text"], fontsize=box["height"]*0.8, color=(0,0,0), render_mode=3)
    
    #archival metadata 
    meta = doc.metadata
    meta["producer"] = "IDP-System-Engine"
    meta["format"] = "PDF/A-1b"
    doc.set_metadata(meta)
    
    # export and cleanup
    doc.save(output_pdf_path, garbage=4, deflate=True)
    doc.close()