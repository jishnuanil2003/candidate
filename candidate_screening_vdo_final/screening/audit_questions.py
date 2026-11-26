import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_local')
django.setup()

from screening.questions import QUESTION_LOOKUP
from screening.translations import QUESTION_HINTS, TRANSLATIONS

print("id | key | field | type | optional | q_hint | global_hint | validator | text")
for qid in sorted(QUESTION_LOOKUP.keys()):
    q = QUESTION_LOOKUP[qid]
    k = q.get('key')
    f = q.get('field')
    t = q.get('type')
    opt = q.get('optional', False)
    qh = q.get('hint', '')
    gh = QUESTION_HINTS.get(qid, '')
    val = q.get('validator')
    val_name = val.__name__ if val else 'validate_answer'
    text = q.get('question', '')
    print(f"{qid} | {k} | {f} | {t} | {opt} | {qh} | {gh} | {val_name} | {text}")
