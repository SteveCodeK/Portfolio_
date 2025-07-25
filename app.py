from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_migrate import Migrate
from form import BlogPostForm, ProjectForm, LoginForm
import bleach
from flask_sitemap import Sitemap # Correct import
import os # Already imported, just for context
from werkzeug.utils import secure_filename # Already imported, just for context
import secrets # Add this import if you haven't already
from PIL import Image 
from flask import current_app
from slugify import slugify
from dotenv import load_dotenv
load_dotenv()
# Configure a directory for uploads
UPLOAD_FOLDER = 'static/uploads' # Make sure this directory exists!
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Basic setup (move to config.py for larger projects)
app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
# Also update your Sitemap base_url config:
# Initialize Sitemap AFTER app config is set
sitemap = Sitemap(app=app)
app.config['SITEMAP_URL_SCHEME'] = 'https' # Use https for production
app.config['SITEMAP_GENERATOR_OPTIONS'] = {'base_url': os.environ.get('SITEMAP_BASE_URL')}

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Redirect unauthenticated users to login page

# User Model for authentication (re-added for completeness, as it was in previous code)
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

# Blog Post Model (re-added for completeness, as it was in previous code)
class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    image_file = db.Column(db.String(100), nullable=False, default='default.jpg') # New column for image
    # Add a column for image paths if you want featured images

    def __repr__(self):
        return f"BlogPost('{self.title}', '{self.date_posted}')"

# Project Model (re-added for completeness, as it was in previous code)
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=False) # For short text/summary
    content = db.Column(db.Text, nullable=False) # For full rich HTML content
    skills_used = db.Column(db.String(200), nullable=True) # e.g., "Zoho CRM, Deluge"
    demo_link = db.Column(db.String(200), nullable=True)
    case_study_link = db.Column(db.String(200), nullable=True)
    image_file = db.Column(db.String(100), nullable=False, default='default.jpg') # New column for image
    # Add a column for project image paths

    def __repr__(self):
        return f"Project('{self.title}')"

def save_picture(form_picture, folder='general_uploads', output_size=(125, 125)):
   
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext

    # Define the full path to the specific subfolder
    target_folder_path = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'], folder)

    # Create the folder if it doesn't exist
    os.makedirs(target_folder_path, exist_ok=True)

    picture_path = os.path.join(target_folder_path, picture_fn)

    # Open, resize, and save the image
    i = Image.open(form_picture)
    i.thumbnail(output_size) # Resize image
    i.save(picture_path)

    # Return the relative path from the UPLOAD_FOLDER, including the subfolder
    return os.path.join(folder, picture_fn).replace('\\', '/')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Robots.txt Route (correct) ---
@app.route('/robots.txt')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Sitemap Generators (FIXED) ---
@sitemap.register_generator
def my_sitemap_generator(): # You can combine them or keep separate, but the format changes
    # Static pages
    yield 'home', {'changefreq': 'daily', 'priority': 1.0}
    yield 'about', {'changefreq': 'monthly', 'priority': 0.6}
    yield 'skills', {'changefreq': 'monthly', 'priority': 0.6}
    yield 'portfolio', {'changefreq': 'weekly', 'priority': 0.9}
    yield 'blog', {'changefreq': 'daily', 'priority': 0.9}
    yield 'contact', {'changefreq': 'monthly', 'priority': 0.5}

    # Blog posts
    for post in BlogPost.query.all():
        yield 'blog_post', {
            'slug': post.slug, # Pass slug as an argument
            'lastmod': post.date_posted.isoformat() + 'Z' if post.date_posted else None,
            'changefreq': 'weekly',
            'priority': 0.8
        }

    # Projects
    for project in Project.query.all():
        # Assuming Project has a date_posted field
        last_mod_date = project.date_posted.isoformat() + 'Z' if hasattr(project, 'date_posted') and project.date_posted else None
        yield 'project_detail', {
            'slug': project.slug, # Pass slug as an argument
            'lastmod': last_mod_date,
            'changefreq': 'monthly',
            'priority': 0.7
        }


