from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_migrate import Migrate
from form import BlogPostForm, ProjectForm, LoginForm
import bleach
from flask_sitemap import Sitemap
import os
import secrets
from PIL import Image
from flask import current_app
from slugify import slugify
from dotenv import load_dotenv
import io # Import io for BytesIO
from sqlalchemy import inspect # Import inspect for proper table existence check
from bleach.css_sanitizer import CSSSanitizer

load_dotenv()

# Basic setup (move to config.py for larger projects)
app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/other_uploads' # Adjusted for clarity
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

sitemap = Sitemap(app=app)
app.config['SITEMAP_URL_SCHEME'] = 'https'
app.config['SITEMAP_GENERATOR_OPTIONS'] = {'base_url': os.environ.get('SITEMAP_BASE_URL')}

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Define your CSS sanitizer
css_sanitizer = CSSSanitizer(
    allowed_css_properties=['color', 'font-size', 'text-align', 'width', 'height', 'max-width', 'max-height', 'margin', 'padding', 'border'] # Add properties you want to allow
)

# --- SQLAlchemy Models (DEFINED AT THE TOP LEVEL) ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(658), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"User('{self.username}')"

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    image_filename = db.Column(db.String(100), nullable=False, default='default.jpg')
    image_data = db.Column(db.LargeBinary, nullable=True)
    image_mimetype = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f"BlogPost('{self.title}', '{self.date_posted}')"

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    skills_used = db.Column(db.String(200), nullable=True)
    demo_link = db.Column(db.String(200), nullable=True)
    case_study_link = db.Column(db.String(200), nullable=True)
    image_filename = db.Column(db.String(100), nullable=False, default='default.jpg')
    image_data = db.Column(db.LargeBinary, nullable=True)
    image_mimetype = db.Column(db.String(50), nullable=True)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"Project('{self.title}')"

# NEW: Define UploadedImage model at the top level
class UploadedImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255))
    data = db.Column(db.LargeBinary)
    mimetype = db.Column(db.String(50))

    def __repr__(self):
        return f"UploadedImage('{self.filename}')"

# --- Helper Function for Image Saving ---
def save_image_to_db(form_picture, output_size=None):
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
                # Fallback: try to save in original format, or default to JPEG
                try:
                    i.save(output_buffer, format=i.format)
                except KeyError: # If i.format is None or unsupported
                    i.save(output_buffer, format='JPEG')
                mimetype = mimetype or 'application/octet-stream' # Ensure mimetype is set

            output_buffer.seek(0)
            image_binary_data = output_buffer.read()

            return image_binary_data, mimetype, form_picture.filename
        except Exception as e:
            app.logger.error(f"Error processing image for DB storage: {e}")
            return None, None, None
    return None, None, None

@login_manager.user_loader
def load_user(user_id):
    # Using Session.get() as recommended by SQLAlchemy 2.0
    return db.session.get(User, int(user_id))

# --- Robots.txt Route ---
@app.route('/robots.txt')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Sitemap Generators ---
@sitemap.register_generator
def my_sitemap_generator():
    yield 'home', {'changefreq': 'daily', 'priority': 1.0}
    yield 'portfolio', {'changefreq': 'weekly', 'priority': 0.9}
    yield 'blog', {'changefreq': 'daily', 'priority': 0.9}

    for post in BlogPost.query.all():
        yield 'blog_post', {
            'slug': post.slug,
            'lastmod': post.date_posted.isoformat() + 'Z' if post.date_posted else None,
            'changefreq': 'weekly',
            'priority': 0.8
        }

    for project in Project.query.all():
        last_mod_date = project.date_posted.isoformat() + 'Z' if project.date_posted else None
        yield 'project_detail', {
            'slug': project.slug,
            'lastmod': last_mod_date,
            'changefreq': 'monthly',
            'priority': 0.7
        }

