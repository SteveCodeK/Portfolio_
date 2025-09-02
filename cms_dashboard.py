from flask import Blueprint, render_template
from model import Project, BlogPost, User, Skill, SubSkill, Comment, Rating, Like
from flask_login import login_required
from extension import db

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/admin")

@dashboard_bp.route("/dashboard")
@dashboard_bp.route("/")
@login_required
def admin_dashboard():
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

    # Example: top 5 latest projects
    latest_projects = Project.query.order_by(Project.date_posted.desc()).limit(5).all()

    # Example: top 5 latest blog posts
    latest_blogs = BlogPost.query.order_by(BlogPost.date_posted.desc()).limit(5).all()

    return render_template(
        "admin/admin_dashboard.html",
        stats=stats,
        latest_projects=latest_projects,
        latest_blogs=latest_blogs
    )