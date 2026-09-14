"""Phase 2 wiring: three_d + virtual_lab across models/schemas/formatter."""
import io
import ast

def patch(path, pairs):
    s = io.open(path, encoding='utf-8').read()
    for old, new in pairs:
        assert s.count(old) == 1, f"{path}: x{s.count(old)} :: {old[:60]!r}"
        s = s.replace(old, new, 1)
    io.open(path, 'w', encoding='utf-8', newline='').write(s)
    if path.endswith('.py'):
        ast.parse(s)
    print("patched", path)

patch('app/models/__init__.py', [(
    "from .geogebra import GeoGebraApplet  # noqa: E402,F401",
    "from .geogebra import GeoGebraApplet  # noqa: E402,F401\nfrom .three_d import ThreeDModel  # noqa: E402,F401",
)])

patch('app/models/course.py', [(
    '    geogebra_applet_id = Column(Integer, ForeignKey("geogebra_applets.id"), nullable=True)',
    '    geogebra_applet_id = Column(Integer, ForeignKey("geogebra_applets.id"), nullable=True)\n'
    '    # Phase 2: 3D GLB model (MP/UP courses only) and PhET virtual lab slug.\n'
    '    three_d_model_id = Column(Integer, ForeignKey("three_d_models.id"), nullable=True)\n'
    '    virtual_lab_sim = Column(String(50), nullable=True)',
)])

p = 'app/schemas/course.py'
s = io.open(p, encoding='utf-8').read()
s = s.replace('LESSON_CONTENT_TYPES = {"video", "h5p", "game", "geogebra"}',
              'LESSON_CONTENT_TYPES = {"video", "h5p", "game", "geogebra", "three_d", "virtual_lab"}')
needle = "    geogebra_applet_id: Optional[int] = None\n"
assert s.count(needle) >= 2, f"geo field x{s.count(needle)}"
s = s.replace(needle, needle + "    three_d_model_id: Optional[int] = None\n    virtual_lab_sim: Optional[str] = None\n")
io.open(p, 'w', encoding='utf-8', newline='').write(s)
ast.parse(s)
print("patched", p)

patch('app/core/database.py', [(
    '        "ALTER TABLE lessons ADD COLUMN IF NOT EXISTS geogebra_applet_id INTEGER",',
    '        "ALTER TABLE lessons ADD COLUMN IF NOT EXISTS geogebra_applet_id INTEGER",\n'
    '        "ALTER TABLE lessons ADD COLUMN IF NOT EXISTS three_d_model_id INTEGER",\n'
    '        "ALTER TABLE lessons ADD COLUMN IF NOT EXISTS virtual_lab_sim VARCHAR(50)",',
)])

patch('app/services/course_service.py', [(
    '            "geogebra_applet_id": getattr(lesson, "geogebra_applet_id", None),',
    '            "geogebra_applet_id": getattr(lesson, "geogebra_applet_id", None),\n'
    '            "three_d_model_id": getattr(lesson, "three_d_model_id", None),\n'
    '            "virtual_lab_sim": getattr(lesson, "virtual_lab_sim", None),',
)])