# --- Route to serve images from the database ---
@app.route('/image/<string:model_name>/<int:image_id>')
def get_image(model_name, image_id):
    app.logger.info(f"Attempting to get image: model_name={model_name}, image_id={image_id}")
    item = None

    if model_name == 'blog':
        item = db.session.get(BlogPost, image_id)
        # Check for image data specific to BlogPost
        if item and item.image_data:
            app.logger.info(f"Serving BlogPost ID {item.id} (filename: {item.image_filename}, mimetype: {item.image_mimetype}, data_len: {len(item.image_data) if item.image_data else 0})")
            return send_file(io.BytesIO(item.image_data), mimetype=item.image_mimetype)

    elif model_name == 'project':
        item = db.session.get(Project, image_id)
        # Check for image data specific to Project
        if item and item.image_data:
            app.logger.info(f"Serving Project ID {item.id} (filename: {item.image_filename}, mimetype: {item.image_mimetype}, data_len: {len(item.image_data) if item.image_data else 0})")
            return send_file(io.BytesIO(item.image_data), mimetype=item.image_mimetype)

    elif model_name == 'uploaded_image': # This is the case for TinyMCE uploads
        item = db.session.get(UploadedImage, image_id)
        # Check for image data specific to UploadedImage (using 'data' attribute)
        if item and item.data: # <--- CHANGED THIS TO item.data
            app.logger.info(f"Serving UploadedImage ID {item.id} (filename: {item.filename}, mimetype: {item.mimetype}, data_len: {len(item.data) if item.data else 0})")
            return send_file(io.BytesIO(item.data), mimetype=item.mimetype)

    else:
        app.logger.warning(f"Invalid model name '{model_name}' in get_image request.")
        return "Invalid model name", 404

    # If we reach here, it means either:
    # 1. No item was found for the given ID and model_name.
    # 2. An item was found, but it had no image data (e.g., item.image_data or item.data was None/empty).
    app.logger.warning(f"No image data found for model_name={model_name}, image_id={image_id}. Item found: {bool(item)}")

    # Serve a default image if no image data exists or item not found
    default_image_path = os.path.join(app.root_path, 'static', 'img', 'default.jpg')
    if os.path.exists(default_image_path):
         app.logger.info(f"Serving default image from: {default_image_path}")
         return send_file(default_image_path, mimetype='image/jpeg')
    else:
         app.logger.error(f"Default image not found at {default_image_path}")
         from flask import make_response
         response = make_response("No image or default image found.", 404)
         response.headers['Content-Type'] = 'text/plain'
         return response


# --- Routes for Public Pages (unchanged) ---
@app.route('/')
@app.route('/home')
def home():
    latest_blogs = BlogPost.query.order_by(BlogPost.date_posted.desc()).limit(3).all()
    latest_projects = Project.query.order_by(Project.id.desc()).limit(3).all()
    return render_template('index.html', latest_blogs=latest_blogs, latest_projects=latest_projects)

@app.route('/about')
def about():
    return render_template('about.html', title='About Me')

@app.route('/skills')
def skills():
    return render_template('skills.html', title='My Skills')

@app.route('/portfolio')
def portfolio():
    projects = Project.query.all()
    return render_template('portfolio.html', projects=projects, title='My Portfolio')

@app.route('/project/<string:slug>')
def project_detail(slug):
    project = Project.query.filter_by(slug=slug).first_or_404()
    return render_template('project_detail.html', project=project, title=project.title)

@app.route('/blog')
def blog():
    page = request.args.get('page', 1, type=int)
    blog_posts = BlogPost.query.order_by(BlogPost.date_posted.desc()).paginate(page=page, per_page=5, error_out=False)
    return render_template('post.html', blog_posts=blog_posts, title='My Blog')

@app.route('/blog/<string:slug>')
def blog_post(slug):
    post = BlogPost.query.filter_by(slug=slug).first_or_404()
    meta_desc = post.content[:160] + '...' if len(post.content) > 160 else post.content
    return render_template('blog.html', post=post, title=post.title + ' - Stephen Awili Blog', description=meta_desc)

@app.route('/contact')
def contact():
    return render_template('contact.html', title='Contact Me')

# --- Admin Routes (unchanged logic, only model definition moved) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin_dashboard'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')

    return render_template('admin/login.html', title='Admin Login', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/admin')
@login_required
def admin_dashboard():
    form = LoginForm()
    blog_posts = BlogPost.query.order_by(BlogPost.date_posted.desc()).all()
    projects = Project.query.order_by(Project.id.desc()).all()
    return render_template('admin/admin.html',
                           title='Admin Dashboard',
                           blog_posts=blog_posts,
                           projects=projects,
                           form=form)

# --- Blog Post Management ---
ALLOWED_TAGS = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'p', 'pre', 'strong', 'ul', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'hr', 'img', 'div', 'span', 'table', 'thead', 'tbody', 'tr', 'th', 'td']
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'width', 'height'],
    'table': ['border', 'cellpadding', 'cellspacing'],
    'td': ['colspan', 'rowspan'],
    'th': ['colspan', 'rowspan'],
    '*': ['class', 'style'],
}

