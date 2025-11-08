from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app
from flask_login import current_user
from model import Project, Skill, SubSkill, Comment, Like, Rating
from form import CommentForm
from extension import db

bp = Blueprint('portfolio', __name__, url_prefix='/portfolio')

@bp.route('/')
def index():
    current_app.logger.info('Accessing portfolio page')
    try:
        projects = Project.query.all()
        return render_template('portfolio/index.html', projects=projects, title='My Portfolio')
    except Exception as e:
        current_app.logger.error('Error retrieving projects:', exc_info=True)
        raise

@bp.route('/skill/<int:skill_id>')
def by_skill(skill_id):
    current_app.logger.info(f'Accessing projects by skill ID: {skill_id}')
    try:
        skill = Skill.query.get_or_404(skill_id)
        from sqlalchemy.orm import aliased
        from model import SubSkill as SubSkillModel
        projects = Project.query.join(Project.subskills.of_type(SubSkillModel)).join(Skill, SubSkillModel.skill_id == Skill.id).filter(Skill.id == skill_id).all()
        return render_template("portfolio/index.html", projects=projects, filter_type="skill", filter_name=skill.name)
    except Exception as e:
        current_app.logger.error(f'Error retrieving projects for skill {skill_id}:', exc_info=True)
        raise

@bp.route('/subskill/<int:subskill_id>')
def by_subskill(subskill_id):
    current_app.logger.info(f'Accessing projects by subskill ID: {subskill_id}')
    try:
        subskill = SubSkill.query.get_or_404(subskill_id)
        projects = subskill.projects
        return render_template("portfolio/index.html", projects=projects, filter_type="subskill", filter_name=subskill.name)
    except Exception as e:
        current_app.logger.error(f'Error retrieving projects for subskill {subskill_id}:', exc_info=True)
        raise

@bp.route('/project/<string:slug>', methods=["GET", "POST"])
def project_detail(slug):
    current_app.logger.info(f'Accessing project detail: {slug}')
    try:
        project = Project.query.filter_by(slug=slug).first_or_404()
        form = CommentForm()

        if form.validate_on_submit():
            current_app.logger.info(f'Processing feedback for project: {project.title}')
            try:
                # Handle Like
                if form.like.data == "true":
                    like = Like()
                    like.guest_name = form.guest_name.data if not current_user.is_authenticated else None
                    like.guest_email = form.guest_email.data if not current_user.is_authenticated else None
                    like.project_id = project.id
                    db.session.add(like)

                # Handle Comment & Rating
                if form.content.data or form.rating.data:
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
                current_app.logger.info(f'Successfully saved feedback for project: {project.title}')
                flash("Your feedback has been submitted!", "success")
                return redirect(url_for("portfolio.project_detail", slug=slug))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error('Error saving feedback:', exc_info=True)
                flash("There was an error submitting your feedback. Please try again.", "danger")

        return render_template("portfolio/project_detail.html", project=project, form=form, title=project.title)
    except Exception as e:
        current_app.logger.error(f'Error accessing project {slug}:', exc_info=True)
        raise