from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, current_app
from flask_login import login_required, current_user
from model import BlogPost, Project, User, UploadedImage, Skill, SubSkill, Comment, Rating, Like
from form import BlogPostForm, ProjectForm, LoginForm, SkillForm, SubSkillForm
from extension import db
from utils import save_image_to_db, allowed_file, clean_content
from slugify import slugify

bp = Blueprint('admin', __name__, url_prefix='/admin')

# --- Dashboard Routes ---
@bp.route('/dashboard')
@login_required
def dashboard():
    # Build simple stats and latest items (same as cms_dashboard.py)
    stats = {
        "users": User.query.count(),
        "projects": Project.query.count(),
        "blog_posts": BlogPost.query.count(),
        "skills": Skill.query.count(),
        "subskills": SubSkill.query.count(),
        "comments": Comment.query.count(),
        "ratings": Rating.query.count(),
        "likes": Like.query.count(),
    }

    latest_projects = Project.query.order_by(Project.date_posted.desc()).limit(5).all()
    latest_blogs = BlogPost.query.order_by(BlogPost.date_posted.desc()).limit(5).all()

    return render_template('admin/admin_dashboard.html', title='Admin Dashboard', stats=stats,
                           latest_projects=latest_projects, latest_blogs=latest_blogs)


@bp.route('/')
@login_required
def index():
    # Provide `/admin` root — redirect or render dashboard content.
    return redirect(url_for('admin.dashboard'))

@bp.route('/manage-blog')
@login_required
def manage_blog():
    form = LoginForm()
    blog_posts = BlogPost.query.order_by(BlogPost.date_posted.desc()).all()
    return render_template('admin/manage_blog.html', title='Manage BlogPost', blog_posts=blog_posts, form=form)

@bp.route('/manage-project')
@login_required
def manage_projects():
    form = LoginForm()
    projects = Project.query.order_by(Project.id.desc()).all()
    return render_template('admin/manage_project.html', title='Manage Project', projects=projects, form=form)

@bp.route('/users')
@login_required
def manage_users():
    form = LoginForm()
    users = User.query.order_by(User.id.desc()).all()
    return render_template('admin/manage_users.html', title='Users', users=users, form=form)

@bp.route('/skills')
@login_required
def manage_skills():
    form = SkillForm()
    skills = Skill.query.order_by(Skill.id.desc()).all()
    return render_template('admin/manage_skills.html', title='Skills', skills=skills, form=form)

@bp.route('/subskills')
@login_required
def manage_subskills():
    form = SubSkillForm()
    subskills = SubSkill.query.all()
    return render_template("admin/manage_subskills.html", subskills=subskills, form=form)

# --- Blog Post Management ---
@bp.route('/blog/new', methods=['GET', 'POST'])
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

        clean_html = clean_content(form.content.data)

        base_slug = slugify(form.title.data)
        slug = base_slug
        counter = 1
        while BlogPost.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        post = BlogPost()
        post.title = form.title.data
        post.slug = slug
        post.content = clean_html
        post.image_filename = image_filename
        post.image_data = image_data
        post.image_mimetype = image_mimetype
        db.session.add(post)
        db.session.commit()
        flash('Blog post created successfully!', 'success')
        return redirect(url_for('blog.post', slug=post.slug))
    return render_template('admin/blog_post_form.html', title='New Blog Post', form=form, legend='New Blog Post')