# --- Routes for Public Pages ---
@app.route('/')
@app.route('/home')
def home():
    latest_blogs = BlogPost.query.order_by(BlogPost.date_posted.desc()).limit(3).all()
    latest_projects = Project.query.order_by(Project.id.desc()).limit(3).all()
    return render_template('index.html', latest_blogs=latest_blogs, latest_projects=latest_projects)

# RE-ADDED these routes, as they were in your navbar/previous code but missing from the traceback snippet
@app.route('/about')
def about():
    return render_template('about.html', title='About Me')

@app.route('/skills')
def skills():
    return render_template('skills.html', title='My Skills')

@app.route('/portfolio')
def portfolio():
    projects = Project.query.all() # Fetch all projects from DB
    return render_template('portfolio.html', projects=projects, title='My Portfolio')

@app.route('/project/<string:slug>')
def project_detail(slug):
    project = Project.query.filter_by(slug=slug).first_or_404() # Query by slug
    return render_template('project_detail.html', project=project, title=project.title)

# CORRECTED /blog route - for listing all blog posts with pagination
@app.route('/blog')
def blog():
    page = request.args.get('page', 1, type=int)
    # Paginate blog posts, e.g., 5 posts per page
    blog_posts = BlogPost.query.order_by(BlogPost.date_posted.desc()).paginate(page=page, per_page=5, error_out=False)
    # RENDER A DEDICATED TEMPLATE FOR THE BLOG LISTING PAGE, typically 'blog.html'
    return render_template('post.html', blog_posts=blog_posts, title='My Blog')

# For individual blog posts: (corrected template name)
@app.route('/blog/<string:slug>')
def blog_post(slug):
    post = BlogPost.query.filter_by(slug=slug).first_or_404() # Query by slug
    meta_desc = post.content[:160] + '...' if len(post.content) > 160 else post.content
    return render_template('blog.html', post=post, title=post.title + ' - Stephen Awili Blog', description=meta_desc)

# RE-ADDED this route, as it was in your navbar/previous code but missing from the traceback snippet
@app.route('/contact')
def contact():
    return render_template('contact.html', title='Contact Me')

# --- Admin Routes (for uploading/managing content) ---
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
    form = LoginForm() # <--- Add this line

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
    '*': ['class', 'style'], # Allow class and style on all elements, but be cautious with 'style' for complex inline styles
}

@app.route('/admin/blog/new', methods=['GET', 'POST'])
@login_required
def new_blog_post():
    form = BlogPostForm()
    if form.validate_on_submit():
        image_file = 'default_blog.jpg'
        if form.image.data:
            image_file = save_picture(form.image.data, folder='blog_images', output_size=(800, 600))

        clean_content = bleach.clean(form.content.data,
                                     tags=ALLOWED_TAGS,
                                     attributes=ALLOWED_ATTRIBUTES,
                                     strip=True)

        # Generate slug
        base_slug = slugify(form.title.data)
        slug = base_slug
        counter = 1
        # Ensure slug is unique
        while BlogPost.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        post = BlogPost(title=form.title.data, slug=slug, content=clean_content, image_file=image_file) # Save the slug
        db.session.add(post)
        db.session.commit()
        flash('Blog post created successfully!', 'success')
        return redirect(url_for('blog_post', slug=post.slug)) # Pass slug to URL
    return render_template('admin/blog_post_form.html', title='New Blog Post', form=form, legend='New Blog Post')

@app.route('/admin/blog/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_blog_post(post_id):
    post = BlogPost.query.get_or_404(post_id)
    form = BlogPostForm()
    if form.validate_on_submit():
        if form.image.data:
            if post.image_file != 'default_blog.jpg' and os.path.exists(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], post.image_file)):
                os.remove(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], post.image_file))
            post.image_file = save_picture(form.image.data, folder='blog_images', output_size=(800, 600))

        # Only regenerate slug if title has changed
        if post.title != form.title.data:
            post.title = form.title.data
            base_slug = slugify(form.title.data)
            slug = base_slug
            counter = 1
            while BlogPost.query.filter_by(slug=slug).first() and slug != post.slug: # Check uniqueness, but allow self
                slug = f"{base_slug}-{counter}"
                counter += 1
            post.slug = slug

        post.content = bleach.clean(form.content.data,
                                     tags=ALLOWED_TAGS,
                                     attributes=ALLOWED_ATTRIBUTES,
                                     strip=True)
        db.session.commit()
        flash('Blog post updated successfully!', 'success')
        return redirect(url_for('blog_post', slug=post.slug)) # Pass slug to URL
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('admin/blog_post_form.html', title='Edit Blog Post', form=form, legend='Edit Blog Post', current_image=post.image_file)

