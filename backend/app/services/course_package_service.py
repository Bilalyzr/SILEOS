"""Versioned, content-only course packages. Preview before restore, always a new draft."""
import copy
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import stat
import uuid
import zipfile
import bleach
from sqlalchemy import DateTime, Integer, Boolean, Numeric, JSON as SQLJSON
from app.core.config import get_settings
from app.models.course import Course, Lesson
from app.models.quiz import Quiz, QuizQuestion, QuizQuestionAnswer
from app.models.assignment import Assignment, AssignmentStatus
from app.models.mastery import ConceptLink, CourseOutcome
from app.models.course_settings import CourseStudioSettings
from app.services.course_ops_service import COURSE_COPY_FIELDS, LESSON_COPY_FIELDS, QUIZ_COPY_FIELDS, QUESTION_COPY_FIELDS, ANSWER_COPY_FIELDS, ASSIGNMENT_COPY_FIELDS

COURSE_COPY_FIELDS = COURSE_COPY_FIELDS + ('enabled_tools',)
QUIZ_COPY_FIELDS = QUIZ_COPY_FIELDS + ('quiz_available_from', 'quiz_available_until')
HTML_FIELDS = {'post_content', 'post_excerpt', 'question_description', 'answer_explanation', 'description', 'instructions'}

FORMAT = "sasha-course-backup"
VERSION = 1
MAX_UPLOAD = 200 * 1024 * 1024
MAX_EXPANDED = 500 * 1024 * 1024
MAX_MANIFEST = 20 * 1024 * 1024
FILE_EXTENSIONS = {".pdf", ".txt", ".md", ".docx", ".mp4", ".webm", ".mp3", ".wav", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".glb"}
TEXT_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}
DEPENDENCIES = {"game_id": "games", "h5p_content_id": "h5p", "three_d_model_id": "models", "geogebra_applet_id": "geogebra"}


def root():
    return Path(get_settings().UPLOAD_DIR).resolve().parent / "course_transfers"


def model_root():
    from app.routers.three_d import BASE_DIR
    return Path(BASE_DIR)


def utcnow():
    return datetime.now(timezone.utc)


def safe_path(base, relative):
    if not isinstance(relative, str) or "\\" in relative or PureWindowsPath(relative).drive or PurePosixPath(relative).is_absolute() or any(p in ("", ".", "..") for p in relative.split("/")) or any(ord(c) < 32 for c in relative):
        raise ValueError("The package contains an unsafe path.")
    target = (base / relative).resolve()
    if base.resolve() not in target.parents:
        raise ValueError("The package path escapes its storage directory.")
    return target


def primitive(v):
    if isinstance(v, Decimal): return str(v)
    if isinstance(v, datetime): return v.isoformat()
    if hasattr(v, "value"): return v.value
    return copy.deepcopy(v)


def fields(row, names):
    return {name: primitive(getattr(row, name)) for name in names}


def sanitize(value):
    if isinstance(value, str):
        return bleach.clean(value, tags=['p','br','strong','em','u','ul','ol','li','h1','h2','h3','h4','blockquote','pre','code','a','img','table','thead','tbody','tr','td','th'], attributes={'a':['href','title'], 'img':['src','alt','width','height']}, protocols=['http','https','mailto'], strip=True)
    if isinstance(value, list): return [sanitize(v) for v in value]
    if isinstance(value, dict): return {k: sanitize(v) for k, v in value.items()}
    return value


def typed(model, data, allowed):
    if not isinstance(data, dict) or set(data) - set(allowed):
        raise ValueError("Unsupported fields in the course package.")
    out = {}
    for key, val in data.items():
        column = model.__table__.columns[key]
        if val is None:
            if not column.nullable: raise ValueError(f"{key} cannot be empty.")
            out[key] = None; continue
        if isinstance(column.type, SQLJSON):
            out[key] = copy.deepcopy(val)
        elif isinstance(column.type, Boolean):
            if type(val) is not bool: raise ValueError(f"{key} must be true or false.")
            out[key] = val
        elif isinstance(column.type, Integer):
            if type(val) is not int or not -1 <= val <= 10000000: raise ValueError(f"Invalid {key}.")
            out[key] = val
        elif isinstance(column.type, Numeric):
            number = Decimal(str(val))
            if not number.is_finite() or not 0 <= number <= 10000000: raise ValueError(f"Invalid {key}.")
            out[key] = number
        elif isinstance(column.type, DateTime):
            out[key] = datetime.fromisoformat(val)
        else:
            if not isinstance(val, str) or len(val) > (getattr(column.type, 'length', None) or 400000): raise ValueError(f"Invalid {key}.")
            out[key] = sanitize(val) if key in HTML_FIELDS else val
            if key.endswith(('_url', '_poster', '_thumbnail', '_cover_image', '_intro_video')) and val:
                from urllib.parse import urlsplit
                if urlsplit(val).scheme.lower() not in ('', 'http', 'https'): raise ValueError(f'Unsafe {key}.')
    return out