@bp.route('/blog/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_blog_post(post_id):
    post = db.session.get(BlogPost, post_id)
    if not post:
        flash('Blog post not found.', 'error')
        return redirect(url_for('admin.manage_blog'))

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

        post.content = clean_content(form.content.data)
        db.session.commit()
        flash('Blog post updated successfully!', 'success')
        return redirect(url_for('blog.post', slug=post.slug))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('admin/blog_post_form.html', title='Edit Blog Post', form=form, 
                         legend='Edit Blog Post', current_image_id=post.id, model_name='blog')

@bp.route('/blog/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_blog_post(post_id):
    post = db.session.get(BlogPost, post_id)
    if not post:
        flash('Blog post not found.', 'error')
        return redirect(url_for('admin.manage_blog'))
    db.session.delete(post)
    db.session.commit()
    flash('Blog post deleted successfully!', 'success')
    return redirect(url_for('admin.manage_blog'))

# --- Project Management ---
@bp.route('/project/new', methods=['GET', 'POST'])
@login_required
def new_project():
    form = ProjectForm()
    skills = SubSkill.query.all()
    if form.validate_on_submit():
        image_data = None
        image_mimetype = None
        image_filename = 'default_project.jpg'

        if form.image.data:
            image_data, image_mimetype, original_filename = save_image_to_db(form.image.data, output_size=(600, 400))
            if image_data and original_filename:
                image_filename = original_filename

        clean_html = clean_content(form.content.data)

        base_slug = slugify(form.title.data)
        slug = base_slug
        counter = 1
        while Project.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        project = Project()
        project.title = form.title.data
        project.slug = slug
        project.description = form.description.data
        project.content = clean_html
        project.skills_used = form.skills_used.data
        project.subskills = form.subskills.data
        project.demo_link = form.demo_link.data
        project.case_study_link = form.case_study_link.data
        project.image_filename = image_filename
        project.image_data = image_data
        project.image_mimetype = image_mimetype
        
        project.subskills = form.subskills.data 
        db.session.add(project)
        db.session.commit()
        flash('Project created successfully!', 'success')
        return redirect(url_for('portfolio.project_detail', slug=project.slug))
    return render_template('admin/project_form.html', title='New Project', form=form, legend='New Project', skills=skills)

@bp.route('/project/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        flash('Project not found.', 'error')
        return redirect(url_for('admin.manage_projects'))

    form = ProjectForm()
    skills = SubSkill.query.all()
    
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
            project.subskills = form.subskills.data
            slug = base_slug
            counter = 1
            while Project.query.filter_by(slug=slug).first() and slug != project.slug:
                slug = f"{base_slug}-{counter}"
                counter += 1
            project.slug = slug

        project.description = form.description.data
        project.content = clean_content(form.content.data)
        project.skills_used = form.skills_used.data
        project.subskills = form.subskills.data
        project.demo_link = form.demo_link.data
        project.case_study_link = form.case_study_link.data
        db.session.commit()
        flash('Project updated successfully!', 'success')
        return redirect(url_for('portfolio.project_detail', slug=project.slug))
    elif request.method == 'GET':
        form.title.data = project.title
        form.description.data = project.description
        form.content.data = project.content
        form.skills_used.data = project.skills_used
        form.subskills.data = project.subskills
        form.demo_link.data = project.demo_link
        form.case_study_link.data = project.case_study_link
    return render_template('admin/project_form.html', title='Edit Project', form=form, 
                         legend='Edit Project', current_image_id=project.id, model_name='project', skills=skills)

@bp.route('/project/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        flash('Project not found.', 'error')
        return redirect(url_for('admin.manage_projects'))
    db.session.delete(project)
    db.session.commit()
    flash('Project deleted successfully!', 'success')
    return redirect(url_for('admin.manage_projects'))

# --- Skills Management ---
@bp.route("/skill/add", methods=["GET", "POST"])
@login_required
def add_skill():
    form = SkillForm()
    if form.validate_on_submit():
        skill = Skill()
        skill.name = form.name.data
        skill.description = form.description.data
        db.session.add(skill)
        db.session.commit()
        flash("Skill added successfully!", "success")
        return redirect(url_for("admin.manage_skills"))
    return render_template("admin/skill_form.html", form=form, title="Add Skill")

@bp.route("/skill/edit/<int:skill_id>", methods=["GET", "POST"])
@login_required
def edit_skill(skill_id):
    skill = Skill.query.get_or_404(skill_id)
    form = SkillForm(obj=skill)
    if form.validate_on_submit():
        skill.name = form.name.data
        skill.description = form.description.data
        db.session.commit()
        flash("Skill updated successfully!", "success")
        return redirect(url_for("admin.manage_skills"))
    return render_template("admin/skill_form.html", form=form, title="Edit Skill")

@bp.route("/skill/delete/<int:skill_id>")
@login_required
def delete_skill(skill_id):
    skill = Skill.query.get_or_404(skill_id)
    db.session.delete(skill)
    db.session.commit()
    flash("Skill deleted.", "danger")
    return redirect(url_for("admin.manage_skills"))

# --- Subskills Management ---
@bp.route("/subskill/add", methods=["GET", "POST"])
@login_required
def add_subskill():
    form = SubSkillForm()
    form.skill_id.choices = [(s.id, s.name) for s in Skill.query.all()]
    if form.validate_on_submit():
        subskill = SubSkill()
        subskill.name = form.name.data
        subskill.skill_id = form.skill_id.data
        db.session.add(subskill)
        db.session.commit()
        flash("SubSkill added successfully!", "success")
        return redirect(url_for("admin.manage_subskills"))
    return render_template("admin/subskill_form.html", form=form, title="Add SubSkill")

@bp.route("/subskill/edit/<int:subskill_id>", methods=["GET", "POST"])
@login_required
def edit_subskill(subskill_id):
    subskill = SubSkill.query.get_or_404(subskill_id)
    form = SubSkillForm(obj=subskill)
    form.skill_id.choices = [(s.id, s.name) for s in Skill.query.all()]
    if form.validate_on_submit():
        subskill.name = form.name.data
        subskill.skill_id = form.skill_id.data
        db.session.commit()
        flash("SubSkill updated successfully!", "success")
        return redirect(url_for("admin.manage_subskills"))
    return render_template("admin/subskill_form.html", form=form, title="Edit SubSkill")

@bp.route("/subskill/delete/<int:subskill_id>")
@login_required
def delete_subskill(subskill_id):
    subskill = SubSkill.query.get_or_404(subskill_id)
    db.session.delete(subskill)
    db.session.commit()
    flash("SubSkill deleted.", "danger")
    return redirect(url_for("admin.manage_subskills"))

# --- User Management ---
@bp.route('/user/new', methods=['GET', 'POST'])
@login_required
def new_user():
    form = LoginForm()
    if form.validate_on_submit():
        user = User()
        user.username = form.username.data
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('User created successfully!', 'success')
        return redirect(url_for('admin.manage_users'))
    return render_template('admin/user_form.html', title='New User', form=form, legend='New User')

@bp.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.manage_users'))

    form = LoginForm()
    if form.validate_on_submit():
        user.username = form.username.data
        user.set_password(form.password.data)
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin.manage_users'))
    elif request.method == 'GET':
        form.username.data = user.username
    return render_template('admin/user_form.html', title='Edit User', form=form, legend='Edit User')

@bp.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.manage_users'))
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin.manage_users'))

# --- Image Upload ---
@bp.route('/upload_image', methods=['POST'])
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

                image_url = url_for('main.get_image', model_name='uploaded_image', image_id=uploaded_img.id, _external=True)
                current_app.logger.info(f"Generated image URL: {image_url}")

                return jsonify({'location': image_url}), 200
            else:
                current_app.logger.error("Failed to get image data from save_image_to_db.")
                return jsonify({'error': 'Failed to process image data'}), 500
        except Exception as e:
            current_app.logger.error(f"Error uploading image: {e}")
            return jsonify({'error': f'Failed to process image: {str(e)}'}), 500
    current_app.logger.warning("File type not allowed or no file provided for upload.")
    return jsonify({'error': 'File type not allowed or no file provided'}), 400