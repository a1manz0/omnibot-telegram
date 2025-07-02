import base64
from pathlib import Path

def encode_image_to_base64(image_path):
    """Encodes an image to a base64 data URL."""
    if not image_path or not Path(image_path).exists():
        return None
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            # Для простоты предполагаем jpeg, но можно добавить определение MIME-типа
            mime_type = "image/jpeg" 
            return f"data:{mime_type};base64,{encoded_string}"
    except Exception as e:
        print(f"Ошибка кодирования изображения {image_path}: {e}")
        return None 