def inspect_archive(path):
    try:
        archive = zipfile.ZipFile(path)
        members = archive.infolist()
        if len(members) > 10000 or len({i.filename.casefold() for i in members}) != len(members): raise ValueError("Duplicate names or too many archive entries.")
        total = 0
        for member in members:
            safe_path(root(), member.orig_filename.rstrip('/'))
            if member.orig_filename != member.filename: raise ValueError('Archive names must use portable paths.')
            if member.flag_bits & 1 or stat.S_ISLNK(member.external_attr >> 16): raise ValueError("Encrypted archives and symbolic links are not supported.")
            total += member.file_size
            if total > MAX_EXPANDED or member.file_size > MAX_UPLOAD: raise ValueError("The expanded archive is too large.")
        if 'manifest.json' not in archive.namelist(): raise ValueError("This ZIP is not a Sasha course backup: manifest.json is missing.")
        if archive.getinfo('manifest.json').file_size > MAX_MANIFEST: raise ValueError("The course manifest is too large.")
        manifest = json.loads(archive.read('manifest.json'))
        if not isinstance(manifest, dict): raise ValueError('Invalid manifest.')
        if manifest.get('format') != FORMAT or manifest.get('version') != VERSION: raise ValueError("This backup format or version is not supported.")
        if archive.getinfo('course.json').file_size > MAX_MANIFEST: raise ValueError('The course data is too large.')
        payload = archive.read('course.json')
        if len(payload) > MAX_MANIFEST or hashlib.sha256(payload).hexdigest() != manifest.get('course_sha256'): raise ValueError("The course data checksum does not match.")
        data = json.loads(payload)
        assets = manifest.get('assets', [])
        if not isinstance(assets, list) or len(assets) > 5000: raise ValueError('Invalid asset manifest.')
        verified = set(); originals = set()
        for asset in assets:
            if not isinstance(asset, dict) or not isinstance(asset.get('original'), str) or not isinstance(asset.get('path'), str): raise ValueError('Invalid asset descriptor.')
            if asset['path'] in verified or asset['original'] in originals: raise ValueError('Duplicate asset descriptor.')
            verified.add(asset['path']); originals.add(asset['original'])
            name = asset['path']; safe_path(root(), name)
            if not name.startswith('assets/') or PurePosixPath(name).suffix.lower() not in FILE_EXTENSIONS | {'.h5p'}: raise ValueError("Unsupported asset type in the backup.")
            digest = hashlib.sha256()
            with archive.open(name) as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b''): digest.update(chunk)
            if digest.hexdigest() != asset['sha256']: raise ValueError("A backup asset checksum does not match.")
        validate_data(data)
        for rows in data.get('dependencies', {}).values():
            for item in rows:
                if 'asset' in item and item['asset'] not in verified: raise ValueError('Interactive asset is not verified by the manifest.')
        warnings = manifest.get('warnings', [])
        if not isinstance(warnings, list) or any(not isinstance(w, str) for w in warnings): raise ValueError('Invalid backup warnings.')
        return data, manifest
    except (zipfile.BadZipFile, KeyError, TypeError, AttributeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("The backup is incomplete or malformed.") from exc
    finally:
        if 'archive' in locals(): archive.close()


def validate_data(data):
    if not isinstance(data, dict) or not isinstance(data.get('course'), dict): raise ValueError("Missing course metadata.")
    typed(Course, data['course'], COURSE_COPY_FIELDS + ('post_title',))
    tools = data['course'].get('enabled_tools')
    if tools is not None and (not isinstance(tools, list) or len(tools) > 100 or any(not isinstance(t, str) or len(t) > 100 for t in tools)): raise ValueError('Invalid course tool selections.')
    if not data['course'].get('post_title', '').strip(): raise ValueError("Course title is required.")
    allowed = {'lessons': (Lesson, LESSON_COPY_FIELDS), 'quizzes': (Quiz, QUIZ_COPY_FIELDS), 'assignments': (Assignment, ASSIGNMENT_COPY_FIELDS + ('rubric','order'))}
    question_ids = set()
    for section, (model, cols) in allowed.items():
        rows = data.get(section, [])
        if not isinstance(rows, list) or len(rows) > 5000: raise ValueError("Too many course items.")
        ids = set()
        for row in rows:
            if not isinstance(row, dict) or type(row.get('id')) is not int or row['id'] in ids: raise ValueError("Course item identifiers must be unique.")
            ids.add(row['id']); typed(model, row['data'], cols)
            title = row['data'].get('title' if section == 'assignments' else 'post_title')
            if not isinstance(title, str) or not title.strip(): raise ValueError('Each course item requires a title.')
            if section == 'quizzes':
                questions = row.get('questions', [])
                if not isinstance(questions, list) or len(questions) > 5000: raise ValueError('Invalid quiz questions.')
                for question in questions:
                    if not isinstance(question, dict) or type(question.get('id')) is not int or question['id'] in question_ids: raise ValueError('Invalid question identifiers.')
                    question_ids.add(question['id'])
                    typed(QuizQuestion, question['data'], QUESTION_COPY_FIELDS + ('is_retired',))
                    for answer in question.get('answers', []): typed(QuizQuestionAnswer, answer, ANSWER_COPY_FIELDS)
    sections = data.get('sections', [])
    if not isinstance(sections, list) or any(not isinstance(s, dict) or not isinstance(s.get('lectureIds', []), list) for s in sections): raise ValueError('Invalid course sections.')
    dependencies = data.get('dependencies', {})
    if not isinstance(dependencies, dict): raise ValueError('Invalid dependencies.')
    for kind, rows in dependencies.items():
        if kind not in (*DEPENDENCIES.values(), "labs", "three_d_tasks") or not isinstance(rows, list) or len(rows) > 5000: raise ValueError('Invalid dependency group.')
        ids = set()
        for item in rows:
            if not isinstance(item, dict) or type(item.get('id')) is not int or item['id'] in ids or not isinstance(item.get('data'), dict): raise ValueError('Invalid dependency identifiers.')
            ids.add(item['id'])
    if dependencies.get('geogebra') and (data['course'].get('course_price_type', 'free') != 'free' or Decimal(str(data['course'].get('course_price') or 0)) > 0): raise ValueError('GeoGebra requires a free course.')
    # Lab attachments work in every course type that supports virtual labs.
    # The type restriction applies only to standalone 3D lessons.
    if any(row['data'].get('three_d_model_id') for row in data.get('lessons', [])) and data['course'].get('course_type', 'meiporul') not in ('meiporul', 'utporul'): raise ValueError('3D models require Meiporul or Utporul courses.')
    if len(json.dumps(data)) > MAX_MANIFEST: raise ValueError("Course data is too large.")


def export_course(db, course, destination):
    data = {'course': fields(course, COURSE_COPY_FIELDS + ('post_title',)), 'sections': json.loads(course.course_sections_meta or '[]'), 'lessons': [], 'quizzes': [], 'assignments': [], 'concepts': [], 'dependencies': {}}
    for lesson in db.query(Lesson).filter_by(post_parent=course.id).order_by(Lesson.menu_order, Lesson.id):
        data['lessons'].append({'id': lesson.id, 'data': fields(lesson, LESSON_COPY_FIELDS)})
    for quiz in db.query(Quiz).filter_by(post_parent=course.id).order_by(Quiz.menu_order, Quiz.id):
        qrow = {'id': quiz.id, 'data': fields(quiz, QUIZ_COPY_FIELDS), 'questions': []}
        for q in db.query(QuizQuestion).filter_by(quiz_id=quiz.id).order_by(QuizQuestion.question_order):
            qrow['questions'].append({'id': q.question_id, 'data': fields(q, QUESTION_COPY_FIELDS + ('is_retired',)), 'answers': [fields(a, ANSWER_COPY_FIELDS) for a in q.answers]})
        data['quizzes'].append(qrow)
    data['assignments'] = [{'id': a.id, 'data': fields(a, ASSIGNMENT_COPY_FIELDS + ('rubric', 'order'))} for a in db.query(Assignment).filter_by(course_id=course.id)]
    data['concepts'] = [{'kind': r.kind, 'ref_id': r.ref_id, 'concept': r.concept} for r in db.query(ConceptLink).filter(ConceptLink.course_id == course.id, ConceptLink.kind.in_(['lesson','quiz','question','assignment']))]
    outcome = db.query(CourseOutcome).filter_by(course_id=course.id).first()
    if outcome: data['outcome'] = fields(outcome, ('target_concepts', 'outcome_text'))
    settings = db.query(CourseStudioSettings).filter_by(course_id=course.id).first()
    if settings: data['settings'] = fields(settings, ('parent_view','rewards'))
    from app.models.assessment_studio import StudioQuestion
    from app.services.assessment_studio_service import question_dict
    data['assessment_drafts'] = [{k: v for k, v in question_dict(db, row).items() if k in ('title','type','options','answer','explanation','difficulty','concept','purpose')} for row in db.query(StudioQuestion).filter_by(course_id=course.id)]
    warnings = ['Learner accounts, enrollments, submissions, grades, payment records and live-class attendance are excluded.']
    uploads = Path(get_settings().UPLOAD_DIR).resolve()
    assets = []
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        collect_dependencies(db, data, archive, assets, warnings)
        text_data = json.dumps(data, ensure_ascii=False)
        # Include local upload references only; never fetch a user-provided remote URL.
        for url in sorted(set(re.findall(r'/uploads/[A-Za-z0-9_./% -]+', text_data))):
            from urllib.parse import unquote
            relative = unquote(url.removeprefix('/uploads/')).rstrip(' ')
            try: source = safe_path(uploads, relative)
            except ValueError: warnings.append('Unsafe local asset reference omitted.'); continue
            if source.is_file() and source.suffix.lower() in FILE_EXTENSIONS:
                add_asset(archive, assets, source, url)
            else: warnings.append(f'Local asset unavailable or unsupported: {relative[:120]}')
        if re.search(r'https?://', text_data): warnings.append('External video, CDN and embed URLs remain references; they require the original provider and access configuration.')
        if '/recordings/' in text_data: warnings.append('Recording chapter links refer to original class reports; recording history is not included in this content-only backup.')
        payload = json.dumps(data, ensure_ascii=False).encode()
        if len(payload) > MAX_MANIFEST: raise ValueError('Course manifest exceeds the supported size.')
        archive.writestr('course.json', payload)
        manifest = {'format': FORMAT, 'version': VERSION, 'created_at': utcnow().isoformat(), 'course_sha256': hashlib.sha256(payload).hexdigest(), 'assets': assets, 'warnings': warnings}
        archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False))
    if destination.stat().st_size > MAX_UPLOAD: raise ValueError('Backup exceeds the 200 MB upload limit. Move large media to a CDN or split the course.')
    return manifest


