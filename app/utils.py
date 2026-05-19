import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

import cloudinary.uploader

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}
ALLOWED_DOC_EXTENSIONS = {"pdf", "doc", "docx"}
ALLOWED_EXTENSIONS = frozenset(ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOC_EXTENSIONS)

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

def save_file(file, folder_name):
    if not file or not file.filename:
        return None
        
    try:
        # We upload to Cloudinary.
        # Cloudinary automatically generates unique filenames if we don't specify public_id.
        # We can specify the folder to keep things organized.
        is_doc = file.filename.rsplit('.', 1)[1].lower() in ALLOWED_DOC_EXTENSIONS
        r_type = "raw" if is_doc else "image"
        
        upload_result = cloudinary.uploader.upload(
            file,
            folder=folder_name,
            resource_type=r_type
        )
        
        # Return the secure HTTPS URL provided by Cloudinary
        return upload_result.get("secure_url")
        
    except Exception as e:
        print(f"Cloudinary upload failed: {e}")
        return None
