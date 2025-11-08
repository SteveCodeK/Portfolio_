# Portfolio Web Application

A modern, responsive portfolio website built with Flask, featuring a blog system, project showcase, and admin dashboard. This application uses SQLite for data storage, Flask-Login for authentication, and includes features like image upload, skills management, and a content management system.

## Features

- 🎨 Modern, responsive design with Tailwind CSS
- 🌐 Animated homepage with Vanta.js background
- 📝 Blog system with rich text editing
- 💼 Project portfolio with image uploads
- 🔐 Secure admin dashboard
- 🎯 Skills and sub-skills management
- 📊 Content management system
- 🔄 Dynamic content loading
- 🖼️ Image optimization and storage
- 🚀 Production-ready with Gunicorn support

## Tech Stack

- **Backend**: Python/Flask
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: 
  - Tailwind CSS
  - GSAP (Animations)
  - Vanta.js (Background effects)
  - Font Awesome icons
- **Authentication**: Flask-Login
- **Forms**: Flask-WTF
- **Image Processing**: Pillow
- **Rich Text**: TinyMCE
- **Asset Pipeline**: Flask-Assets

## Installation

1. Clone the repository:
```bash
git clone https://github.com/SteveCodeK/Portfolio_.git
cd Portfolio_
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Initialize the database:
```bash
flask db upgrade
```

5. Create an admin user:
```bash
python create_admin.py
```

6. Run the development server:
```bash
python wsgi.py
```

The application will be available at `http://localhost:5000`

## Project Structure

```
Portfolio_/
├── blueprints/           # Route blueprints (auth, blog, portfolio, admin)
├── static/              # Static assets (images, CSS, JS)
├── templates/           # Jinja2 templates
│   ├── admin/          # Admin dashboard templates
│   ├── auth/           # Authentication templates
│   ├── blog/           # Blog templates
│   ├── main/           # Main site templates
│   └── portfolio/      # Portfolio templates
├── migrations/         # Database migrations
├── instance/          # Instance-specific files
├── logs/              # Application logs
├── app.py            # Application factory and main app
├── config.py         # Configuration settings
├── extension.py      # Flask extensions
├── model.py          # SQLAlchemy models
├── form.py           # WTForms definitions
└── utils.py          # Utility functions
```

## Configuration

The application uses environment variables for configuration. Create a `.env` file in the root directory with:

```env
FLASK_APP=app.py
FLASK_ENV=development  # Change to 'production' for production
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///instance/site.db
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

## Deployment

The application is configured for deployment on Render. Key deployment steps:

1. Add your repository to Render
2. Configure as a Web Service
3. Set the build command:
```bash
pip install -r requirements.txt
```

4. Set the start command:
```bash
gunicorn --log-level debug wsgi:app
```

5. Add environment variables in Render dashboard

## Features in Detail

### Admin Dashboard
- Manage blog posts, projects, and users
- Upload and manage images
- Track content statistics
- Manage skills and sub-skills

### Blog System
- Rich text editing with TinyMCE
- Image upload support
- Comment system
- Likes and ratings

### Portfolio
- Project showcase with images
- Skills display
- Animated transitions
- Responsive grid layout

### Authentication
- Secure login system
- Role-based access control
- Password hashing
- Protected admin routes

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to your branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.

## Author

**Stephen Awili**
- Website: [awilisteve.co.ke]
- GitHub: [@SteveCodeK](https://github.com/SteveCodeK)

## Acknowledgments

- Flask documentation and community
- Tailwind CSS team
- TinyMCE for the rich text editor
- Vanta.js for beautiful backgrounds
- GSAP for smooth animations