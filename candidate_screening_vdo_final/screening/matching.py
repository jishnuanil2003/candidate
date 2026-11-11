"""Keyword matching between dmcore fields and the existing interview clips."""
import json
import logging
import re
from difflib import get_close_matches
from pathlib import Path

from .questions import QUESTIONS

logger = logging.getLogger(__name__)
KEYWORDS_PATH = Path(__file__).with_name('question_keywords.json')
FUZZY_CUTOFF = 0.80


def normalize_text(value):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]+', ' ', str(value or '').lower())).strip()


def load_catalog():
    """Read keywords on each match so edits take effect without a restart."""
    with KEYWORDS_PATH.open(encoding='utf-8') as config_file:
        keywords = json.load(config_file)
    questions = {question['id']: question for question in QUESTIONS}
    return {
        question_id: {
            'question_text': re.sub(r'<[^>]+>', '', questions[question_id]['question']),
            'keywords': entry.get('keywords', []) if isinstance(entry, dict) else entry,
            'requires_one_of': entry.get('requires_one_of', []) if isinstance(entry, dict) else [],
        }
        for question_id, entry in keywords.items() if question_id in questions
    }


def _phrase_matches(text, phrase):
    phrase = normalize_text(phrase)
    if not phrase:
        return False
    if re.search(r'\b' + re.escape(phrase) + r'\b', text):
        return True
    words = text.split()
    phrase_words = phrase.split()
    if len(phrase_words) > len(words):
        return False
    for start in range(len(words) - len(phrase_words) + 1):
        if all(word == candidate or (len(word) >= 4 and get_close_matches(word, [candidate], n=1, cutoff=FUZZY_CUTOFF))
               for word, candidate in zip(phrase_words, words[start:start + len(phrase_words)])):
            return True
    return False


def match_fields(fields):
    """Return ordered clip matches and fields that did not safely match."""
    catalog = load_catalog()
    matched_by_id = {}
    unmatched = []
    for field in fields:
        field_name = str(field.get('field_name', '') or '')
        description = str(field.get('description', '') or '')
        normalized = normalize_text(field_name + ' ' + description)
        hits = {}
        for question_id, entry in catalog.items():
            if entry['requires_one_of'] and not any(_phrase_matches(normalized, required) for required in entry['requires_one_of']):
                continue
            matching_keywords = {keyword for keyword in entry['keywords'] if _phrase_matches(normalized, keyword)}
            if matching_keywords:
                hits[question_id] = matching_keywords

        best_guess = None
        if hits:
            highest = max(len(terms) for terms in hits.values())
            leaders = [question_id for question_id, terms in hits.items() if len(terms) == highest]
            best_guess = leaders[0] if len(leaders) == 1 else None
        if not best_guess:
            if hits:
                logger.warning('Ambiguous dmcore field field_name=%r description=%r question_ids=%r', field_name, description, list(hits))
            else:
                logger.warning('Unmatched dmcore field field_name=%r description=%r best_guess=%r', field_name, description, None)
            unmatched.append(field)
            continue

        multi_topic = best_guess == 'expected_salary' and bool(
            re.search(r'\bcurrent (?:salary|ctc)\b', normalized)
            and re.search(r'\b(?:expected|expectation|desired)\b', normalized)
        )
        if multi_topic:
            logger.warning('Mixed current and expected salary field field_name=%r description=%r', field_name, description)
        item = matched_by_id.get(best_guess)
        if item is None:
            item = {'field_names': [], 'question_id': best_guess, 'method': 'keyword', 'multi_topic': False, 'field_options': []}
            matched_by_id[best_guess] = item
        item['field_names'].append(field_name)
        item['field_options'].append({'field_name': field_name, 'multi_topic': multi_topic})
        item['multi_topic'] = item['multi_topic'] or multi_topic

    return list(matched_by_id.values()), unmatched
