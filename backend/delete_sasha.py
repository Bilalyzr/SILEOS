from app.core.database import SessionLocal
from app.models.user import User, UserProfile

db = SessionLocal()

email = 'sasha@gmail.com'
user = db.query(User).filter(User.user_email == email).first()

if user:
    print(f'Deleting user: {user.user_email} (Role: {user.role})')

    # Delete profile first
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if profile:
        db.delete(profile)

    # Delete user
    db.delete(user)
    db.commit()
    print('User deleted successfully')
else:
    print(f'User {email} not found')

db.close()
