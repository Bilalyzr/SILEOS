"""Deterministic pilot, not a validated diagnosis or an AI efficacy claim.

All mutations use optimistic SQL compare-and-swap as well as row locks. The
immutable catalog hash pins both scoring and educator review. No LLM is needed.
"""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from fastapi import HTTPException
from sqlalchemy import or_
from app.models.course import Course
from app.models.math_pilot import MathPilotPolicy, MathPilotSession, MathPilotEvent
from app.models.mastery import MasteryEvidence
from app.services.course_access import can_edit, collaborated_course_ids, ADMIN_ROLES
from app.services.learning_planner_service import enrolled

CATALOG = {
    'topic': 'Volume through unit cubes', 'revision': 1,
    'concept': 'volume of rectangular prisms',
    'prerequisites': ['counting equal groups', 'multiplication', 'area of rectangles'],
    'misconceptions': {
        'layers': 'May be counting one layer rather than all layers.',
        'multiplication': 'May need support counting equal groups.',
        'uncertain': 'Evidence is mixed; check wording, interface and reasoning with the learner.',
        'no_gap_observed': 'No gap observed on these two diagnostic items; this is not a mastery verdict.'},
    'interventions': {
        'layers': 'One layer has length × width unit cubes. Stack equal layers: total cubes = cubes per layer × number of layers.',
        'multiplication': 'Count a row, then equal rows in a layer. For a 3 by 2 base, 3 + 3 = 6. Repeat the whole layer for each unit of height.',
        'language': 'Length counts cubes along a row. Width counts rows in one layer. Height counts stacked layers. Volume counts ALL unit cubes, not the outline.'},
    'predict': {'prompt': 'A box is 3 cubes long, 2 wide and 2 high. Only its height doubles. What happens to its volume?',
                'options': ['Stays the same', 'Doubles', 'Increases by 2 cubes', 'Becomes four times as large'], 'key': [1]},
    'diagnose': {'prompt': 'Before an explanation: count a 3 by 2 base, then a box with 4 such layers.',
                 'questions': ['How many cubes are in one layer?', 'How many cubes are in all 4 layers?'], 'key': [6, 24]},
    'build': {'prompt': 'Build a box with a 3 by 2 base and 4 layers. Then enter its total number of unit cubes.', 'key': [4, 24]},
    'transfer': {'prompt': 'New problems. Work independently without the cube helper.',
                 'questions': ['A crate is 4 cubes long, 3 wide and 2 high. How many unit cubes fill it?',
                               'A different crate has 5 cubes in each layer and 3 layers. How many cubes fill it?'], 'key': [24, 15]},
    'retention': {'prompt': 'Delayed check. Work independently; no helper or hints.',
                  'questions': ['A box is 2 cubes long, 5 wide and 3 high. How many unit cubes fill it?',
                                'A box has 6 cubes per layer and 4 layers. Only its height doubles. How many cubes now?'], 'key': [30, 48]},
}
VERSION = sha256(json.dumps(CATALOG, sort_keys=True).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc)


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def catalog():
    return {**{k: v for k, v in CATALOG.items() if k not in ('predict', 'diagnose', 'build', 'transfer', 'retention')},
            'version': VERSION, 'review_required': True, 'retention_days': 90,
            'notice': 'Formative pilot. Two correct answers do not prove permanent mastery. No public student results.'}


def editor(db, course_id, user):
    course = db.get(Course, course_id)
    if not can_edit(db, course, user):
        raise HTTPException(403, 'Only this course owner, collaborator or administrator may review this pilot.')
    return course


def active_policy(db, course_id):
    return db.query(MathPilotPolicy).filter_by(course_id=course_id, version=VERSION).first()


def own(db, session_id, user):
    row = db.query(MathPilotSession).filter_by(id=session_id, user_id=user.id).with_for_update().first()
    if not row:
        raise HTTPException(404, 'Activity not found.')
    return row


def available(db, row):
    if row.version != VERSION or not active_policy(db, row.course_id):
        raise HTTPException(409, 'This activity version is paused or needs educator review.')
    if aware(row.expires_at) <= now():
        raise HTTPException(410, 'Pilot data expired. Delete this record before starting again.')
    if not enrolled(db, row.user_id, row.course_id):
        raise HTTPException(403, 'Active course enrollment is required.')


