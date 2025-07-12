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

# Configure a directory for uploads
UPLOAD_FOLDER = 'static/uploads' # Make sure this directory exists!
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Basic setup (move to config.py for larger projects)
app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_dev_secret_key_here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///site.db')
# Also update your Sitemap base_url config:
# Initialize Sitemap AFTER app config is set
sitemap = Sitemap(app=app)
app.config['SITEMAP_URL_SCHEME'] = 'https' # Use https for production
app.config['SITEMAP_GENERATOR_OPTIONS'] = {'base_url': os.environ.get('SITEMAP_BASE_URL', 'http://127.0.0.1:5000')}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Redirect unauthenticated users to login page

# User Model for authentication (re-added for completeness, as it was in previous code)
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

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
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # Add a column for image paths if you want featured images

    def __repr__(self):
        return f"BlogPost('{self.title}', '{self.date_posted}')"

# Project Model (re-added for completeness, as it was in previous code)
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    skills_used = db.Column(db.String(200), nullable=True) # e.g., "Zoho CRM, Deluge"
    demo_link = db.Column(db.String(200), nullable=True)
    case_study_link = db.Column(db.String(200), nullable=True)
    # Add a column for project image paths

    def __repr__(self):
        return f"Project('{self.title}')"


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
def blog_posts_sitemap_generator(): # Renamed function for clarity (optional)
    urls = []
    # Add static pages that need to be in the sitemap here if they are not dynamically generated
    # Example for static pages (adjust changefreq and priority as needed)
    urls.append({'loc': url_for('home', _external=True), 'changefreq': 'daily', 'priority': 1.0})
    urls.append({'loc': url_for('about', _external=True), 'changefreq': 'monthly', 'priority': 0.6})
    urls.append({'loc': url_for('skills', _external=True), 'changefreq': 'monthly', 'priority': 0.6})
    urls.append({'loc': url_for('portfolio', _external=True), 'changefreq': 'weekly', 'priority': 0.9})
    urls.append({'loc': url_for('blog', _external=True), 'changefreq': 'daily', 'priority': 0.9})
    urls.append({'loc': url_for('contact', _external=True), 'changefreq': 'monthly', 'priority': 0.5})


    for post in BlogPost.query.all():
        urls.append({
            'loc': url_for('blog_post', post_id=post.id, _external=True),
            'lastmod': post.date_posted.isoformat() + 'Z' if post.date_posted else None, # Add 'Z' for UTC
            'changefreq': 'weekly', # How often it changes
            'priority': 0.8 # Importance relative to other pages (0.0 to 1.0)
        })
    return urls

@sitemap.register_generator
def projects_sitemap_generator(): # Renamed function for clarity (optional)
    urls = []
    for project in Project.query.all():
        urls.append({
            'loc': url_for('project_detail', project_id=project.id, _external=True),
            'lastmod': None, # Add a 'last_updated' field to Project model if needed for this
            'changefreq': 'monthly',
            'priority': 0.7
        })
    return urls


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

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
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
@app.route('/blog/<int:post_id>')
def blog_post(post_id):
    post = BlogPost.query.get_or_404(post_id)
    meta_desc = post.content[:160] + '...' if len(post.content) > 160 else post.content
    # Use 'blog_post.html' for the individual post detail view
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
        clean_content = bleach.clean(form.content.data,
                                     tags=ALLOWED_TAGS,
                                     attributes=ALLOWED_ATTRIBUTES,
                                     strip=True)
        post = BlogPost(title=form.title.data, content=clean_content)
        db.session.add(post)
        db.session.commit()
        flash('Blog post created successfully!', 'success')
        return redirect(url_for('blog_post', post_id=post.id))
    return render_template('admin/blog_post_form.html', title='New Blog Post', form=form, legend='New Blog Post')

@app.route('/admin/blog/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_blog_post(post_id):
    post = BlogPost.query.get_or_404(post_id)
    form = BlogPostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = bleach.clean(form.content.data,
                                     tags=ALLOWED_TAGS,
                                     attributes=ALLOWED_ATTRIBUTES,
                                     strip=True)
        db.session.commit()
        flash('Blog post updated successfully!', 'success')
        return redirect(url_for('blog_post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('admin/blog_post_form.html', title='Edit Blog Post', form=form, legend='Edit Blog Post')

@app.route('/admin/blog/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_blog_post(post_id):
    post = BlogPost.query.get_or_404(post_id)
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
        project = Project(
            title=form.title.data,
            description=form.description.data,
            skills_used=form.skills_used.data,
            demo_link=form.demo_link.data,
            case_study_link=form.case_study_link.data
        )
        db.session.add(project)
        db.session.commit()
        flash('Project created successfully!', 'success')
        return redirect(url_for('project_detail', project_id=project.id))
    return render_template('admin/project_form.html', title='New Project', form=form, legend='New Project')

@app.route('/admin/project/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    form = ProjectForm()
    if form.validate_on_submit():
        project.title = form.title.data
        project.description = form.description.data
        project.skills_used = form.skills_used.data
        project.demo_link = form.demo_link.data
        project.case_study_link = form.case_study_link.data
        db.session.commit()
        flash('Project updated successfully!', 'success')
        return redirect(url_for('project_detail', project_id=project.id))
    elif request.method == 'GET':
        form.title.data = project.title
        form.description.data = project.description
        form.skills_used.data = project.skills_used
        form.demo_link.data = project.demo_link
        form.case_study_link.data = project.case_study_link
    return render_template('admin/project_form.html', title='Edit Project', form=form, legend='Edit Project')

@app.route('/admin/project/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
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
        filename = secure_filename(file.filename)
        unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)

        image_url = url_for('static', filename=f'uploads/{unique_filename}', _external=True)
        return jsonify({'location': image_url}), 200
    return jsonify({'error': 'File type not allowed'}), 400

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin')
            admin_user.set_password('adminpassword') # CHANGE THIS PASSWORD IMMEDIATELY!
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created with username 'admin' and password 'adminpassword'")
    
