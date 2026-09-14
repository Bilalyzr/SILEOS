# Legacy Data Migration to PostgreSQL

This directory contains scripts to migrate data from legacy learning management systems to SashaInfinity LMS PostgreSQL database.

## Migration Process

### Step 1: Extract Legacy Data

```bash
# Navigate to the migration directory
cd backend/app/migration

# Extract data from your legacy LMS site
python legacy_extractor.py /path/to/your/legacy/system

# This will create: legacy_data.json (contains all your site data)
```

### Step 2: Migrate to PostgreSQL

```bash
# Migrate extracted data to PostgreSQL
python data_migrator.py legacy_data.json "postgresql://user:password@localhost:5432/sashainfinity_lms"
```

## What Gets Migrated

### User Data
- ✅ Users → users table
- ✅ User profiles → user_profiles table
- ✅ Instructor profiles → instructor_profiles table
- ✅ User roles → user_roles table

### Course Content
- ✅ Courses → courses table
- ✅ Lessons → lessons table
- ✅ Course metadata → course fields
- ✅ Course categories/tags → course_categories, course_tags tables

### Quiz System
- ✅ Quizzes → quizzes table
- ✅ Quiz questions → quiz_questions table
- ✅ Quiz answers → quiz_question_answers table
- ✅ Quiz attempts → quiz_attempts table
- ✅ Quiz attempt answers → quiz_attempt_answers table

### Enrollment & Progress
- ✅ Course enrollments → enrollments table
- ✅ Lesson progress → lesson_progress table
- ✅ Student activities → student_course_activities table

### E-commerce
- ✅ Orders → orders table
- ✅ Order items → order_items table
- ✅ Payments → payments table
- ✅ Coupons → coupons table

### Instructor Earnings
- ✅ Earnings → earnings table
- ✅ Withdrawals → withdrawals table

### Certificates
- ✅ Certificate templates → certificates table
- ✅ Generated certificates → issued_certificates table

## Legacy Configuration

The extractor automatically reads your legacy system configuration file to get database credentials.

## Dependencies

Install required Python packages:

```bash
pip install mysql-connector-python asyncpg
```

## Data Validation

After migration, the scripts provide detailed statistics:

```
📊 Migration Summary:
   Users: 245
   Courses: 12
   Lessons: 89
   Quizzes: 23
   Enrollments: 1,234
   Orders: 567
```

## Troubleshooting

### Common Issues

1. **MySQL Connection Error**
   - Verify legacy system database credentials
   - Ensure MySQL server is accessible
   - Check firewall settings

2. **PostgreSQL Connection Error**
   - Verify PostgreSQL URL format
   - Ensure PostgreSQL server is running
   - Check database exists and permissions

3. **Missing Tables**
   - Some legacy LMS tables may not exist if features aren't used
   - Scripts handle missing tables gracefully

### Error Handling

- Scripts continue on errors and report issues at the end
- Failed records are logged with specific error messages
- Partial migrations can be resumed safely (uses ON CONFLICT DO NOTHING)

## Custom Fields

If you have custom fields or plugins, you may need to extend the scripts:

1. Add custom table extraction in `legacy_extractor.py`
2. Add corresponding migration logic in `data_migrator.py`
3. Update PostgreSQL models if needed

## Performance

- Large sites (10K+ users, 1K+ courses) may take 10-30 minutes
- Progress is displayed in real-time
- Memory usage scales with data size (JSON file is loaded entirely)

## Security

- Database credentials are never stored in migration files
- All SQL queries use parameterized statements
- JSON output contains actual data - handle securely