def add_asset(archive, assets, source, original):
    if source.stat().st_size > MAX_UPLOAD or sum(a['size'] for a in assets) + source.stat().st_size > MAX_EXPANDED: raise ValueError('Course assets exceed the backup size limit.')
    name = f'assets/{uuid.uuid4().hex}{source.suffix.lower()}'
    digest = hashlib.sha256()
    with source.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''): digest.update(chunk)
    archive.write(source, name)
    assets.append({'path': name, 'original': original, 'sha256': digest.hexdigest(), 'size': source.stat().st_size})
    return name


def collect_dependencies(db, data, archive, assets, warnings):
    from app.models.game import Game
    from app.models.geogebra import GeoGebraApplet
    from app.models.three_d import ThreeDModel
    from app.models.h5p import H5PContent
    configs = {'games': (Game, ('title','template','config')), 'geogebra': (GeoGebraApplet, ('title','app_type','material_id','ggb_base64','config')), 'models': (ThreeDModel, ('title',)), 'h5p': (H5PContent, ('title',))}
    from app.models.content_library import VirtualLabCatalog
    from app.models.three_d_task import ThreeDTask
    configs['labs'] = (VirtualLabCatalog, ('slug','title','subject','description','provider','native_template','config','embed_url','attribution'))
    configs['three_d_tasks'] = (ThreeDTask, ('title','model_id','task_type','config','concepts','tier_floor'))
    refs = {kind: set() for kind in configs}
    for row in data['lessons']:
        slug = row['data'].get('virtual_lab_sim')
        if slug:
            entry = db.query(VirtualLabCatalog).filter_by(slug=slug).first()
            if entry: refs['labs'].add(entry.id)
        for field, kind in DEPENDENCIES.items():
            if row['data'].get(field): refs[kind].add(row['data'][field])
    for quiz in data['quizzes']:
        for module in quiz['data'].get('interactive_modules') or []:
            kind = {'game':'games','h5p':'h5p','three_d_task':'three_d_tasks'}.get(module.get('kind'))
            if kind: refs[kind].add(module['id'])
            if module.get('kind') == 'lab':
                entry = db.query(VirtualLabCatalog).filter_by(slug=module.get('id')).first()
                if entry: refs['labs'].add(entry.id)
    for task_id in refs['three_d_tasks']:
        task = db.get(ThreeDTask, task_id)
        if task is None: raise ValueError(f'Missing 3D task {task_id}; repair this course before export.')
        refs['models'].add(task.model_id)
    for lab_id in refs['labs']:
        lab = db.get(VirtualLabCatalog, lab_id)
        if lab and lab.native_template == 'concept_lab' and (lab.config or {}).get('model_id'):
            refs['models'].add(lab.config['model_id'])
    for kind, ids in refs.items():
        data['dependencies'][kind] = []
        model, cols = configs[kind]
        for ident in sorted(ids):
            row = db.get(model, ident)
            if row is None: raise ValueError(f'Missing {kind} dependency {ident}; repair this course before export.')
            item = {'id': ident, 'data': fields(row, cols)}
            if kind == 'models':
                base = model_root()
                source = safe_path(base, row.file_path.replace('\\', '/'))
                if not source.is_file(): raise ValueError('A 3D model file is missing.')
                item['asset'] = add_asset(archive, assets, source, f'model:{ident}')
            elif kind == 'h5p':
                folder = safe_path(Path(get_settings().UPLOAD_DIR).resolve() / 'h5p', row.public_id)
                if not (folder / 'h5p.json').is_file(): raise ValueError('An H5P package is missing.')
                temp = root() / f'{uuid.uuid4().hex}.h5p'; temp.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED) as package:
                        for path in folder.rglob('*'):
                            if path.is_symlink(): raise ValueError('H5P contains an unsupported symlink.')
                            if path.is_file(): package.write(path, path.relative_to(folder).as_posix())
                    item['asset'] = add_asset(archive, assets, temp, f'h5p:{ident}')
                finally: temp.unlink(missing_ok=True)
            data['dependencies'][kind].append(item)


