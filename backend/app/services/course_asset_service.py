"""Classify standalone course uploads, validate bytes and retain original assets."""
import hashlib
import html
import struct
from pathlib import Path

GROUPS = {'.pdf':'Document', '.docx':'Document', '.txt':'Text', '.md':'Text',
          '.mp4':'Video', '.webm':'Video', '.mp3':'Audio', '.wav':'Audio',
          '.png':'Image', '.jpg':'Image', '.jpeg':'Image', '.webp':'Image', '.gif':'Image', '.glb':'3D model'}


def classify(filename):
    return GROUPS.get(Path(filename).suffix.lower(), 'Resource')


def inspect_files(stored):
    from app.services import course_package_service as package
    data = {'course': {'post_title': Path(stored[0][1]).stem}, 'lessons': [], 'quizzes': [], 'assignments': [], 'sections': [], 'import_assets': []}
    media = []
    for index, (path, name) in enumerate(stored):
        ext = Path(name).suffix.lower()
        if ext not in GROUPS:
            raise ValueError(f'Unsupported course file: {name}. Import H5P and lab packages through their dedicated libraries.')
        category = classify(name)
        reference = f'/uploads/course-import/{index}{ext}'
        attrs = {'post_title': Path(name).stem[:200], 'menu_order': index, 'post_status': 'draft', 'lesson_content_type': 'text', 'lesson_attachment_url': reference}
        with path.open('rb') as stream: header = stream.read(16)
        if category in ('Audio', 'Video'):
            if not package.valid_media_header(ext, header): raise ValueError(f'{name} has an invalid {category.lower()} header.')
            attrs.update(lesson_content_type='video', lesson_video_source='html5', lesson_video_url=reference)
        elif category == 'Image':
            from PIL import Image
            with Image.open(path) as image:
                if image.width * image.height > 40_000_000: raise ValueError('Images must be smaller than 40 megapixels.')
                expected = {'.jpg':'JPEG', '.jpeg':'JPEG', '.png':'PNG', '.webp':'WEBP', '.gif':'GIF'}[ext]
                if image.format != expected: raise ValueError('The image content does not match its file extension.')
                image.verify()
            attrs['post_content'] = f'<p>{html.escape(Path(name).stem)}</p><img src="{reference}" alt="{html.escape(Path(name).stem, quote=True)}">'
        elif category == '3D model':
            if path.stat().st_size > 50 * 1024 * 1024: raise ValueError('3D models are limited to 50 MB.')
            raw = path.read_bytes()
            if len(raw) < 20 or raw[:4] != b'glTF' or struct.unpack_from('<I', raw, 8)[0] != len(raw): raise ValueError('Invalid GLB container length or header.')
            from app.services.glb_budget import check_or_raise, parse_glb_json
            model = parse_glb_json(raw)
            if not isinstance(model, dict) or model.get('asset', {}).get('version') != '2.0':
                raise ValueError('Use a glTF 2.0 model in a GLB container.')
            for entry in model.get('buffers', []) + model.get('images', []):
                if entry.get('uri') and not str(entry['uri']).startswith('data:'):
                    raise ValueError('Embed external model textures and buffers inside the GLB before importing.')
            check_or_raise(raw, name)
            attrs.update(lesson_content_type='three_d', three_d_model_id=index + 1, lesson_attachment_url='')
            data['course']['course_type'] = 'meiporul'
        else:
            if ext == '.pdf' and not header.startswith(b'%PDF-'): raise ValueError('This file is not a PDF.')
            text = package.document_text(path, name).strip()
            if len(text) > 400000 or '\x00' in text: raise ValueError('Use readable documents under 400,000 characters.')
            if not text and ext != '.pdf': raise ValueError(f'No readable text found in {name}.')
            attrs['post_content'] = ''.join('<p>'+html.escape(line)+'</p>' for line in text.splitlines() if line.strip()) or '<p>Open the original PDF in Resources to view the scanned pages.</p>'
        data['lessons'].append({'id': index + 1, 'data': attrs})
        with path.open('rb') as stream: digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        media.append({'file': path.name, 'extension': ext, 'original': reference, 'sha256': digest, 'kind': category, 'lesson_id': index + 1, 'title': attrs['post_title']})
        data['import_assets'].append({'filename': name, 'category': category, 'size': path.stat().st_size})
    return data, {'media': media}, ['Each file becomes one draft lesson. Original documents and images are retained in Resources. Review imported content before publishing; scanned PDFs retain their pages without OCR.']
