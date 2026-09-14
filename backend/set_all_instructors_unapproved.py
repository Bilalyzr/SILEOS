from app.core.database import SessionLocal
from app.models.user import InstructorProfile

db = SessionLocal()

# Get all instructor profiles
profiles = db.query(InstructorProfile).all()

print(f'Found {len(profiles)} instructor profile(s)')

if profiles:
    for profile in profiles:
        print(f'Setting instructor profile {profile.id} (User ID: {profile.user_id}) to is_approved=False')
        profile.is_approved = False

    db.commit()
    print(f'\n✓ All {len(profiles)} instructor profiles set to unapproved (is_approved=False)')
else:
    print('No instructor profiles found in database')

db.close()
