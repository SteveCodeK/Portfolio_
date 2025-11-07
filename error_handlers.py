from flask import render_template, request
from werkzeug.exceptions import HTTPException, BadRequest, Unauthorized, Forbidden, NotFound, MethodNotAllowed, RequestTimeout
import logging
import os
from logging.handlers import RotatingFileHandler, SMTPHandler
from flask.logging import default_handler
from time import strftime
import traceback
from extension import db

class RequestFormatter(logging.Formatter):
    def format(self, record):
        record.url = request.url if request else "No URL"
        record.remote_addr = request.remote_addr if request else "No IP"
        record.method = request.method if request else "No method"
        return super().format(record)

def configure_logging(app):
    """Configure logging for the application."""
    # Remove default handler
    app.logger.removeHandler(default_handler)
    
    # Create log directory if it doesn't exist
    log_dir = os.path.join(app.root_path, app.config['LOG_DIR'])
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Set up formatters
    standard_formatter = RequestFormatter(app.config['LOG_FORMAT'])
    detailed_formatter = RequestFormatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d] '
        '- %(url)s - %(remote_addr)s - %(method)s'
    )
    
    # Configure handlers based on environment
    handlers = []
    
    # Main application log
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, app.config['LOG_FILE']),
        maxBytes=app.config['LOG_MAX_BYTES'],
        backupCount=app.config['LOG_BACKUP_COUNT']
    )
    file_handler.setFormatter(standard_formatter)
    file_handler.setLevel(getattr(logging, app.config['LOGGING_LEVEL']))
    handlers.append(file_handler)
    
    # Error log
    error_file_handler = RotatingFileHandler(
        os.path.join(log_dir, app.config['ERROR_LOG_FILE']),
        maxBytes=app.config['LOG_MAX_BYTES'],
        backupCount=app.config['LOG_BACKUP_COUNT']
    )
    error_file_handler.setFormatter(detailed_formatter)
    error_file_handler.setLevel(logging.ERROR)
    handlers.append(error_file_handler)
    
    # Access log
    access_file_handler = RotatingFileHandler(
        os.path.join(log_dir, app.config['ACCESS_LOG_FILE']),
        maxBytes=app.config['LOG_MAX_BYTES'],
        backupCount=app.config['LOG_BACKUP_COUNT']
    )
    access_file_handler.setFormatter(detailed_formatter)
    access_file_handler.setLevel(logging.INFO)
    handlers.append(access_file_handler)
    
    # Add console handler in development
    if app.config.get('LOG_TO_STDOUT', False):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(detailed_formatter)
        console_handler.setLevel(getattr(logging, app.config['LOGGING_LEVEL']))
        handlers.append(console_handler)
    
    # Configure email notifications for errors in production
    if not app.debug and not app.testing and app.config.get('MAIL_USERNAME'):
        mail_handler = SMTPHandler(
            mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
            fromaddr=app.config['MAIL_DEFAULT_SENDER'],
            toaddrs=[app.config['MAIL_DEFAULT_SENDER']],
            subject='Portfolio Application Error',
            credentials=(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD']),
            secure=() if app.config['MAIL_USE_TLS'] else None
        )
        mail_handler.setLevel(logging.ERROR)
        mail_handler.setFormatter(detailed_formatter)
        handlers.append(mail_handler)
    
    # Add all handlers to the logger
    for handler in handlers:
        app.logger.addHandler(handler)
    
    # Set overall logging level
    app.logger.setLevel(getattr(logging, app.config['LOGGING_LEVEL']))
    
    # First log message
    app.logger.info('Portfolio application startup')

def log_error(app, error, level=logging.ERROR):
    """Log error with request context."""
    error_details = {
        'url': request.url,
        'method': request.method,
        'ip': request.remote_addr,
        'user_agent': str(request.user_agent),
        'error': str(error),
        'traceback': traceback.format_exc() if not isinstance(error, HTTPException) else None
    }
    
    app.logger.log(level, f"Error occurred: {error_details}")
    return error_details

def register_error_handlers(app):
    """Register error handlers for the application."""
    
    @app.errorhandler(400)
    def bad_request_error(error):
        log_error(app, error, logging.WARNING)
        return render_template('errors/400.html', error=error.description), 400

    @app.errorhandler(401)
    def unauthorized_error(error):
        log_error(app, error, logging.WARNING)
        return render_template('errors/401.html', error=error.description), 401

    @app.errorhandler(403)
    def forbidden_error(error):
        log_error(app, error, logging.WARNING)
        return render_template('errors/403.html', error=error.description), 403

    @app.errorhandler(404)
    def not_found_error(error):
        log_error(app, error, logging.WARNING)
        return render_template('errors/404.html', error=error.description), 404

    @app.errorhandler(405)
    def method_not_allowed_error(error):
        log_error(app, error, logging.WARNING)
        return render_template('errors/405.html', error=error.description), 405

    @app.errorhandler(408)
    def request_timeout_error(error):
        log_error(app, error, logging.WARNING)
        return render_template('errors/408.html', error=error.description), 408

    @app.errorhandler(429)
    def too_many_requests_error(error):
        log_error(app, error, logging.WARNING)
        return render_template('errors/429.html', error=error.description), 429

    @app.errorhandler(500)
    def internal_error(error):
        error_details = log_error(app, error)
        db.session.rollback()  # Roll back db session in case of error
        return render_template('errors/500.html', error=error_details), 500

    @app.errorhandler(502)
    def bad_gateway_error(error):
        log_error(app, error)
        return render_template('errors/502.html', error=error.description), 502

    @app.errorhandler(503)
    def service_unavailable_error(error):
        log_error(app, error)
        return render_template('errors/503.html', error=error.description), 503

    @app.errorhandler(Exception)
    def unhandled_exception(error):
        error_details = log_error(app, error)
        
        if isinstance(error, HTTPException):
            code = error.code
            description = error.description
        else:
            code = 500
            description = str(error)
            db.session.rollback()  # Roll back db session for 500 errors
            
        # Send error notification in production
        if not app.debug and not app.testing:
            app.logger.error(f'Unhandled Exception: {error_details}')
            
        return render_template('errors/500.html', error=description), code

    # After request logging
    @app.after_request
    def after_request_logging(response):
        if response.status_code >= 400:
            app.logger.warning(
                f"{request.remote_addr} - - [{strftime('%Y-%b-%d %H:%M:%S')}] "
                f"\"{request.method} {request.path} {request.scheme}\" "
                f"{response.status_code} -"
            )
        return response