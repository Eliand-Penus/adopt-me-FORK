import os
import cloudinary.uploader
from werkzeug.utils import secure_filename

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}
ALLOWED_DOC_EXTENSIONS = {"pdf"}
ALLOWED_EXTENSIONS = frozenset(ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOC_EXTENSIONS)

def allowed_file(filename, allowed_set=ALLOWED_EXTENSIONS):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

def upload_to_cloudinary(file, folder_name, allowed_set=ALLOWED_EXTENSIONS):
    if not file or not file.filename:
        return None
        
    if not allowed_file(file.filename, allowed_set):
        return None
        
    try:
        ext = file.filename.rsplit('.', 1)[1].lower()
        is_doc = ext in ALLOWED_DOC_EXTENSIONS
        r_type = "raw" if is_doc else "image"
        
        upload_result = cloudinary.uploader.upload(
            file,
            folder=folder_name,
            resource_type=r_type
        )
        
        return upload_result.get("secure_url")
        
    except Exception as e:
        print(f"Cloudinary upload failed: {e}")
        return None