def valid_media_header(extension, header):
    return {'.mp4': header[4:8] == b'ftyp', '.webm': header[:4] == bytes.fromhex('1a45dfa3'), '.wav': header[:4] == b'RIFF' and header[8:12] == b'WAVE', '.mp3': header[:3] == b'ID3' or len(header) > 1 and header[0] == 255 and header[1] & 224 == 224}.get(extension, False)


def document_text(path, filename):
    ext = Path(filename).suffix.lower()
    if ext in ('.txt', '.md'): return path.read_text(encoding='utf-8-sig')
    if ext == '.pdf':
        from PyPDF2 import PdfReader
        pdf = PdfReader(path)
        if pdf.is_encrypted: raise ValueError('Unlock encrypted PDFs before uploading.')
        if len(pdf.pages) > 500: raise ValueError('PDF exceeds 500 pages.')
        return '\n\n'.join(page.extract_text() or '' for page in pdf.pages)
    if ext == '.docx':
        from xml.etree import ElementTree
        with zipfile.ZipFile(path) as z:
            entry = z.getinfo('word/document.xml')
            if entry.file_size > 5*1024*1024: raise ValueError('The Word document is too large.')
            xml = z.read(entry)
            if b'<!DOCTYPE' in xml or b'<!ENTITY' in xml: raise ValueError('Unsupported Word XML declarations.')
            tree = ElementTree.fromstring(xml)
        ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        return '\n'.join(''.join(t.text or '' for t in p.iter(ns+'t')) for p in tree.iter(ns+'p'))
    raise ValueError('Use PDF, DOCX, TXT, MD or a Sasha course backup ZIP.')


