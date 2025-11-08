from flask import Flask, send_file, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sitemap import Sitemap
from flask_mail import Mail
from sqlalchemy import inspect
import io
import os
from dotenv import load_dotenv

from extension import db
mail = Mail()
from model import User, UploadedImage, BlogPost, Project, Skill, SubSkill, Like, Comment, Rating
from flask_login import current_user, login_user, logout_user, login_required
from form import LoginForm, SkillForm, SubSkillForm, BlogPostForm, ProjectForm, CommentForm
import bleach
from slugify import slugify
from flask_mail import Message
from utils import allowed_file, save_image_to_db, css_sanitizer

load_dotenv()

app = Flask(__name__)
# When running this module directly we need a minimal initialization so
# extensions (like Flask-SQLAlchemy) are registered with the app before
# we access things like `db.engine` in the `__main__` block below.
# If you use the factory `create_app`, this will be a no-op when the
# factory also initializes the extensions.
#
# Load config based on FLASK_ENV (matches logic inside create_app)
config_name = os.environ.get('FLASK_ENV', 'default')
# Attempt to load configuration class in a robust way. The project's
# `config.py` exposes a `config` dict mapping keys like 'default',
# 'development', etc. to config classes. Try attribute first, then
# fall back to the mapping.
try:
    import config as app_config
    if hasattr(app_config, config_name):
        app.config.from_object(getattr(app_config, config_name))
    else:
        cfg = app_config.config.get(config_name, app_config.config.get('default'))
        app.config.from_object(cfg)
except Exception:
    # If loading config fails for any reason, continue with defaults
    # and let later code raise a clearer error if needed.
    pass
# Initialize extensions so `db` and `mail` are bound to this `app` when
# the module is executed directly (prevents "app not registered" errors).
db.init_app(app)
mail.init_app(app)
# Ensure Flask-Login's LoginManager is initialized for module-level runs
# so templates can access `current_user` via the context processor.
from flask_login import LoginManager as _LoginManager
login_manager = _LoginManager()
login_manager.init_app(app)
from flask_login import current_user as _current_user


@app.context_processor
def inject_current_user():
    """Ensure `current_user` is always available in templates.

    Flask-Login normally provides this via its own context processor when
    the LoginManager is initialized. Some runtime/import paths in this
    project can bypass that hook, so we inject the proxy explicitly to
    avoid Jinja `UndefinedError`.
    """
    return {'current_user': _current_user}


# Register admin blueprint at module import time so templates that call
# `url_for('admin.<endpoint>')` are resolvable when the module-level `app`
# is used directly (some parts of the code render templates without
# using the application factory). The full application factory also
# registers blueprints when used.
try:
    from blueprints.admin.views import bp as admin_bp
    app.register_blueprint(admin_bp)
except Exception:
    # If registration fails (e.g. during certain import paths), continue
    # and let create_app register the blueprint later.
    pass

# Also register auth blueprint at module import time so compatibility
# redirects to `url_for('auth.login')` resolve when running this module
# directly (the factory registers all blueprints when used normally).
try:
    from blueprints.auth import bp as auth_bp
    app.register_blueprint(auth_bp)
except Exception:
    # If it fails here, create_app will register it later.
    pass


# Minimal user_loader for module-level runs. The full application factory
# also registers a loader when it builds the app, but when running this
# module directly we need one so `flask_login` can load users into
# `current_user` without raising an exception.
@login_manager.user_loader
def _load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except Exception:
        return None
