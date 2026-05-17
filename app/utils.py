import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}
ALLOWED_DOC_EXTENSIONS = {"pdf", "doc", "docx"}
ALLOWED_EXTENSIONS = frozenset(ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOC_EXTENSIONS)

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

def save_file(file, folder_name):
    if not file or not file.filename:
        return None
        
    filename = secure_filename(file.filename)
    
    # Generate unique filename to prevent duplicates
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    
    # Path relative to app root
    upload_path = os.path.join(current_app.root_path, "static", "uploads", folder_name)
    
    # Ensure directory exists
    os.makedirs(upload_path, exist_ok=True)
    
    file_path = os.path.join(upload_path, unique_filename)
    file.save(file_path)
    
    # Return the relative path to be stored in DB
    return f"uploads/{folder_name}/{unique_filename}"
