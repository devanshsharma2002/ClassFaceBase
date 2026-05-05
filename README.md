# 🎓 ClassFace
### AI-Powered Classroom Attendance from Group Photos

Multi-college • Multi-teacher • Face Recognition System

---

## 🚀 Overview

ClassFace is an AI-powered attendance system that automatically marks classroom attendance from 3–4 classroom group photos using face recognition.

It supports a multi-tenant academic hierarchy:

**College → Department → Teacher → Subject → Class**

Designed for real-world campus deployment and placement-level projects.

---

## ✨ Features

- 📸 Batch Photo Attendance (3–4 images → full class marked automatically)
- 🏫 Multi-tenant architecture
- 👨‍🏫 Teacher dashboard with role-based access
- 🧠 Face recognition using 128D embeddings
- 📊 Lecture audit trail
- 🔐 JWT authentication
- 📱 REST API ready for mobile/web frontend
- ⚡ Fast processing (~8 seconds for 60 students × 4 photos)

---

## 🎯 How It Works

1. Teacher logs in  
2. Selects subject (e.g., CS101)  
3. Uploads 3–4 classroom photos  
4. AI detects all faces in batch  
5. Faces matched with enrolled students  
6. Attendance marked Present/Absent  
7. Record saved with teacher signature  

---

## 🛠 Tech Stack

**Backend**
- Django 4.2
- Django REST Framework

**Face Recognition**
- face_recognition
- OpenCV

**Database**
- SQLite (Development)
- PostgreSQL (Production)

**Authentication**
- JWT (SimpleJWT)
- Django Role-Based Permissions

**Deployment**
- Docker
- Gunicorn
- Nginx

---

## 📦 Installation & Setup

### 1️⃣ Clone Repository

```bash
git clone https://github.com/yourusername/ClassFace.git
cd ClassFace
pip install -r requirements.txt
```

### 2️⃣ Setup Database

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py populate_demo_data  # Optional
```

### 3️⃣ Run Development Server

```bash
python manage.py runserver
```

Admin Panel:  
http://localhost:8000/admin/

---

## 🔌 API Example

```bash
curl -X POST "http://localhost:8000/api/attendance/upload/" \
  -H "Authorization: Bearer <jwt_token>" \
  -F "subject_code=CS101" \
  -F "lecture_date=2026-02-27" \
  -F "lecture_no=1" \
  -F "photos=@class1.jpg" \
  -F "photos=@class2.jpg"
```

---

## 🏗 Project Structure

```
ClassFace/
│
├── core/
│   ├── models.py
│   ├── admin.py
│   ├── face_processor.py
│   ├── views.py
│
├── ClassFace/        # Django settings
├── templates/
├── static/
├── requirements.txt
└── README.md
```

---

## 📈 Performance

- 60 students × 4 photos → ~8 seconds processing
- 95%+ recognition accuracy (good lighting & frontal faces)
- Scalable architecture with async support (Celery-ready)

---

## 🔒 Security

- Encrypted face embeddings
- Department-scoped permissions
- JWT token expiry (24 hours)
- Manual override support

---

## 🚀 Production Deployment (Docker Example)

```dockerfile
FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements-prod.txt
CMD ["gunicorn", "ClassFace.wsgi:application", "--bind", "0.0.0.0:8000"]
```

---

## 🏆 Resume Description

ClassFace – Multi-College Face Recognition Attendance System  
Django • OpenCV • face_recognition • Multi-tenant Architecture

• Built AI-powered attendance system from classroom group photos  
• Designed scalable academic hierarchy with Django ORM  
• Developed secure REST API with JWT authentication  
• Achieved fast batch processing using 128D embeddings  



---

## 👨‍💻 Author

Devansh Sharma  
B.Tech IT  

---

⭐ If you found this project useful, consider giving it a star!
