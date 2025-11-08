from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app
from flask_login import login_user, logout_user, current_user
from model import User
from form import LoginForm
from extension import db

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    current_app.logger.info('Login page accessed')
    
    if current_user.is_authenticated:
        current_app.logger.debug(f'Already authenticated user {current_user.username} redirected to dashboard')
        return redirect(url_for('admin.dashboard'))

    form = LoginForm()

    if form.validate_on_submit():
        try:
            user = User.query.filter_by(username=form.username.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember.data)
                current_app.logger.info(f'Successful login for user: {user.username}')
                flash('Login successful!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('admin.dashboard'))
            else:
                current_app.logger.warning(f'Failed login attempt for username: {form.username.data}')
                flash('Login Unsuccessful. Please check username and password', 'danger')
        except Exception as e:
            current_app.logger.error('Error during login process:', exc_info=True)
            raise

    return render_template('auth/login.html', title='Admin Login', form=form)

@bp.route('/logout')
def logout():
    current_app.logger.info(f'User {current_user.username if current_user.is_authenticated else "Anonymous"} logging out')
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))