def view(row):
    stage = row.stage
    if stage == 'waiting' and aware(row.due_at) <= now():
        stage = 'retention'
    task = CATALOG.get(stage, {})
    return {'id': row.id, 'course_id': row.course_id, 'version': row.version,
            'stage': stage, 'sequence': row.sequence, 'due_at': aware(row.due_at) if row.due_at else None,
            'expires_at': aware(row.expires_at), 'hypothesis': row.hypothesis,
            'hypothesis_note': CATALOG['misconceptions'].get(row.hypothesis),
            'intervention': row.intervention,
            'explanation': CATALOG['interventions'].get(row.intervention) if stage == 'build' else None,
            'transfer_score': row.transfer_score, 'retention_score': row.retention_score,
            'task': {k: v for k, v in task.items() if k != 'key'},
            'notice': catalog()['notice']}


def start(db, course_id, user):
    if user.role != 'student' or not enrolled(db, user.id, course_id):
        raise HTTPException(403, 'Only an enrolled student can record a pilot attempt.')
    if not active_policy(db, course_id):
        raise HTTPException(409, 'An educator must review this task version and school data arrangements first.')
    row = db.query(MathPilotSession).filter_by(course_id=course_id, user_id=user.id, version=VERSION).first()
    if row:
        available(db, row)
        return view(row)
    row = MathPilotSession(course_id=course_id, user_id=user.id, version=VERSION,
                           stage='predict', sequence=0, created_at=now(), expires_at=now()+timedelta(days=90))
    db.add(row)
    db.commit()
    return view(row)


def evidence(db, row, stage, score):
    # Same transaction as the scored event. No evidence for clicks or helped practice.
    from app.services.mastery_service import _recompute
    db.add(MasteryEvidence(user_id=row.user_id, course_id=row.course_id,
                          concept=CATALOG['concept'], source_kind='math_pilot',
                          source_ref=f'{row.id}:{stage}', score_pct=score*50, weight=0.5,
                          detail={'version': VERSION, 'stage': stage, 'items': 2,
                                  'interpretation': 'Limited formative evidence, not calibrated mastery.'}))
    db.flush()
    _recompute(db, row.user_id, CATALOG['concept'])


def reserve(db, row, sequence):
    changed = db.query(MathPilotSession).filter_by(id=row.id, sequence=sequence).update(
        {'sequence': sequence+1}, synchronize_session=False)
    if changed != 1:
        raise HTTPException(409, 'Activity changed in another tab. Reload before continuing.')
    db.refresh(row)


def submit(db, row, body, user):
    payload = body.model_dump(mode='json')
    old = db.query(MathPilotEvent).filter_by(session_id=row.id, key=str(body.key)).first()
    if old:
        if old.payload != payload or old.actor_id != user.id:
            raise HTTPException(409, 'This request key was already used for different evidence.')
        return {**view(row), 'feedback': old.result.get('feedback')}
    available(db, row)
    stage = view(row)['stage']
    if body.version != row.version or body.stage != stage or stage not in ('predict', 'diagnose', 'build', 'transfer', 'retention'):
        raise HTTPException(409, 'This step is not available. Refresh the activity.')
    if len(body.answers) != len(CATALOG[stage]['key']):
        raise HTTPException(422, 'Answer every item in this step.')
    if stage == 'predict' and body.answers[0] not in range(4):
        raise HTTPException(422, 'Choose one of the four predictions.')
    if row.sequence >= 100:
        raise HTTPException(409, 'This pilot has reached its 100-step safety limit. Export your evidence and ask your teacher for support.')
    reserve(db, row, body.sequence)
    correct = sum(a == b for a, b in zip(body.answers, CATALOG[stage]['key']))
    feedback = None
    if stage == 'predict':
        row.stage = 'diagnose'
    elif stage == 'diagnose':
        a, b = body.answers
        row.hypothesis = 'no_gap_observed' if correct == 2 else 'layers' if a == 6 and b == 6 else 'multiplication' if a != 6 else 'uncertain'
        row.intervention = {'layers': 'layers', 'multiplication': 'multiplication'}.get(row.hypothesis, 'language')
        row.stage = 'build'
    elif stage == 'build':
        if correct == 2:
            row.stage = 'transfer'
        else:
            feedback = 'Count six cubes in each layer. Check both the number of layers and the total, then try again.'
    elif stage == 'transfer':
        row.transfer_score = correct
        row.due_at = now()+timedelta(days=3)
        row.stage = 'waiting'
        evidence(db, row, stage, correct)
    else:
        row.retention_score = correct
        row.stage = 'complete'
        evidence(db, row, stage, correct)
    db.add(MathPilotEvent(session_id=row.id, sequence=row.sequence, key=str(body.key), actor_id=user.id,
                          action=stage, payload=payload, result={'score': correct, 'feedback': feedback}, created_at=now()))
    db.commit()
    return {**view(row), 'feedback': feedback}


