from app.core.database import SessionLocal
from app.models.user import User, InstructorProfile

db = SessionLocal()

email = 'sowmiya@sashainfinity.com'
user = db.query(User).filter(User.user_email == email).first()

if user:
    print(f'User Found:')
    print(f'  Email: {user.user_email}')
    print(f'  Role: {user.role}')
    print(f'  ID: {user.id}')
    print(f'  Status: {user.user_status}')

    profile = db.query(InstructorProfile).filter(InstructorProfile.user_id == user.id).first()
    if profile:
        print(f'\nInstructorProfile Found:')
        print(f'  ID: {profile.id}')
        print(f'  Approved: {profile.is_approved}')
        print(f'  Blocked: {profile.is_blocked}')
        print(f'  Bio: {profile.instructor_bio[:50] if profile.instructor_bio else "None"}')
        print(f'  Designation: {profile.instructor_designation}')
    else:
        print('\n*** NO INSTRUCTOR PROFILE FOUND - THIS IS THE BUG! ***')
else:
    print(f'User {email} not found')

db.close()
