"""update_quiz: persist interactive_modules on PUT (quiz-builder edit flow)."""
import io
import ast

p = 'app/routers/quizzes.py'
s = io.open(p, encoding='utf-8').read()

# The PUT handler validates modules (lines ~403-441) but the UPDATE block
# never writes quiz.interactive_modules. Find the quiz.* field assignments
# in update_quiz and add the modules write after the last quiz_ assignment.
anchor_candidates = [
    'quiz.feedback_mode = normalize_feedback_mode(',
]
found = False
for a in anchor_candidates:
    if s.count(a) >= 1:
        idx = s.index(a)
        # find end of that statement (the line's end)
        line_end = s.index('\n', idx) + 1
        addition = '''    if "interactive_modules" in quiz_data:
        from app.models.h5p import H5PContent
        from app.models.game import Game
        validated_modules = []
        for m in quiz_data.get("interactive_modules") or []:
            kind = m.get("kind")
            mid = m.get("id")
            if kind not in ("h5p", "game") or not isinstance(mid, int):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="interactive_modules entries need {kind: 'h5p'|'game', id: int}",
                )
            if kind == "h5p":
                row = db.query(H5PContent).filter(H5PContent.id == mid).first()
            else:
                row = db.query(Game).filter(Game.id == mid).first()
            if not row:
                raise HTTPException(status.HTTP_404_NOT_FOUND,
                                    detail=f"{kind} module {mid} not found")
            if row.owner_id != current_user.id and current_user.role != "admin":
                raise HTTPException(status.HTTP_403_FORBIDDEN,
                                    detail=f"not your {kind} module {mid}")
            validated_modules.append({"kind": kind, "id": mid, "title": str(row.title or "")})
        quiz.interactive_modules = validated_modules
'''
        s = s[:line_end] + addition + s[line_end:]
        found = True
        break
assert found, "no anchor in update_quiz"
io.open(p, 'w', encoding='utf-8', newline='').write(s)
ast.parse(s)
print("update_quiz persists interactive_modules")
