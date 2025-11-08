from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app
from flask_login import current_user
from model import BlogPost, Comment, Like, Rating
from form import CommentForm
from extension import db

bp = Blueprint('blog', __name__, url_prefix='/blog')

@bp.route('/')
def index():
    current_app.logger.info('Accessing blog page')
    try:
        page = request.args.get('page', 1, type=int)
        current_app.logger.debug(f'Fetching blog posts for page {page}')
        
        blog_posts = BlogPost.query.order_by(BlogPost.date_posted.desc()).paginate(page=page, per_page=5, error_out=False)
        
        current_app.logger.info(f'Successfully retrieved {len(blog_posts.items)} posts for page {page}')
        return render_template('blog/index.html', blog_posts=blog_posts, title='My Blog')
    except Exception as e:
        current_app.logger.error('Error retrieving blog posts:', exc_info=True)
        raise

@bp.route('/<string:slug>', methods=["GET", "POST"])
def post(slug):
    current_app.logger.info(f'Accessing blog post: {slug}')
    try:
        post = BlogPost.query.filter_by(slug=slug).first_or_404()
        form = CommentForm()

        if form.validate_on_submit():
            current_app.logger.info(f'Processing feedback for blog post: {post.title}')
            try:
                # Handle Like
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
                current_app.logger.info(f'Successfully saved feedback for blog post: {post.title}')
                flash("Your feedback has been submitted!", "success")
                return redirect(url_for("blog.post", slug=slug))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error('Error saving feedback:', exc_info=True)
                flash("There was an error submitting your feedback. Please try again.", "danger")

        return render_template("blog/post.html", post=post, form=form, title=post.title)
    except Exception as e:
        current_app.logger.error(f'Error accessing blog post {slug}:', exc_info=True)
        raise