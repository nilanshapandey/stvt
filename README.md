🎓 STVT – Summer Training Internship Portal
A responsive and automated web portal built using Django to streamline summer internship registrations, payments, project selections, and certificate issuance for students.
-----------------------------------------------------------------------------------------------------------------------------------------------------------------
🔗 Live Demo / Preview: Coming Soon
------------------------------------------------------------------------------------------------
📄 Overview
The STVT Portal is a complete training center system that manages:

👨‍🎓 Student registration and document submission

💸 Fee challan generation, payment verification

📁 Project selection and batch allotment

🎫 Admit card and 🎓 certificate generation

📬 Email notifications at every important step
-----------------------------------------------------------------------------------------------------------------------------------------------


🧰 Technologies Used---------------
🐍 Python + Django – Backend and admin management

🖼 HTML + CSS + Bootstrap – Front-end design

📨 Django Email Backend – Sending emails (via Gmail SMTP)

🗂 SQLite – Default database (easy setup)

❌ No external PDF libraries used – Certificate and challan are styled HTML files
---------------------------------------------------------------------------------------------------------------------------------------------------
✨ Features


✅ Student Panel

Secure login/logout

Register with photo, ID, and course details

View and download challan, admit card, certificate

Track training progress through dashboard tabs

Receive status emails after admin actions
---------------------------------------------------------------------------------

✅ Admin Panel

Select students and generate challan automatically

Approve payments and allot projects

Generate admit cards and certificates

Auto-generate unique ID (STVTxx/yy) and certificate numbers

Filter by status (Pending, Sent, Verified, etc.)
----------------------------------------------------------------------------

✅ Automations

Email alerts at every important step

Certificate issued only after admin approval

Serial numbers auto-managed

Real-time dashboard updates for students
-----------------------------------------------------------------------------------

🎯 Purpose

This project was created to:

🔧 Automate summer internship training workflows

📤 Reduce manual certificate creation

📨 Integrate email notifications for better tracking

🧪 Practice real-world Django admin customization

💼 Showcase full-stack development & deployment
--------------------------------------------------------------------------------------------------------------------------
📂 Project Structure

<pre> stvt/ ├── studentpanel/ │ ├── templates/studentpanel/ │ │ ├── dashboard.html │ │ ├── admit_card.html │ │ ├── certificate.html │ │ └── ... │ ├── views.py │ ├── models.py │ ├── forms.py │ └── admin.py ├── static/ │ └── images/ # Logos and assets ├── summer_training_portal/ ├── db.sqlite3 └── manage.py </pre>

-------------------------------------------------------------------------------------------------------------------------

🛠 Setup Instructions

# Clone the repo
git clone https://github.com/your-username/stvt.git
cd stvt

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # for Windows

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Run server
python manage.py runserver


--------------------------------------------------------------------------------------------------------
📜 License

This project is open-source and available under the MIT License.
----------------------------------------------------------------------------

🙋‍♀️ Author

Made with ❤️ by Nilansha Pandey

🔗 GitHub: @nilanshapandey

📧 Email: nilansha777@gmail.com