def preview_data(data):
    from app.services.course_asset_service import classify
    categories = {}
    for row in data.get('lessons', []):
        attrs = row['data']
        kind = attrs.get('lesson_content_type', 'text')
        category = {'h5p':'H5P', 'game':'Game', 'geogebra':'GeoGebra', 'three_d':'3D model', 'virtual_lab':'Virtual lab'}.get(kind) or classify(attrs.get('lesson_video_url') or attrs.get('lesson_attachment_url') or '')
        if category == 'Resource': category = 'Video' if kind == 'video' else 'Text'
        categories[category] = categories.get(category, 0) + 1
    return {'categories': categories, 'assets': data.get('import_assets', []), 'title': data['course']['post_title'], 'lessons': len(data.get('lessons', [])), 'quizzes': len(data.get('quizzes', [])), 'assignments': len(data.get('assignments', [])), 'assessment_drafts': len(data.get('assessment_drafts', [])), 'dependencies': {k: len(v) for k, v in data.get('dependencies', {}).items()}, 'lesson_titles': [r['data']['post_title'] for r in data.get('lessons', [])][:100]}


def transfer_out(row):
    return {'id': row.id, 'kind': row.kind, 'filename': row.filename, 'status': row.status, 'course_id': row.course_id, 'expires_at': row.expires_at, 'warnings': row.warnings, 'preview': preview_data(row.manifest['data'])}


def replace_assets(value, mapping):
    if isinstance(value, str):
        for old, new in mapping.items(): value = value.replace(old, new)
        return value
    if isinstance(value, list): return [replace_assets(v, mapping) for v in value]
    if isinstance(value, dict): return {k: replace_assets(v, mapping) for k, v in value.items()}
    return value


