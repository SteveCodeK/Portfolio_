from flask import current_app
import io
from PIL import Image
import bleach
from bleach.css_sanitizer import CSSSanitizer

# Define your CSS sanitizer
css_sanitizer = CSSSanitizer(
    allowed_css_properties=['color', 'font-size', 'text-align', 'width', 'height', 'max-width', 'max-height', 'margin', 'padding', 'border'] 
)

# List of allowed HTML tags for content
ALLOWED_TAGS = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'p', 
                'pre', 'strong', 'ul', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'hr', 'img', 
                'div', 'span', 'table', 'thead', 'tbody', 'tr', 'th', 'td']
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'width', 'height'],
    'table': ['border', 'cellpadding', 'cellspacing'],
    'td': ['colspan', 'rowspan'],
    'th': ['colspan', 'rowspan'],
    '*': ['class', 'style'],
}

def save_image_to_db(form_picture, output_size=None):
    """
    Process and save an uploaded image to be stored in the database.
    
    Args:
        form_picture: The uploaded file object from the form
        output_size: Optional tuple of (width, height) to resize the image
        
    Returns:
        Tuple of (image_binary_data, mimetype, filename) or (None, None, None) if error
    """
    if form_picture:
        try:
            in_memory_file = io.BytesIO()
            form_picture.save(in_memory_file)
            in_memory_file.seek(0)

            i = Image.open(in_memory_file)
            if output_size:
                i.thumbnail(output_size)

            output_buffer = io.BytesIO()
            mimetype = form_picture.mimetype
            if mimetype == 'image/jpeg' or mimetype == 'image/jpg':
                i.save(output_buffer, format='JPEG')
            elif mimetype == 'image/png':
                i.save(output_buffer, format='PNG')
            elif mimetype == 'image/gif':
                i.save(output_buffer, format='GIF')
            else:
                try:
                    i.save(output_buffer, format=i.format)
                except KeyError:
                    i.save(output_buffer, format='JPEG')
                mimetype = mimetype or 'application/octet-stream'

            output_buffer.seek(0)
            image_binary_data = output_buffer.read()

            return image_binary_data, mimetype, form_picture.filename
        except Exception as e:
            current_app.logger.error(f"Error processing image for DB storage: {e}")
            return None, None, None
    return None, None, None

def allowed_file(filename):
    """
    Check if a filename has an allowed extension.
    
    Args:
        filename: The name of the file to check
        
    Returns:
        bool: True if the file extension is allowed, False otherwise
    """
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clean_content(content):
    """
    Clean and sanitize HTML content using bleach.
    
    Args:
        content: The HTML content to clean
        
    Returns:
        str: The cleaned and sanitized HTML content
    """
    return bleach.clean(content,
                       tags=ALLOWED_TAGS,
                       attributes=ALLOWED_ATTRIBUTES,
                       css_sanitizer=css_sanitizer,
                       strip=True)