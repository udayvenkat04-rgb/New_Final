"""
FileUtils centralizes filesystem management, uploads saving, and image loading.
"""
import os
import uuid
from PIL import Image, ImageDraw

def save_uploaded_file(uploaded_file, target_dir: str) -> str:
    """Saves a Streamlit uploaded file into the target directory with a unique UUID filename."""
    if not uploaded_file:
        return ""
    
    os.makedirs(target_dir, exist_ok=True)
    _, ext = os.path.splitext(uploaded_file.name)
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    target_path = os.path.join(target_dir, unique_filename)
    
    with open(target_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    # Return path with forward slashes for cross-platform compatibility
    return target_path.replace("\\", "/")

def get_placeholder_image(name: str = "No Photo") -> Image.Image:
    """Creates a placeholder avatar image with initials."""
    img = Image.new('RGB', (300, 300), color='#1e293b')
    draw = ImageDraw.Draw(img)
    draw.ellipse([75, 75, 225, 225], fill='#334155')
    draw.ellipse([110, 110, 190, 190], fill='#475569')
    draw.ellipse([50, 240, 250, 300], fill='#334155')
    
    initials = "".join([part[0].upper() for part in name.split() if part])[:2]
    try:
        draw.text((150, 150), initials, fill='#f1f5f9', anchor="mm")
    except Exception:
        pass
    return img

def load_image_safely(image_path: str, default_name: str = "Missing Person") -> Image.Image:
    """Safely loads an image from the filesystem. If not found, returns a placeholder."""
    if not image_path or not os.path.exists(image_path):
        return get_placeholder_image(default_name)
    try:
        return Image.open(image_path)
    except Exception:
        return get_placeholder_image(default_name)
