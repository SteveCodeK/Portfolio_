"""WSGI entrypoint for Gunicorn/Render.

This file attempts to create the application via `create_app()` if
available. If that fails we fall back to the module-level `app` and
print a full traceback to stderr so platform logs capture import-time
errors.
"""
import sys
import traceback

try:
    # Prefer application factory if present
    from app import create_app
    application = create_app()
except Exception:
    # If factory fails at import-time, attempt to import a module-level
    # `app` and surface the original exception so platform logs contain
    # a clear traceback.
    try:
        from app import app as application  # fallback
    except Exception:
        # Print both the factory error and the fallback error to stderr.
        print('Error creating application via create_app().', file=sys.stderr)
        traceback.print_exc()
        # Ensure we don't leave `application` undefined. Exit with non-zero
        # so the process fails fast and logs are clear in the hosting
        # platform. Raising here will also surface the traceback to stderr.
        raise SystemExit(1)

if __name__ == '__main__':
    # Allow running locally: use Flask dev server only when executed
    # directly. Production deployment should use Gunicorn pointed at
    # this module (wsgi:application).
    if application is None:
        print('Application failed to initialize; aborting run.', file=sys.stderr)
        sys.exit(1)
    application.run(host='0.0.0.0', port=5000, debug=False)