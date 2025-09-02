# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, PasswordField, BooleanField, HiddenField, IntegerField, SelectMultipleField, SelectField
from wtforms.validators import DataRequired, Length, URL, Optional, Email, EqualTo, NumberRange, ValidationError
from flask_wtf.file import FileField, FileAllowed # Import these for file uploads
from wtforms_sqlalchemy.fields import QuerySelectMultipleField
from model import SubSkill, Skill

def subskill_query():
    return SubSkill.query.all()

def skill_choices():
    return Skill.query.all()


class BlogPostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=5, max=100)])
    content = TextAreaField('Content', validators=[DataRequired()])
    image = FileField('Featured Image (Optional)', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Images only!')])
    submit = SubmitField('Save Blog Post')

class ProjectForm(FlaskForm):
    title = StringField('Project Title', validators=[DataRequired(), Length(min=5, max=100)])
    description = TextAreaField('Short Description', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Project Details', validators=[DataRequired()])
    skills_used = StringField('Skills Used (comma-separated)', validators=[Optional(), Length(max=200)])
    skills = QuerySelectMultipleField(
        'Skills',
        query_factory=skill_choices,
        get_label='name'
    )
    subskills = QuerySelectMultipleField(
        'SubSkills',
        query_factory=subskill_query,
        get_label='name'
    )
    demo_link = StringField('Live Demo URL', validators=[Optional(), URL()])
    case_study_link = StringField('Case Study URL', validators=[Optional(), URL()])
    # If you want to handle image uploads, you'd add a FileField here
    # from flask_wtf.file import FileField, FileAllowed
    image = FileField('Project Image (Optional)', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    submit = SubmitField('Save Project')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me') # For "remember me" functionality
    submit = SubmitField('Login')

class CommentForm(FlaskForm):
    guest_name = StringField("Name ", validators=[Optional()])
    guest_email = StringField("Email ", validators=[Optional(), Email()])
    content = TextAreaField("Comment", validators=[DataRequired()])
    rating = IntegerField("Rating", validators=[Optional(), NumberRange(min=1, max=5)])
    like = HiddenField("Like")
    submit = SubmitField("Post Comment")

class SkillForm(FlaskForm):
    name = StringField("Skill Name", validators=[DataRequired()])
    description = TextAreaField("Description")
    submit = SubmitField("Save")

class SubSkillForm(FlaskForm):
    name = StringField("SubSkill Name", validators=[DataRequired()])
    skill_id = SelectField("Parent Skill", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Save")