def restore(db, transfer, user, title):
    data = copy.deepcopy(transfer.manifest['data'])
    validate_data(data)
    created_paths = []
    mapping = {}
    try:
        if transfer.kind == 'backup':
            path = safe_path(root(), f'{transfer.id}/upload.bin')
            # Verify staged file again; preview metadata alone is never authority for bytes.
            with path.open('rb') as source:
                digest = hashlib.file_digest(source, 'sha256').hexdigest()
            if digest != transfer.sha256: raise ValueError('The staged backup changed after preview.')
            fresh, manifest = inspect_archive(path)
            if fresh != transfer.manifest['data']: raise ValueError('The staged backup changed after preview.')
            with zipfile.ZipFile(path) as archive:
                for asset in manifest.get('assets', []):
                    if not asset['original'].startswith('/uploads/'): continue
                    dest = safe_path(Path(get_settings().UPLOAD_DIR).resolve(), f'course-restores/{transfer.id}/{PurePosixPath(asset["path"]).name}')
                    dest.parent.mkdir(parents=True, exist_ok=True); created_paths.append(dest)
                    with archive.open(asset['path']) as source, dest.open('wb') as target: shutil.copyfileobj(source, target)
                    mapping[asset['original']] = '/uploads/' + dest.relative_to(Path(get_settings().UPLOAD_DIR).resolve()).as_posix()
                dependency_map = restore_dependencies(db, data, archive, user, transfer.id, created_paths)
            data = replace_assets(data, mapping)
        else:
            dependency_map = {}
            for media in transfer.manifest.get('package', {}).get('media', []):
                source = safe_path(root(), f'{transfer.id}/{media["file"]}')
                with source.open('rb') as stream:
                    if hashlib.file_digest(stream, 'sha256').hexdigest() != media['sha256']: raise ValueError('An uploaded media file changed after preview.')
                if media.get('kind') == '3D model':
                    from app.models.three_d import ThreeDModel
                    relative = f'{user.id}/{uuid.uuid4().hex}.glb'
                    dest = safe_path(model_root(), relative)
                    dest.parent.mkdir(parents=True, exist_ok=True); created_paths.append(dest)
                    shutil.copyfile(source, dest)
                    model = ThreeDModel(owner_id=user.id, title=media['title'], file_path=relative, file_size_bytes=dest.stat().st_size)
                    db.add(model); db.flush()
                    dependency_map['models', media['lesson_id']] = model.id
                    continue
                dest = safe_path(Path(get_settings().UPLOAD_DIR).resolve(), f'course-restores/{transfer.id}/{uuid.uuid4().hex}{media["extension"]}')
                dest.parent.mkdir(parents=True, exist_ok=True); created_paths.append(dest)
                shutil.copyfile(source, dest)
                mapping[media['original']] = '/uploads/' + dest.relative_to(Path(get_settings().UPLOAD_DIR).resolve()).as_posix()
            data = replace_assets(data, mapping)
        attrs = typed(Course, data['course'], COURSE_COPY_FIELDS + ('post_title',))
        attrs['post_title'] = title.strip() if title and title.strip() else attrs['post_title']
        course = Course(**attrs, post_author=user.id, post_status='draft', post_name='course-' + uuid.uuid4().hex[:16])
        db.add(course); db.flush()
        ids = {}
        for row in data.get('lessons', []):
            attrs = typed(Lesson, row['data'], LESSON_COPY_FIELDS)
            for field, kind in DEPENDENCIES.items():
                old = attrs.get(field)
                if old:
                    if (kind, old) not in dependency_map: raise ValueError(f'Missing {kind} dependency in this backup.')
                    attrs[field] = dependency_map[kind, old]
            lab_slug = attrs.get('virtual_lab_sim')
            if lab_slug:
                attrs['virtual_lab_sim'] = dependency_map.get(('lab_slug', lab_slug), lab_slug)
                if ('lab_slug', lab_slug) not in dependency_map:
                    from app.services.lab_catalog_service import canonical_lab_slug
                    attrs['virtual_lab_sim'] = canonical_lab_slug(lab_slug)
                    from app.routers.virtual_labs import is_valid_lab_slug
                    if not is_valid_lab_slug(db, lab_slug): raise ValueError('This lab is missing from the destination catalog.')
            attrs['post_status'] = 'draft'; attrs['lesson_preview'] = False
            lesson = Lesson(**attrs, post_author=user.id, post_parent=course.id)
            db.add(lesson); db.flush(); ids[f'lesson-{row["id"]}'] = f'lesson-{lesson.id}'
        practice_lesson_ids = []
        for row in data.get('quizzes', []):
            attrs = typed(Quiz, row['data'], QUIZ_COPY_FIELDS); attrs['post_status'] = 'draft'
            restored_modules = []
            for mod in attrs.get('interactive_modules') or []:
                if mod.get('kind') == 'lab':
                    from app.services.lab_catalog_service import canonical_lab_slug
                    from app.routers.virtual_labs import catalog
                    old_slug = mod['id']
                    mod['id'] = dependency_map.get(('lab_slug', old_slug), canonical_lab_slug(old_slug))
                    lab = catalog(db, include_unpublished=True).get(mod['id'])
                    if lab is None: raise ValueError('A quiz lab is missing from this backup or the supplied catalog.')
                    if lab['provider'] != 'native':
                        # Supplied simulations have no gradeable result. Preserve
                        # the investigation as a new draft lesson, never invent marks.
                        investigation = Lesson(post_author=user.id, post_parent=course.id, post_title='Investigation: ' + lab['title'],
                            post_status='draft', post_type='lesson', lesson_content_type='virtual_lab',
                            virtual_lab_sim=lab['slug'], lesson_preview=False, menu_order=len(data.get('lessons', [])) + len(practice_lesson_ids))
                        db.add(investigation); db.flush(); practice_lesson_ids.append(f'lesson-{investigation.id}')
                        transfer.warnings = list(transfer.warnings or []) + [f"Quiz lab {old_slug} restored as a lesson investigation ({lab['slug']}); review quiz grading before publication."]
                        continue
                    restored_modules.append(mod)
                    continue
                kind = {'game':'games','h5p':'h5p','three_d_task':'three_d_tasks'}.get(mod.get('kind'))
                if (kind, mod['id']) not in dependency_map: raise ValueError('Missing quiz interactive dependency.')
                mod['id'] = dependency_map[kind, mod['id']]
                restored_modules.append(mod)
            attrs['interactive_modules'] = restored_modules
            quiz = Quiz(**attrs, post_author=user.id, post_parent=course.id); db.add(quiz); db.flush(); ids[f'quiz-{row["id"]}'] = f'quiz-{quiz.id}'
            for q in row.get('questions', []):
                question = QuizQuestion(**typed(QuizQuestion, q['data'], QUESTION_COPY_FIELDS + ('is_retired',)), quiz_id=quiz.id)
                db.add(question); db.flush(); ids[f'question-{q["id"]}'] = f'question-{question.question_id}'
                for a in q.get('answers', []): db.add(QuizQuestionAnswer(**typed(QuizQuestionAnswer, a, ANSWER_COPY_FIELDS), belongs_question_id=question.question_id))
        for row in data.get('assignments', []):
            assignment = Assignment(**typed(Assignment, row['data'], ASSIGNMENT_COPY_FIELDS + ('rubric','order')), course_id=course.id, created_by=user.id, status=AssignmentStatus.DRAFT)
            db.add(assignment); db.flush(); ids[f'assignment-{row["id"]}'] = f'assignment-{assignment.id}'
        sections = data.get('sections', [])
        if not isinstance(sections, list): raise ValueError('Invalid course sections.')
        for section in sections:
            section['lectureIds'] = [ids[k] for item in section.get('lectureIds', []) if (k := str(item) if str(item).startswith(('lesson-','quiz-','assignment-')) else f'lesson-{item}') in ids]
        if practice_lesson_ids:
            sections.append({'id': 'restored-investigations', 'title': 'Restored lab investigations', 'lectureIds': practice_lesson_ids})
        course.course_sections_meta = json.dumps(sections)
        for link in data.get('concepts', []):
            key = f'{link["kind"]}-{link["ref_id"]}'
            if key in ids:
                concept = str(link['concept']).strip().lower()[:80]
                if concept: db.add(ConceptLink(kind=link['kind'], ref_id=ids[key].split('-')[-1], concept=concept, course_id=course.id, created_by=user.id))
        if data.get('outcome'): db.add(CourseOutcome(course_id=course.id, **typed(CourseOutcome, data['outcome'], ('target_concepts','outcome_text'))))
        if data.get('settings'): db.add(CourseStudioSettings(course_id=course.id, updated_by=user.id, **typed(CourseStudioSettings, data['settings'], ('parent_view','rewards'))))
        from app.services.assessment_studio_service import save_draft
        for question in data.get('assessment_drafts', []):
            content = {k: question[k] for k in ('title','type','options','answer','explanation','difficulty')}
            save_draft(db, course.id, user.id, content, question['concept'], question['purpose'], allow_incomplete=True)
        transfer.course_id, transfer.status = course.id, 'restored'
        db.commit()
        return course
    except Exception:
        db.rollback()
        for path in reversed(created_paths):
            if path.is_file(): path.unlink(missing_ok=True)
            elif path.is_dir(): shutil.rmtree(path)
        raise