@app.route('/admin/blog/new', methods=['GET', 'POST'])
@login_required
def new_blog_post():
    form = BlogPostForm()
    if form.validate_on_submit():
        image_data = None
        image_mimetype = None
        image_filename = 'default_blog.jpg'

        if form.image.data:
            image_data, image_mimetype, original_filename = save_image_to_db(form.image.data, output_size=(800, 600))
            if image_data and original_filename:
                image_filename = original_filename

        clean_content = bleach.clean(form.content.data,
                                     tags=ALLOWED_TAGS,
                                     attributes=ALLOWED_ATTRIBUTES,
                                     css_sanitizer=css_sanitizer,
                                     strip=True)

        base_slug = slugify(form.title.data)
        slug = base_slug
        counter = 1
        while BlogPost.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        post = BlogPost(title=form.title.data, slug=slug, content=clean_content,
                        image_filename=image_filename, image_data=image_data, image_mimetype=image_mimetype)
        db.session.add(post)
        db.session.commit()
        flash('Blog post created successfully!', 'success')
        return redirect(url_for('blog_post', slug=post.slug))
    return render_template('admin/blog_post_form.html', title='New Blog Post', form=form, legend='New Blog Post')

@app.route('/admin/blog/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_blog_post(post_id):
    # Using Session.get() as recommended by SQLAlchemy 2.0
    post = db.session.get(BlogPost, post_id)
    if not post:
        return "Post not found", 404 # Or abort(404)

    form = BlogPostForm()
    if form.validate_on_submit():
        if form.image.data:
            image_data, image_mimetype, original_filename = save_image_to_db(form.image.data, output_size=(800, 600))
            if image_data:
                post.image_data = image_data
                post.image_mimetype = image_mimetype
                post.image_filename = original_filename
            else:
                flash('Failed to process new image.', 'danger')

        if post.title != form.title.data:
            post.title = form.title.data
            base_slug = slugify(form.title.data)
            slug = base_slug
            counter = 1
            while BlogPost.query.filter_by(slug=slug).first() and slug != post.slug:
                slug = f"{base_slug}-{counter}"
                counter += 1
            post.slug = slug

        post.content = bleach.clean(form.content.data,
                                     tags=ALLOWED_TAGS,
                                     attributes=ALLOWED_ATTRIBUTES,
                                     css_sanitizer=css_sanitizer,
                                     strip=True)
        db.session.commit()
        flash('Blog post updated successfully!', 'success')
        return redirect(url_for('blog_post', slug=post.slug))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('admin/blog_post_form.html', title='Edit Blog Post', form=form, legend='Edit Blog Post', current_image_id=post.id, model_name='blog')

@app.route('/admin/blog/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_blog_post(post_id):
    post = db.session.get(BlogPost, post_id)
    if not post:
        return "Post not found", 404
    db.session.delete(post)
    db.session.commit()
    flash('Blog post deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

# --- Project Management (unchanged logic, only model definition moved) ---
@app.route('/admin/project/new', methods=['GET', 'POST'])
@login_required
def new_project():
    form = ProjectForm()
    if form.validate_on_submit():
        image_data = None
        image_mimetype = None
        image_filename = 'default_project.jpg'

        if form.image.data:
            image_data, image_mimetype, original_filename = save_image_to_db(form.image.data, output_size=(600, 400))
            if image_data and original_filename:
                image_filename = original_filename

        clean_content = bleach.clean(form.content.data,
                                     tags=ALLOWED_TAGS,
                                     attributes=ALLOWED_ATTRIBUTES,
                                     css_sanitizer=css_sanitizer,
                                     strip=True)

        base_slug = slugify(form.title.data)
        slug = base_slug
        counter = 1
        while Project.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        project = Project(
            title=form.title.data,
            slug=slug,
            description=form.description.data,
            content=clean_content,
            skills_used=form.skills_used.data,
            demo_link=form.demo_link.data,
            case_study_link=form.case_study_link.data,
            image_filename=image_filename,
            image_data=image_data,
            image_mimetype=image_mimetype
        )
        db.session.add(project)
        db.session.commit()
        flash('Project created successfully!', 'success')
        return redirect(url_for('project_detail', slug=project.slug))
    return render_template('admin/project_form.html', title='New Project', form=form, legend='New Project')

@app.route('/admin/project/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return "Project not found", 404

    form = ProjectForm()
    if form.validate_on_submit():
        if form.image.data:
            image_data, image_mimetype, original_filename = save_image_to_db(form.image.data, output_size=(600, 400))
            if image_data:
                project.image_data = image_data
                project.image_mimetype = image_mimetype
                project.image_filename = original_filename
            else:
                flash('Failed to process new image.', 'danger')

        if project.title != form.title.data:
            project.title = form.title.data
            base_slug = slugify(form.title.data)
            slug = base_slug
            counter = 1
            while Project.query.filter_by(slug=slug).first() and slug != project.slug:
                slug = f"{base_slug}-{counter}"
                counter += 1
            project.slug = slug

        project.description = form.description.data
        project.content = bleach.clean(form.content.data, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, css_sanitizer=css_sanitizer, strip=True)
        project.skills_used = form.skills_used.data
        project.demo_link = form.demo_link.data
        project.case_study_link = form.case_study_link.data
        db.session.commit()
        flash('Project updated successfully!', 'success')
        return redirect(url_for('project_detail', slug=project.slug))
    elif request.method == 'GET':
        form.title.data = project.title
        form.description.data = project.description
        form.content.data = project.content
        form.skills_used.data = project.skills_used
        form.demo_link.data = project.demo_link
        form.case_study_link.data = project.case_study_link
    return render_template('admin/project_form.html', title='Edit Project', form=form, legend='Edit Project', current_image_id=project.id, model_name='project')

@app.route('/admin/project/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return "Project not found", 404
    db.session.delete(project)
    db.session.commit()
    flash('Project deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

# In app.py, within the upload_image function
@app.route('/upload_image', methods=['POST'])
@login_required
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        try:
            image_data, image_mimetype, original_filename = save_image_to_db(file)
            if image_data:
                uploaded_img = UploadedImage(filename=original_filename, data=image_data, mimetype=image_mimetype)
                db.session.add(uploaded_img)
                db.session.commit()

                # *** ENSURE _external=True IS HERE ***
                image_url = url_for('get_image', model_name='uploaded_image', image_id=uploaded_img.id, _external=True)
                
                # Add logging to confirm the generated URL
                app.logger.info(f"Generated image URL: {image_url}")

                return jsonify({'location': image_url}), 200
            else:
                app.logger.error("Failed to get image data from save_image_to_db.")
                return jsonify({'error': 'Failed to process image data'}), 500
        except Exception as e:
            app.logger.error(f"Error uploading image: {e}")
            return jsonify({'error': f'Failed to process image: {str(e)}'}), 500
    app.logger.warning("File type not allowed or no file provided for upload.")
    return jsonify({'error': 'File type not allowed or no file provided'}), 400

if __name__ == '__main__':
    with app.app_context():
        # Correctly check for table existence using inspect
        inspector = inspect(db.engine)
        if not inspector.has_table(UploadedImage.__tablename__):
            # If the table doesn't exist, create it (only for UploadedImage, others are handled by migrate)
            UploadedImage.__table__.create(db.engine)
            print(f"Table '{UploadedImage.__tablename__}' created.")
        else:
            print(f"Table '{UploadedImage.__tablename__}' already exists.")

        admin_username = os.getenv('ADMIN_USERNAME')
        admin_password = os.getenv('ADMIN_PASSWORD')
        if not User.query.filter_by(username=admin_username).first():
            if admin_username and admin_password:
                admin_user = User(username=admin_username)
                admin_user.set_password(admin_password)
                db.session.add(admin_user)
                db.session.commit()
                print(f"Admin user '{admin_username}' created successfully!")
            else:
                print("Warning: ADMIN_USERNAME or ADMIN_PASSWORD not found in .env. Admin user not created.")
        else:
            print(f"Admin user '{admin_username}' already exists.")

    #app.run(debug=True) # Run with debug=True for development
