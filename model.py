from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from extension import db


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

    comments = db.relationship('Comment', backref='blog_post', lazy=True)
    ratings = db.relationship('Rating', backref='blog_post', lazy=True)
    likes = db.relationship('Like', backref='blog_post', lazy=True)

    def __repr__(self):
        return f"BlogPost('{self.title}', '{self.date_posted}')"

# Many-to-Many table: Projects ↔ SubSkills
project_subskill = db.Table(
    'project_subskill',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('subskill_id', db.Integer, db.ForeignKey('sub_skill.id'), primary_key=True)
)

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


    comments = db.relationship('Comment', backref='project', lazy=True)
    ratings = db.relationship('Rating', backref='project', lazy=True)
    likes = db.relationship('Like', backref='project', lazy=True)
    subskills = db.relationship('SubSkill', secondary=project_subskill, back_populates='projects')

    @property
    def skill_tags(self):
        if not self.skills_used:
            return []
        return [skill.strip() for skill in self.skills_used.split(",")]

    def __repr__(self):
        return f"Project('{self.title}')"

# models.py
class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    subskills = db.relationship('SubSkill', backref='skill', lazy=True)

    def __repr__(self):
        return f"Skill('{self.name}')"


class SubSkill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey('skill.id'), nullable=False)
    projects = db.relationship('Project', secondary='project_subskill', back_populates='subskills')

    def __repr__(self):
        return f"SubSkill('{self.name}')"




class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)

    # If guest
    guest_name = db.Column(db.String(100), nullable=True)
    guest_email = db.Column(db.String(120), nullable=True)

    # Polymorphic association
    post_id = db.Column(db.Integer, db.ForeignKey('blog_post.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)

    def __repr__(self):
        who = self.user , self.guest_name
        return f"Comment(by {who}, '{self.content[:20]}...')"


class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, nullable=False)  # 1–5 stars
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)

    # For guests
    guest_name = db.Column(db.String(100), nullable=True)
    guest_email = db.Column(db.String(120), nullable=True)

    post_id = db.Column(db.Integer, db.ForeignKey('blog_post.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)

    def __repr__(self):
        who = self.user , self.guest_name
        return f"Rating({self.score} by {who})"


class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)

    # For guests
    guest_name = db.Column(db.String(100), nullable=True)
    guest_email = db.Column(db.String(120), nullable=True)

    post_id = db.Column(db.Integer, db.ForeignKey('blog_post.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)

    def __repr__(self):
        who = self.user , self.guest_name
        return f"Like(by {who})"


# NEW: Define UploadedImage model at the top level
class UploadedImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255))
    data = db.Column(db.LargeBinary)
    mimetype = db.Column(db.String(50))

    def __repr__(self):
        return f"UploadedImage('{self.filename}')"