def restore_dependencies(db, data, archive, user, transfer_id, created_paths):
    from app.models.game import Game
    from app.models.geogebra import GeoGebraApplet
    from app.models.three_d import ThreeDModel
    from app.models.h5p import H5PContent
    from app.models.three_d_task import ThreeDTask
    from app.schemas.game_config import validate_game_config
    from app.services.h5p_service import validate_and_extract, generate_public_id
    mapping = {}
    expanded_h5p = 0
    from sqlalchemy import func
    owner_h5p = db.query(func.coalesce(func.sum(H5PContent.size_bytes), 0)).filter(H5PContent.owner_id == user.id).scalar()
    for kind, rows in sorted(data.get('dependencies', {}).items(), key=lambda item: item[0] != 'models'):
        if kind not in ('games','geogebra','models','h5p','labs','three_d_tasks') or not isinstance(rows, list) or len(rows)>5000: raise ValueError('Unsupported interactive dependency.')
        for item in rows:
            if kind == 'three_d_tasks':
                from app.schemas.three_d_task_config import validate_task_config
                attrs = typed(ThreeDTask, item['data'], ('title','model_id','task_type','config','concepts','tier_floor'))
                if ('models', attrs['model_id']) not in mapping: raise ValueError('3D task model is missing from this backup.')
                attrs['model_id'] = mapping['models', attrs['model_id']]
                attrs['config'] = validate_task_config(attrs['task_type'], attrs['config'])
                if attrs.get('tier_floor') not in ('T0','T1','T2','T3','T4','T5','T6','T7'): raise ValueError('Invalid 3D task tier.')
                obj = ThreeDTask(**attrs, owner_id=user.id, status='draft')
            elif kind == 'labs':
                from app.models.content_library import VirtualLabCatalog
                from app.schemas.lab_config import LabCatalogEntryIn
                attrs = LabCatalogEntryIn(**item['data'], is_published=False).normalized()
                attached = (attrs.get('config') or {}).get('model_id')
                if attrs.get('native_template') == 'concept_lab' and attached:
                    if ('models', attached) not in mapping:
                        raise ValueError('Lab backup is missing its attached 3D model.')
                    attrs['config']['model_id'] = mapping['models', attached]
                old_slug = attrs['slug']; attrs['slug'] = 'restored-' + uuid.uuid4().hex
                obj = VirtualLabCatalog(**attrs, created_by=user.id)
                mapping['lab_slug', old_slug] = obj.slug
            elif kind == 'games':
                attrs = typed(Game, item['data'], ('title','template','config')); attrs['config'] = validate_game_config(attrs['template'], attrs['config'])
                obj = Game(**attrs, owner_id=user.id, status='draft')
            elif kind == 'geogebra':
                attrs = typed(GeoGebraApplet, item['data'], ('title','app_type','material_id','ggb_base64','config'))
                from app.models.geogebra import GEOGEBRA_APP_TYPES
                if attrs['app_type'] not in GEOGEBRA_APP_TYPES: raise ValueError('Unknown GeoGebra app.')
                obj = GeoGebraApplet(**attrs, owner_id=user.id)
            else:
                asset = item['asset']; safe_path(root(), asset)
                if not asset.startswith('assets/'): raise ValueError('Invalid interactive asset path.')
                if kind == 'models':
                    base = model_root(); relative = f'{user.id}/{uuid.uuid4().hex}.glb'
                    dest = safe_path(base, relative); dest.parent.mkdir(parents=True, exist_ok=True); created_paths.append(dest)
                    with archive.open(asset) as source, dest.open('wb') as target:
                        if source.read(4) != b'glTF': raise ValueError('Invalid 3D model file.')
                        target.write(b'glTF'); shutil.copyfileobj(source, target)
                    if dest.stat().st_size > 50*1024*1024: raise ValueError('3D models are limited to 50 MB.')
                    obj = ThreeDModel(**typed(ThreeDModel, item['data'], ('title',)), owner_id=user.id, file_path=relative, file_size_bytes=dest.stat().st_size)
                else:
                    public_id = generate_public_id(); dest = safe_path(Path(get_settings().UPLOAD_DIR).resolve() / 'h5p', public_id); created_paths.append(dest)
                    temp = safe_path(root(), f'{transfer_id}/{public_id}.h5p')
                    try:
                        with archive.open(asset) as source, temp.open('wb') as target: shutil.copyfileobj(source, target)
                        result = validate_and_extract(temp, dest)
                        expanded_h5p += result.size_bytes
                        if expanded_h5p > MAX_EXPANDED or owner_h5p + expanded_h5p > 2 * 1024**3: raise ValueError('Restored H5P content exceeds the storage limit.')
                    finally: temp.unlink(missing_ok=True)
                    obj = H5PContent(**typed(H5PContent, item['data'], ('title',)), owner_id=user.id, public_id=public_id, status='ready', library=result.library, size_bytes=result.size_bytes)
            db.add(obj); db.flush(); mapping[kind, item['id']] = obj.id
    return mapping