@app.route('/admin/blog/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_blog_post(post_id):
   post = BlogPost.query.get_or_404(post_id)
    # Delete associated image file if not default
   if post.image_file != 'default_blog.jpg' and os.path.exists(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], post.image_file)):
        os.remove(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], post.image_file))
   db.session.delete(post)
   db.session.commit()
   flash('Blog post deleted successfully!', 'success')
   return redirect(url_for('admin_dashboard'))

# --- Project Management ---

@app.route('/admin/project/new', methods=['GET', 'POST'])
@login_required
def new_project():
    form = ProjectForm()
    if form.validate_on_submit():
        image_file = 'default_project.jpg'
        if form.image.data:
            image_file = save_picture(form.image.data, folder='project_images', output_size=(600, 400))

        clean_content = bleach.clean(form.content.data,
                                     tags=ALLOWED_TAGS,
                                     attributes=ALLOWED_ATTRIBUTES,
                                     strip=True)

        # Generate slug
        base_slug = slugify(form.title.data)
        slug = base_slug
        counter = 1
        # Ensure slug is unique
        while Project.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        project = Project(
            title=form.title.data,
            slug=slug, # Save the slug
            description=form.description.data,
            content=clean_content,
            skills_used=form.skills_used.data,
            demo_link=form.demo_link.data,
            case_study_link=form.case_study_link.data,
            image_file=image_file
        )
        db.session.add(project)
        db.session.commit()
        flash('Project created successfully!', 'success')
        return redirect(url_for('project_detail', slug=project.slug)) # Pass slug to URL
    return render_template('admin/project_form.html', title='New Project', form=form, legend='New Project')

@app.route('/admin/project/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    form = ProjectForm()
    if form.validate_on_submit():
        if form.image.data:
            if project.image_file != 'default_project.jpg' and os.path.exists(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], project.image_file)):
                os.remove(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], project.image_file))
            project.image_file = save_picture(form.image.data, folder='project_images', output_size=(600, 400))

        # Only regenerate slug if title has changed
        if project.title != form.title.data:
            project.title = form.title.data
            base_slug = slugify(form.title.data)
            slug = base_slug
            counter = 1
            while Project.query.filter_by(slug=slug).first() and slug != project.slug: # Check uniqueness, but allow self
                slug = f"{base_slug}-{counter}"
                counter += 1
            project.slug = slug

        project.description = form.description.data
        project.content = bleach.clean(form.content.data, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
        project.skills_used = form.skills_used.data
        project.demo_link = form.demo_link.data
        project.case_study_link = form.case_study_link.data
        db.session.commit()
        flash('Project updated successfully!', 'success')
        return redirect(url_for('project_detail', slug=project.slug)) # Pass slug to URL
    elif request.method == 'GET':
        form.title.data = project.title
        form.description.data = project.description
        form.content.data = project.content
        form.skills_used.data = project.skills_used
        form.demo_link.data = project.demo_link
        form.case_study_link.data = project.case_study_link
    return render_template('admin/project_form.html', title='Edit Project', form=form, legend='Edit Project', current_image=project.image_file)

@app.route('/admin/project/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    # Delete associated image file if not default
    if project.image_file != 'default_project.jpg' and os.path.exists(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], project.image_file)):
        os.remove(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], project.image_file))
    db.session.delete(project)
    db.session.commit()
    flash('Project deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/upload_image', methods=['POST'])
@login_required # Only logged-in users can upload images
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        try:
            # Let's save these generic uploads into a 'general' subfolder
            image_filename = save_picture(file, folder='general', output_size=(1000, 1000))
            image_url = url_for('static', filename=f'uploads/{image_filename}', _external=True)
            return jsonify({'location': image_url}), 200
        except Exception as e:
            app.logger.error(f"Error uploading image: {e}")
            return jsonify({'error': 'Failed to process image'}), 500
    return jsonify({'error': 'File type not allowed or no file provided'}), 400

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
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

    
