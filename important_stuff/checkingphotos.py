from urllib.parse import urlparse
import os
from PIL import Image
import tempfile
import io
async def optimize_image(attachment):
    # Load the image from the attachment
    img_data = await attachment.read()
    image = Image.open(io.BytesIO(img_data))
    
    # Optimize the image by resizing or converting format
    # Example: Resize if the width or height is greater than a threshold
    max_size = 1080
    if image.width > max_size or image.height > max_size:
        scaling_factor = max_size / max(image.width, image.height)
        new_size = (int(image.width * scaling_factor), int(image.height * scaling_factor))
        image = image.resize(new_size, Image.LANCZOS)
    
    # Save optimized image to a temporary file
    optimized_temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpeg")
    image.save(optimized_temp_file.name, "JPEG", quality=85)  # Adjust quality for further optimization
    optimized_temp_file.close()
    
    return optimized_temp_file.name