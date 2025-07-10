📘 STVT – Summer Training Internship Portal
A complete web-based system built using Django for managing student summer internships at STC Charbagh, including:

Student registration and login

LOR upload (optional)

Fee challan generation and payment verification

Project selection (with seat limits and branch filters)

Batch allotment + Admit card generation

Internship certificate verification and issuance

🔧 Features
🎓 Student Panel
Registration with photo and academic info

Auto-generated unique student ID

Login and dashboard with multiple tabs

Fee challan download and upload

Project selection based on branch and slot availability

Admit card download (after approval)

Certificate tracking and download

🛠️ Admin Panel
Django admin with custom buttons and actions

Approve students and auto-generate Unique ID

Generate fee challans and send via email

Verify payment and notify students

Approve projects and generate admit cards

Verify and send internship certificates (with auto serial number)

Filtered certificate tab for all verified and unverified students

🖥️ Tech Stack
Backend: Python, Django

Frontend: HTML, CSS (AdminLTE 3), Bootstrap

Database: SQLite (default), easily replaceable with PostgreSQL/MySQL

Email: SMTP (configured for Gmail)

PDF/HTML Document: Custom certificate & challan generation using HTML templates

📁 Project Structure
bash
Copy
Edit
stvt/
├── studentpanel/
│   ├── templates/studentpanel/
│   │   ├── dashboard.html
│   │   ├── challan.html
│   │   ├── admit_card.html
│   │   ├── certificate.html
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   ├── admin.py
├── static/
│   ├── images/  # logo used in certificate/admit
├── summer_training_portal/
├── manage.py
✨ How to Run

# Clone the repo
git clone https://github.com/your-username/stvt.git
cd stvt

# Create and activate virtual environment
python -m venv v
v\Scripts\activate   # for Windows
# or
source v/bin/activate  # for Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Run server
python manage.py runserver

📬 Contact
Developer: Nilansha Pandey
Email: nilansha777@gmail.com
GitHub: github.com/your-username

This project was developed as part of a summer training automation system. It includes:

A practical implementation of Django's admin customization

Real-world PDF-like HTML documents for challans and certificates

Auto-generated serial IDs for both students and certificates

Email-based workflow without external file generation tools