# Load configuration and register error handlers
def create_app(config_name=None):

    # Load configuration based on environment
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    app.config.from_object(f'config.{config_name}')

    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)
    login_manager = LoginManager(app)
    # Ensure Flask-Login redirects to the auth login endpoint when protecting
    # routes with @login_required. Use setattr to avoid narrow static typing issues.
    setattr(login_manager, 'login_view', 'auth.login')
    # login_manager.login_view = 'auth.login'  # Disabled due to type error
    sitemap = Sitemap()
    sitemap.init_app(app)
    migrate = Migrate(app, db)

    # Configure logging and error handlers
    from error_handlers import configure_logging, register_error_handlers
    configure_logging(app)
    register_error_handlers(app)

    # Register blueprints
    # Register blueprints with defensive error handling so import-time
    # failures are logged and don't crash the whole process silently.
    try:
        from blueprints.main import bp as main_bp
        app.register_blueprint(main_bp)
    except Exception as e:
        app.logger.exception('Failed to register main blueprint: %s', e)

    try:
        from blueprints.blog import bp as blog_bp
        app.register_blueprint(blog_bp)
    except Exception as e:
        app.logger.exception('Failed to register blog blueprint: %s', e)

    try:
        from blueprints.portfolio import bp as portfolio_bp
        app.register_blueprint(portfolio_bp)
    except Exception as e:
        app.logger.exception('Failed to register portfolio blueprint: %s', e)

    try:
        from blueprints.auth import bp as auth_bp
        app.register_blueprint(auth_bp)
    except Exception as e:
        app.logger.exception('Failed to register auth blueprint: %s', e)

    try:
        from blueprints.admin.views import bp as admin_bp
        app.register_blueprint(admin_bp)
    except Exception as e:
        app.logger.exception('Failed to register admin blueprint: %s', e)

    # Set up user loader
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register sitemap generators
    @sitemap.register_generator
    def my_sitemap_generator():
        from model import BlogPost, Project
        # Main routes
        yield 'main.home', {'changefreq': 'daily', 'priority': 1.0}
        yield 'portfolio.index', {'changefreq': 'weekly', 'priority': 0.9}
        yield 'blog.index', {'changefreq': 'daily', 'priority': 0.9}

        # Blog posts
        for post in BlogPost.query.all():
            yield 'blog.post', {
                'slug': post.slug,
                'lastmod': post.date_posted.isoformat() + 'Z' if post.date_posted else None,
                'changefreq': 'weekly',
                'priority': 0.8
            }

        # Projects
        for project in Project.query.all():
            last_mod_date = project.date_posted.isoformat() + 'Z' if project.date_posted else None
            yield 'portfolio.project_detail', {
                'slug': project.slug,
                'lastmod': last_mod_date,
                'changefreq': 'monthly',
                'priority': 0.7
            }

    # Image serving route
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
    app.logger.info('Accessing home page')
    try:
        latest_blogs = BlogPost.query.order_by(BlogPost.date_posted.desc()).limit(3).all()
        latest_projects = Project.query.order_by(Project.id.desc()).limit(3).all()
        skills = Skill.query.all()

        # get count of skills used in projects
        # Fix join: use actual table/class, not relationship property
        from sqlalchemy.orm import aliased
        from model import SubSkill as SubSkillModel
        skill_count = db.session.query(
            Project, Skill.id,
            db.func.count(Skill.id)
        ).join(Project.subskills.of_type(SubSkillModel)).join(Skill, SubSkillModel.skill_id == Skill.id).group_by(Project.id, Skill.id).all()

        app.logger.debug(f'Retrieved {len(latest_blogs)} blogs, {len(latest_projects)} projects, {len(skills)} skills')
        # Calculate total projects for the About section
        total_projects = Project.query.count()
        # Templates are organized under the `templates/main/` directory.
        # Use the explicit path to avoid TemplateNotFound errors when the
        # default template name isn't located at the top-level templates dir.
        return render_template('main/index.html', latest_blogs=latest_blogs, latest_projects=latest_projects, skills=skills, skill_used=skill_count, total_projects=total_projects)
    except Exception as e:
        app.logger.error('Error in home page:', exc_info=True)
        raise

@app.route('/about')
def about():
    return render_template('about.html', title='About Me')


