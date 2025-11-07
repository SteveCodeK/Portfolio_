from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app
from flask_mail import Message
from model import BlogPost, Project, Skill
from extension import db
from flask_mail import Mail
mail = Mail()

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/home')
def home():
    current_app.logger.info('Accessing home page')
    try:
        latest_blogs = BlogPost.query.order_by(BlogPost.date_posted.desc()).limit(3).all()
        latest_projects = Project.query.order_by(Project.id.desc()).limit(3).all()
        skills = Skill.query.all()
        
        # get count of skills used in projects
        from sqlalchemy.orm import aliased
        from model import SubSkill as SubSkillModel
        skill_count = db.session.query(
            Project, Skill.id,
            db.func.count(Skill.id)
        ).join(Project.subskills.of_type(SubSkillModel)).group_by(Project.id, Skill.id).all()
        
        current_app.logger.debug(f'Retrieved {len(latest_blogs)} blogs, {len(latest_projects)} projects, {len(skills)} skills')
        return render_template('main/index.html', 
                             latest_blogs=latest_blogs, 
                             latest_projects=latest_projects, 
                             skills=skills, 
                             skill_used=skill_count)
    except Exception as e:
        current_app.logger.error('Error in home page:', exc_info=True)
        raise

@bp.route('/about')
def about():
    current_app.logger.info('Accessing about page')
    return render_template('main/about.html', title='About Me')

@bp.route("/contact", methods=["POST"])
def contact():
    current_app.logger.info('Contact form submission received')
    
    try:
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")
        
        if not all([name, email, message]):
            current_app.logger.warning('Incomplete contact form submission')
            flash("Please fill in all fields", "danger")
            return redirect(url_for("main.home"))

        current_app.logger.info(f'Processing contact form submission from {email}')
        
        msg = Message(
            subject=f"New Contact Form Submission from {name}",
            recipients=[current_app.config['MAIL_DEFAULT_SENDER']],
            body=f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
        )
        mail.send(msg)
        
        current_app.logger.info(f'Successfully sent contact email from {email}')
        flash("Your message has been sent successfully!", "success")
        return redirect(url_for("main.home"))
        
    except Exception as e:
        current_app.logger.error('Error processing contact form:', exc_info=True)
        flash("There was an error sending your message. Please try again later.", "danger")
        return redirect(url_for("main.home"))

# Robots.txt route
@bp.route('/robots.txt')
def robots_txt():
    from flask import send_from_directory
    static_folder = current_app.static_folder or 'static'
    return send_from_directory(static_folder, request.path[1:])