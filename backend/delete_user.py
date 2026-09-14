from app.core.database import SessionLocal
from app.models.user import User

db = SessionLocal()

email = 'sowmiya@sashainfinity.com'
user = db.query(User).filter(User.user_email == email).first()

if user:
    print(f'Deleting user: {user.user_email} (role: {user.role})')
    db.delete(user)
    db.commit()
    print('User deleted successfully')
else:
    print(f'User {email} not found')

db.close()