# Backwards-compatible convenience route: /login -> /auth/login
@app.route('/login')
def legacy_login():
    return redirect(url_for('auth.login', next=request.args.get('next')))

@app.route("/contact", methods=["POST"])
def contact():
    app.logger.info('Contact form submission received')
    
    name = request.form.get("name")
    email = request.form.get("email")
    message = request.form.get("message")
    try:
        if not all([name, email, message]):
            app.logger.warning('Incomplete contact form submission')
            flash("Please fill in all fields", "danger")
            return redirect(url_for("home"))

        app.logger.info(f'Processing contact form submission from {email}')
        msg = Message(
            subject=f"New Contact Form Submission from {name}",
            recipients=[app.config['MAIL_DEFAULT_SENDER']],
            body=f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
        )
        mail.send(msg)
        app.logger.info(f'Successfully sent contact email from {email}')
        flash("Your message has been sent successfully!", "success")
        return redirect(url_for("home"))
    except Exception as e:
        app.logger.error('Error processing contact form:', exc_info=True)
        flash("There was an error sending your message. Please try again later.", "danger")
        return redirect(url_for("home"))

@app.route("/portfolio/skill/<int:skill_id>")
def portfolio_by_skill(skill_id):
    skill = Skill.query.get_or_404(skill_id)
    # Get projects linked via subskills
    from model import SubSkill as SubSkillModel
    projects = Project.query.join(Project.subskills.of_type(SubSkillModel)).join(Skill, SubSkillModel.skill_id == Skill.id).filter(Skill.id == skill_id).all()
    return render_template("portfolio/index.html", projects=projects, filter_type="skill", filter_name=skill.name)


@app.route("/portfolio/subskill/<int:subskill_id>")
def portfolio_by_subskill(subskill_id):
    subskill = SubSkill.query.get_or_404(subskill_id)
    projects = subskill.projects  # direct relationship
    return render_template("portfolio/index.html", projects=projects, filter_type="subskill", filter_name=subskill.name)

@app.route('/portfolio')
def portfolio():
    projects = Project.query.all()
    return render_template('portfolio/index.html', projects=projects, title='My Portfolio')


@app.route('/project/<string:slug>', methods=["GET", "POST"])
def project_detail(slug):
    app.logger.info(f'Accessing project detail page for slug: {slug}')
    try:
        project = Project.query.filter_by(slug=slug).first_or_404()
        app.logger.debug(f'Retrieved project: {project.title}')
        form = CommentForm()

        if form.validate_on_submit():
            app.logger.info(f'Processing feedback submission for project: {project.title}')
            try:
                # Handle Like separately
                if form.like.data == "true":
                    app.logger.debug(f'Adding like to project: {project.title}')
                    like = Like()
                    like.guest_name = form.guest_name.data if not current_user.is_authenticated else None
                    like.guest_email = form.guest_email.data if not current_user.is_authenticated else None
                    like.project_id = project.id
                    db.session.add(like)

                # Handle Comment & Rating
                if form.content.data or form.rating.data:
                    app.logger.debug(f'Adding comment/rating to project: {project.title}')
                    comment = Comment()
                    comment.content = form.content.data
                    comment.guest_name = form.guest_name.data if not current_user.is_authenticated else None
                    comment.guest_email = form.guest_email.data if not current_user.is_authenticated else None
                    comment.project_id = project.id
                    db.session.add(comment)

                    if form.rating.data:
                        rating = Rating()
                        rating.score = form.rating.data
                        rating.guest_name = form.guest_name.data if not current_user.is_authenticated else None
                        rating.guest_email = form.guest_email.data if not current_user.is_authenticated else None
                        rating.project_id = project.id
                        db.session.add(rating)

                db.session.commit()
                app.logger.info(f'Successfully saved feedback for project: {project.title}')
                flash("Your feedback has been submitted!", "success")
                return redirect(url_for("project_detail", slug=slug))
            except Exception as e:
                db.session.rollback()
                app.logger.error('Error saving feedback:', exc_info=True)
                flash("There was an error submitting your feedback. Please try again.", "danger")

        return render_template("portfolio/project_detail.html", project=project, form=form, title=project.title)
    except Exception as e:
        app.logger.error(f'Error accessing project {slug}:', exc_info=True)
        raise


