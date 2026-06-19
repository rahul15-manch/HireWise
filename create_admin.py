from app.database import SessionLocal, engine
from app import models
from app.main import pwd_context

# Ensure tables are created
models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

email = "admin@hirewise.com"
password = "admin"
full_name = "HireWise Admin"

user = db.query(models.User).filter(models.User.email == email).first()

if user:
    user.role = "admin"
    db.commit()
    print(f"User {email} updated to admin!")
else:
    hashed_password = pwd_context.hash(password)
    admin_user = models.User(
        email=email,
        full_name=full_name,
        hashed_password=hashed_password,
        role="admin"
    )
    db.add(admin_user)
    db.commit()
    print(f"Admin user created successfully!\nEmail: {email}\nPassword: {password}")

db.close()
