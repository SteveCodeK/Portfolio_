import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration class with common settings."""
    # Load all settings from environment variables with no defaults for sensitive data
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/other_uploads'
    
    # Logging Configuration
    LOG_DIR = 'logs'
    LOG_FORMAT = '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 10
    LOG_FILE = 'portfolio.log'
    ERROR_LOG_FILE = 'error.log'
    ACCESS_LOG_FILE = 'access.log'
    LOGGING_LEVEL = 'INFO'  # Default level
    
    # Mail settings - no default values for sensitive data
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))  # Port can have a safe default
    MAIL_USE_TLS = True  # Always use TLS for security
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    @classmethod
    def init_app(cls, app):
        """Base initialization."""
        # Verify required environment variables are set
        required_vars = [
            'SECRET_KEY',
            'MAIL_USERNAME',
            'MAIL_PASSWORD',
            'MAIL_DEFAULT_SENDER'
        ]
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Sitemap settings
    SITEMAP_URL_SCHEME = os.environ.get('SITEMAP_URL_SCHEME', 'https')
    SITEMAP_GENERATOR_OPTIONS = {'base_url': os.environ.get('SITEMAP_BASE_URL')}

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///instance/site.db'
    # Enable more detailed error pages
    EXPLAIN_TEMPLATE_LOADING = True
    
    # Development logging settings
    LOGGING_LEVEL = 'DEBUG'
    LOG_TO_STDOUT = True  # Also log to console in development
    LOG_FORMAT = '[%(asctime)s] %(levelname)s in %(module)s [%(pathname)s:%(lineno)d]: %(message)s'
    SQLALCHEMY_RECORD_QUERIES = True  # Log SQL queries

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    # Use a separate test database
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite:///instance/test.db'
    # Disable CSRF tokens in testing
    WTF_CSRF_ENABLED = False
    
    # Testing logging settings
    LOGGING_LEVEL = 'DEBUG'
    LOG_TO_STDOUT = True  # Log to console for tests
    LOG_FORMAT = '[%(asctime)s] %(levelname)s in %(module)s [%(pathname)s:%(lineno)d]: %(message)s'
    # Separate log files for tests
    LOG_FILE = 'test.log'
    ERROR_LOG_FILE = 'test_error.log'
    ACCESS_LOG_FILE = 'test_access.log'

class ProductionConfig(Config):
    """Production configuration."""
    # Security settings
    DEBUG = False
    TESTING = False
    
    # Secure cookie settings
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    
    # Content Security Policy
    CONTENT_SECURITY_POLICY = {
        'default-src': "'self'",
        'script-src': "'self'",
        'style-src': "'self'",
        'img-src': "'self' data:",
        'font-src': "'self'",
    }
    
    # Database and storage
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("Production database URL must be set")
    
    # Force HTTPS
    SITEMAP_URL_SCHEME = 'https'
    PREFERRED_URL_SCHEME = 'https'
    
    # Security headers
    STRICT_TRANSPORT_SECURITY = True
    STRICT_TRANSPORT_SECURITY_PRELOAD = True
    STRICT_TRANSPORT_SECURITY_MAX_AGE = 31536000  # 1 year
    
    @classmethod
    def init_app(cls, app):
        """Production-specific initialization."""
        Config.init_app(app)  # Call parent init_app
        
        # Production logging
        import logging
        from logging.handlers import SysLogHandler
        
        # Set up syslog handler
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.ERROR)
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        )
        syslog_handler.setFormatter(formatter)
        app.logger.addHandler(syslog_handler)
        
        # Validate production settings
        if not app.config['SECRET_KEY'] or len(app.config['SECRET_KEY']) < 32:
            raise ValueError("Production SECRET_KEY must be set and at least 32 characters long")
            
        # Ensure mail settings are configured
        mail_settings = ['MAIL_USERNAME', 'MAIL_PASSWORD', 'MAIL_DEFAULT_SENDER']
        if not all(app.config.get(key) for key in mail_settings):
            raise ValueError("All mail settings must be configured in production")

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