def cleanup_expired(db, limit=100):
    """Reclaim private upload bytes only after their restore window closes.

    The row lock/CAS prevents deleting files while another request restores.
    UUID validation and safe_path keep cleanup inside this service's staging root.
    """
    from app.models.operations import CourseTransfer
    rows = db.query(CourseTransfer).filter(
        CourseTransfer.expires_at < utcnow(),
        CourseTransfer.staging_cleaned_at.is_(None),
        CourseTransfer.status.in_(['preview', 'restored', 'discarded', 'expired']),
    ).order_by(CourseTransfer.expires_at).limit(limit).with_for_update(skip_locked=True).all()
    removed = 0
    for row in rows:
        if str(uuid.UUID(row.id)) != row.id: continue
        previous = row.status
        changed = db.query(CourseTransfer).filter_by(id=row.id, status=previous).update(
            {'status': 'expired' if previous == 'preview' else previous}, synchronize_session=False)
        if not changed: continue
        folder = safe_path(root(), row.id)
        if folder.is_dir():
            shutil.rmtree(folder)
            removed += 1
        row.staging_cleaned_at = utcnow()
        # Keep the lightweight audit/preview row and idempotent restored course link.
    db.commit()
    # Account deletion can cascade transfer rows; reclaim their old private files too.
    if root().is_dir():
        cutoff = (utcnow() - timedelta(hours=24)).timestamp()
        for candidate in root().iterdir():
            if removed >= limit: break
            if not candidate.is_dir(): continue
            try:
                if str(uuid.UUID(candidate.name)) != candidate.name: continue
                folder = safe_path(root(), candidate.name)
            except ValueError:
                continue
            if folder.stat().st_mtime >= cutoff: continue
            if any(p.stat().st_mtime >= cutoff for p in folder.iterdir()): continue
            if db.get(CourseTransfer, candidate.name) is not None: continue
            shutil.rmtree(folder)
            removed += 1
    return removed
