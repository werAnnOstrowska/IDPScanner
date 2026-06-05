import cv2
import easyocr
import os
from core.inference_pipeline import IDPPipeline

# ML pipeline initialization
pipeline = IDPPipeline()

#Orientation detection
def get_page_orientation(image, detector):
    results = detector.readtext(image, paragraph=False, width_ths=0.1, mag_ratio=1.5)
    if not results: return image
    vertical_boxes = sum(1 for bbox, _, _ in results if (max(pt[1] for pt in bbox) - min(pt[1] for pt in bbox)) > (max(pt[0] for pt in bbox) - min(pt[0] for pt in bbox)) * 1.2)
    total_boxes = len(results)
    if total_boxes > 0 and (vertical_boxes / total_boxes) > 0.5:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return image

# text extrecation (OCR)
def scan_header_text(image, detector, task_id_z_pliku="debug_skan"):
    if image is None or image.size == 0:
        return "", []

    # print("   [SCANNER] Analiza i segmentacja nagłówka dokumentu...")
    word_boxes = detector.readtext(image, paragraph=False)

    if not word_boxes:
        return "", []

    annotated_image = image.copy()
    word_boxes.sort(key=lambda r: (min([pt[1] for pt in r[0]]) // 20, min([pt[0] for pt in r[0]])))

    header_words_crnn = []
    words_geometry = [] 

    # processing word crops
    for bbox, _, _ in word_boxes:
        (tl, tr, br, bl) = bbox
        top_left = (int(tl[0]), int(tl[1]))
        bottom_right = (int(br[0]), int(br[1]))

        wx_min = max(0, top_left[0] - 2)
        wx_max = min(image.shape[1], bottom_right[0] + 2)
        wy_min = max(0, top_left[1] - 2)
        wy_max = min(image.shape[0], bottom_right[1] + 2)

        word_crop = image[wy_min:wy_max, wx_min:wx_max]

        if word_crop.size > 0 and word_crop.shape[0] > 0 and word_crop.shape[1] > 0:
            word_text, _ = pipeline.process(image_array=word_crop)
            if word_text and word_text.strip():
                clean_word = word_text.strip()
                header_words_crnn.append(clean_word)
                
                words_geometry.append({
                    "text": clean_word,
                    "box": {
                        "x": top_left[0],
                        "y": top_left[1],
                        "width": bottom_right[0] - top_left[0],
                        "height": bottom_right[1] - top_left[1]
                    }
                })
                
                cv2.rectangle(annotated_image, top_left, bottom_right, (0, 255, 0), 2)
                cv2.putText(annotated_image, clean_word, (top_left[0], top_left[1] - 5), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

    final_text = " ".join(header_words_crnn)
    
    # save artifacts
    output_dir = "/app/data/output" 
    os.makedirs(output_dir, exist_ok=True)
    
    oryginal_path = os.path.join(output_dir, f"{task_id_z_pliku}_oryginal.jpg")
    przetworzony_path = os.path.join(output_dir, f"{task_id_z_pliku}_przetworzony.jpg")
    
    cv2.imwrite(oryginal_path, image)
    cv2.imwrite(przetworzony_path, annotated_image)
    
    return final_text, words_geometry