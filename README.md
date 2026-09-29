# B2 - Assignment Management System

Simple Flask website for a college assignment submission system.

## Roles
### Admin / Professor
- Separate registration and login
- Post assignments
- Set subject, description and due date
- View student submissions
- Download submitted files

### Student
- Separate registration and login
- View posted assignments
- Submit answer text and/or file
- Update a previous submission

## Demo accounts
Admin: admin@demo.com / admin123
Student: student@demo.com / student123

## Run in VS Code (Windows)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```
Then open: http://127.0.0.1:5000
