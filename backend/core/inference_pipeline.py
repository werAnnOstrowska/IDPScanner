import os
import sys
import torch
import cv2
import numpy as np


#paths definition
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODELS_DIR = os.path.join(BASE_DIR, "models")
WEIGHTS_PATH = os.path.join(MODELS_DIR, "crnn_weights_massive.pth")
DATA_INFO_PATH = os.path.join(BASE_DIR, "data", "processed", "sequence_dataset_hybrid.pt")

sys.path.append(MODELS_DIR)

#model import
try:
    from models.crnn_model import CRNN
except ImportError:
    print("BŁĄD: Nie znaleziono crnn_model.py w folderze models.")
    sys.exit(1)

#image preprocessing pipeline
#polimoprfic preprocessing, path or matrix, safeguards from c++ openCV errors
def preprocess_image(image_input):

    # input validation
    if isinstance(image_input, str):
        if not os.path.exists(image_input):
            raise FileNotFoundError(f"Brak obrazu: {image_input}")
        img = cv2.imread(image_input, cv2.IMREAD_GRAYSCALE)
    else:
        if image_input is None or image_input.size == 0 or len(image_input.shape) < 2:
            return torch.zeros((1, 1, 32, 256), dtype=torch.float32)

        if len(image_input.shape) == 3:
            img = cv2.cvtColor(image_input, cv2.COLOR_BGR2GRAY)
        else:
            img = image_input.copy()

    #dimensiion check
    h, w = img.shape[:2]
    if h == 0 or w == 0:
        return torch.zeros((1, 1, 32, 256), dtype=torch.float32)

    #noise reduction - guassian blur
    try:

        img = cv2.GaussianBlur(img, (3, 3), 0)
    except cv2.error:
        return torch.zeros((1, 1, 32, 256), dtype=torch.float32)

    # binarization
    _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    #resizing;
    TARGET_TEXT_H = 24
    h, w = binary.shape

    if h == 0 or w == 0:
        return torch.zeros((1, 1, 32, 256), dtype=torch.float32)

    new_w = max(int(w * (TARGET_TEXT_H / h)), TARGET_TEXT_H)

    if new_w > 2500:
        new_w = 2500

    img_resized = cv2.resize(binary, (new_w, TARGET_TEXT_H), interpolation=cv2.INTER_AREA)

    # padding and tensor formatting
    pad_w = int(np.ceil((new_w + 10) / 4.0) * 4)
    canvas = np.zeros((32, pad_w), dtype=np.uint8)

    canvas[4:4 + TARGET_TEXT_H, 5:5 + new_w] = img_resized

    tensor_img = torch.tensor(canvas, dtype=torch.float32).unsqueeze(0).unsqueeze(0) / 255.0
    return tensor_img

# MAIN INFERENCE ENGINE;
class IDPPipeline:
    def __init__(self):

        #Hardware setup;
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        #vocabulary loading;
        # print(f"-> Ładowanie słownika z {DATA_INFO_PATH}")
        data_info = torch.load(DATA_INFO_PATH)
        self.idx_to_char = {int(k): v for k, v in data_info['class_map'].items()}

        #neural network loading;
        self.model = CRNN(len(self.idx_to_char)).to(self.device)
        self.model.load_state_dict(torch.load(WEIGHTS_PATH, map_location=self.device))
        self.model.eval()
        # print(f"-> System gotowy (Weights: {os.path.basename(WEIGHTS_PATH)})")

    # CTC decoding
    def decode(self, pred_indices):
        chars = []
        prev = -1
        for idx in pred_indices:
            if idx != 0 and idx != prev:
                chars.append(self.idx_to_char.get(idx, ""))
            prev = idx
        return "".join(chars)

    #processing trigger
    #ommiting the slow hard disk
    def process(self, image_path=None, image_array=None):
        if image_array is not None:
            img_tensor = preprocess_image(image_array).to(self.device)
        elif image_path is not None:
            img_tensor = preprocess_image(image_path).to(self.device)
        else:
            return "", "" 

        #forward pass
        with torch.no_grad():
            output = self.model(img_tensor)
            indices = output.argmax(2)[:, 0].tolist()
            raw = self.decode(indices)

        return raw, raw

# Standalone execution tests
# if __name__ == "__main__":
#     TEST_IMG = os.path.join(CURRENT_DIR, "test_cropped.png")
#     if os.path.exists(TEST_IMG):
#         pipe = IDPPipeline()
#         raw, _ = pipe.process(TEST_IMG)
#         print(f"\n[SUROWY ODCZYT]: {raw}")
#     else:
#         print("Wstaw test_cropped.png do folderu głównego.")