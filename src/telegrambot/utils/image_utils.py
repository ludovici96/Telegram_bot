
from PIL import Image
import pytesseract

def resize_image(image_path: str, max_size: tuple = (4096, 4096)) -> None:
    """
    Resize an image while maintaining aspect ratio.
    
    Args:
        image_path (str): Path to the image file
        max_size (tuple): Maximum dimensions (width, height)
    """
    with Image.open(image_path) as img:
        img.thumbnail(max_size)
        img.save(image_path)

def extract_text_from_image(image_path: str) -> str:
    """
    Extract text from an image using OCR.
    
    Args:
        image_path (str): Path to the image file
    
    Returns:
        str: Extracted text from the image
    """
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        print(f"Error extracting text from image: {str(e)}")
        return ""