@app.route('/blog')
def blog():
    try:
        app.logger.info('Accessing blog page')
        page = request.args.get('page', 1, type=int)
        app.logger.debug(f'Fetching blog posts for page {page}')
        
        blog_posts = BlogPost.query.order_by(BlogPost.date_posted.desc()).paginate(page=page, per_page=5, error_out=False)
        
        app.logger.info(f'Successfully retrieved {len(blog_posts.items)} posts for page {page}')
        return render_template('blog/index.html', blog_posts=blog_posts, title='My Blog')
    except Exception as e:
        app.logger.error('Error retrieving blog posts:', exc_info=True)
        raise

@app.route('/blog/<string:slug>', methods=["GET", "POST"])
def blog_post(slug):
    post = BlogPost.query.filter_by(slug=slug).first_or_404()
    form = CommentForm()

    if form.validate_on_submit():
        # Handle Like separately
        if form.like.data == "true":
            like = Like()
            like.guest_name = form.guest_name.data if not current_user.is_authenticated else None
            like.guest_email = form.guest_email.data if not current_user.is_authenticated else None
            like.post_id = post.id
            db.session.add(like)

        # Handle Comment & Rating
        if form.content.data or form.rating.data:
            comment = Comment()
            comment.content = form.content.data
            comment.guest_name = form.guest_name.data if not current_user.is_authenticated else None
            comment.guest_email = form.guest_email.data if not current_user.is_authenticated else None
            comment.post_id = post.id
            db.session.add(comment)

            if form.rating.data:
                rating = Rating()
                rating.score = form.rating.data
                rating.guest_name = form.guest_name.data if not current_user.is_authenticated else None
                rating.guest_email = form.guest_email.data if not current_user.is_authenticated else None
                rating.post_id = post.id
                db.session.add(rating)

        db.session.commit()
        flash("Your feedback has been submitted!", "success")
        return redirect(url_for("blog_post", slug=slug))

    return render_template("blog/post.html", post=post, form=form, title=post.title)



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

# Note: All admin CRUD routes are handled in the `admin` blueprint.
# The app-level stubs were intentionally removed to keep the blueprint
# as the single source of truth for admin functionality.

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
                uploaded_img = UploadedImage()
                uploaded_img.filename = original_filename
                uploaded_img.data = image_data
                uploaded_img.mimetype = image_mimetype
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

# --- Project Management (unchanged logic, only model definition moved) ---

# User management moved to the admin blueprint; app-level stubs removed.


if __name__ == '__main__':
    with app.app_context():
        # Correctly check for table existence using inspect
        inspector = inspect(db.engine)
        # UploadedImage table creation (if not exists)
        if not inspector.has_table('uploaded_image'):
            db.Model.metadata.create_all(db.engine)
            print("Table 'uploaded_image' created.")
        else:
            print("Table 'uploaded_image' already exists.")

        admin_username = os.getenv('ADMIN_USERNAME')
        admin_password = os.getenv('ADMIN_PASSWORD')
        if not User.query.filter_by(username=admin_username).first():
            if admin_username and admin_password:
                admin_user = User()
                admin_user.username = admin_username
                admin_user.set_password(admin_password)
                db.session.add(admin_user)
                db.session.commit()
                print(f"Admin user '{admin_username}' created successfully!")
            else:
                print("Warning: ADMIN_USERNAME or ADMIN_PASSWORD not found in .env. Admin user not created.")
        else:
            print(f"Admin user '{admin_username}' already exists.")

    app.run(debug=True) # Run with debug=True for development
