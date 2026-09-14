#!/bin/bash
B="${SMOKE_BASE:-http://127.0.0.1:8010/api/v1}"
T="$1"; S="$2"
pass=0; fail=0
chk() { # name, expected, actual
  if [ "$2" = "$3" ]; then pass=$((pass+1)); echo "PASS  $1";
  else fail=$((fail+1)); echo "FAIL  $1 (want $2 got $3)"; fi
}
code() { curl -s -m 12 -o /dev/null -w "%{http_code}" "$@"; }

# auth
chk "auth /me" 200 $(code "$B/auth/me" -H "Authorization: Bearer $T")
# dashboard (student)
chk "student dashboard" 200 $(code "$B/dashboard/student" -H "Authorization: Bearer $T")
# courses list + tree
chk "courses list" 200 $(code "$B/courses/" -H "Authorization: Bearer $T")
chk "course 5 detail" 200 $(code "$B/courses/5" -H "Authorization: Bearer $T")
# type capabilities
chk "type-capabilities" 200 $(code "$B/courses/type-capabilities")
# ebooks store/detail/claim/me
chk "ebook store" 200 $(code "$B/library")
chk "ebook detail" 200 $(code "$B/library/class-10-physics-formula-sheet-2" -H "Authorization: Bearer $T")
chk "my library" 200 $(code "$B/library/me" -H "Authorization: Bearer $T")
chk "ebook download" 200 $(code "$B/library/2/download" -H "Authorization: Bearer $T")
# 3D
chk "3d list" 200 $(code "$B/three-d/models" -H "Authorization: Bearer $S")
chk "3d stream duck" 200 $(code "$B/three-d/models/3/file" -H "Authorization: Bearer $T")
# labs
chk "labs catalog" 200 $(code "$B/virtual-labs")
# geogebra
chk "geogebra applets" 200 $(code "$B/geogebra/applets" -H "Authorization: Bearer $S")
# question banks + analysis
chk "banks list" 200 $(code "$B/question-banks" -H "Authorization: Bearer $S")
chk "bank 1 analysis" 200 $(code "$B/question-banks/1/analysis" -H "Authorization: Bearer $S")
# quizzes
chk "quiz 1 fetch" 200 $(code "$B/courses/5/quizzes/1" -H "Authorization: Bearer $S")
# analytics
chk "mastery" 200 $(code "$B/analytics/students/3/mastery" -H "Authorization: Bearer $T")
chk "cumulative" 200 $(code "$B/analytics/courses/5/students/3/cumulative-grade" -H "Authorization: Bearer $T")
chk "at-risk (instructor)" 200 $(code "$B/analytics/courses/5/at-risk" -H "Authorization: Bearer $S")
# unlock status
chk "unlock-status" 200 $(code "$B/courses/2/unlock-status" -H "Authorization: Bearer $T")
# learning paths
chk "learning-paths list" 200 $(code "$B/learning-paths" -H "Authorization: Bearer $S")
# live classes
chk "past-classes" 200 $(code "$B/live/past-classes-report" -H "Authorization: Bearer $S")
# marketplace
chk "games marketplace" 200 $(code "$B/games/marketplace" -H "Authorization: Bearer $S")
# xapi
chk "xapi me" 200 $(code "$B/xapi/me/statements" -H "Authorization: Bearer $T")
# AI honest 503s
chk "AI tutor 503" 503 $(code -X POST "$B/ai/tutor/chat" -H "Authorization: Bearer $T" -H "Content-Type: application/json" -d '{"message":"hi"}')
chk "AI exam 503" 503 $(code -X POST "$B/ai/generate-exam-paper" -H "Authorization: Bearer $S" -H "Content-Type: application/json" -d '{"exam":"JEE","count":5}')
chk "AI questions 503" 503 $(code -X POST "$B/ai/generate-questions" -H "Authorization: Bearer $S" -H "Content-Type: application/json" -d '{"topic":"x","count":2}')
echo "-----"
echo "PASS=$pass FAIL=$fail"
