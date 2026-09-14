"""Public course URL validation, shared by writes and availability checks."""
import re

RESERVED = {'new', 'create', 'edit', 'search', 'categories', 'pending', 'my-courses',
            'checkout-info', 'slug-availability', 'tools', 'featured', 'popular', 'enrolled'}


def validate_course_slug(value):
    if value is None or value == '':
        return None
    value = value.strip().lower()
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', value) or not 3 <= len(value) <= 120:
        raise ValueError('Use 3–120 lowercase letters, numbers and single hyphens for the course link.')
    if value.isdigit() or value in RESERVED:
        raise ValueError('This course link is reserved. Choose a different name.')
    return value