def erase(db, row):
    from app.services.mastery_service import _recompute
    from app.models.mastery import LearnerMastery
    from app.models.notification import Notification
    db.query(Notification).filter_by(user_id=row.user_id, type='math_retention_due', related_id=row.id).delete()
    db.query(MasteryEvidence).filter(MasteryEvidence.user_id == row.user_id,
        MasteryEvidence.source_kind == 'math_pilot',
        MasteryEvidence.source_ref.in_([f'{row.id}:transfer', f'{row.id}:retention'])).delete(synchronize_session=False)
    db.query(MathPilotEvent).filter_by(session_id=row.id).delete()
    uid = row.user_id
    db.delete(row)
    db.flush()
    if db.query(MasteryEvidence.id).filter_by(user_id=uid, concept=CATALOG['concept']).first():
        _recompute(db, uid, CATALOG['concept'])
    else:
        db.query(LearnerMastery).filter_by(user_id=uid, concept=CATALOG['concept']).delete()


def cleanup(db):
    rows = db.query(MathPilotSession).filter(MathPilotSession.expires_at <= now()).order_by(MathPilotSession.id).limit(500).with_for_update().all()
    for row in rows:
        erase(db, row)
    db.commit()
    return len(rows)


def maintenance(db):
    """Bounded private reminders, respecting the existing learning topic opt-out."""
    from app.models.notification import Notification
    from app.models.communication_automation import CommunicationTopicPreference
    removed = cleanup(db)
    rows = db.query(MathPilotSession).filter(
        MathPilotSession.stage == 'waiting', MathPilotSession.due_at <= now(),
        MathPilotSession.expires_at > now(),
        ~db.query(MathPilotEvent.id).filter(MathPilotEvent.session_id == MathPilotSession.id,
            MathPilotEvent.key == 'retention-reminder').exists()).order_by(MathPilotSession.id).limit(200).with_for_update().all()
    sent = 0
    for row in rows:
        if not enrolled(db, row.user_id, row.course_id) or not active_policy(db, row.course_id):
            continue
        preference = db.query(CommunicationTopicPreference).filter_by(user_id=row.user_id, topic='learning_interventions').first()
        if preference is not None and not preference.in_app_enabled:
            continue
        reserve(db, row, row.sequence)
        db.add(Notification(user_id=row.user_id, type='math_retention_due', related_id=row.id,
            title='Your volume check is ready', message='Try the delayed questions independently. Your results stay private.',
            link='/math-pilot', is_read=False))
        db.add(MathPilotEvent(session_id=row.id, sequence=row.sequence, key='retention-reminder',
            actor_id=row.user_id, action='system_reminder', payload={'channel': 'in_app'},
            result={'scheduled': True}, created_at=now()))
        sent += 1
    db.commit()
    return {'expired': removed, 'reminders': sent}


def courses(db, user):
    query = db.query(Course)
    if user.role == 'student':
        from app.models.enrollment import Enrollment
        query = query.join(Enrollment, Enrollment.course_id == Course.id).filter(
            Enrollment.user_id == user.id, Enrollment.enrollment_status.in_(['enrolled', 'completed']))
    elif user.role not in ADMIN_ROLES:
        query = query.filter(or_(Course.post_author == user.id, Course.id.in_(collaborated_course_ids(db, user.id))))
    return [{'id': c.id, 'title': c.post_title, 'approved': bool(active_policy(db, c.id))}
            for c in query.order_by(Course.id.desc()).limit(200).all()]
