"""Server-side dmcore HTTP client. No credentials or tokens reach the browser."""
import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
import re
import socket
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)
TIMEOUT_SECONDS = 10


class DmcoreError(Exception):
    def __init__(self, message, status=None, kind='service'):
        super().__init__(message)
        self.status = status
        self.kind = kind


def validate_configuration():
    """Log missing DMCore settings without ever logging their values."""
    missing = [name for name in ('DMCORE_BASE_URL', 'DMCORE_API_KEY') if not os.environ.get(name, '').strip()]
    if missing:
        logger.error('DMCore configuration missing required .env variable(s): %s', ', '.join(missing))
        return False
    return True


def _request(path, token, payload=None):
    base_url = os.environ.get('DMCORE_BASE_URL', '').strip().rstrip('/')
    api_key = os.environ.get('DMCORE_API_KEY', '').strip()
    missing = [name for name, value in (('DMCORE_BASE_URL', base_url), ('DMCORE_API_KEY', api_key)) if not value]
    if missing:
        logger.error('DMCore request blocked; missing required .env variable(s): %s', ', '.join(missing))
        raise DmcoreError('DMCore configuration is missing: ' + ', '.join(missing), kind='configuration')

    # DMCore authenticates the shared service key with X-API-Key. The separate
    # per-candidate credential belongs in X-Interview-Token.
    headers = {'X-API-Key': api_key, 'X-Interview-Token': token, 'Accept': 'application/json'}
    body = None
    method = 'GET'
    if payload is not None:
        method = 'POST'
        headers['Content-Type'] = 'application/json'
        body = json.dumps(payload).encode('utf-8')
    request = Request(base_url + path, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            status = response.status
            response_body = response.read()
    except HTTPError as error:
        if error.code in (401, 403):
            logger.error('key rejected (HTTP %s)', error.code)
            raise DmcoreError('DMCore rejected the configured API key', error.code, kind='authentication') from error
        logger.error('DMCore returned a non-2xx response (HTTP %s)', error.code)
        raise DmcoreError('DMCore returned HTTP %s' % error.code, error.code, kind='http') from error
    except (socket.timeout, TimeoutError) as error:
        logger.error('DMCore request timed out after %s seconds', TIMEOUT_SECONDS)
        raise DmcoreError('DMCore request timed out', kind='timeout') from error
    except URLError as error:
        reason = error.reason
        if isinstance(reason, (socket.timeout, TimeoutError)):
            logger.error('DMCore request timed out after %s seconds', TIMEOUT_SECONDS)
            raise DmcoreError('DMCore request timed out', kind='timeout') from error
        if isinstance(reason, ConnectionRefusedError):
            logger.error('DMCore connection was refused; confirm DMCore is running and reachable')
            raise DmcoreError('DMCore connection was refused', kind='connection_refused') from error
        logger.error('DMCore is unreachable (%s)', type(reason).__name__)
        raise DmcoreError('DMCore is unreachable', kind='connection') from error
    except ConnectionRefusedError as error:
        logger.error('DMCore connection was refused; confirm DMCore is running and reachable')
        raise DmcoreError('DMCore connection was refused', kind='connection_refused') from error
    except OSError as error:
        logger.error('DMCore is unreachable (%s)', type(error).__name__)
        raise DmcoreError('DMCore is unreachable', kind='connection') from error

    if status < 200 or status >= 300:
        logger.error('DMCore returned a non-2xx response (HTTP %s)', status)
        raise DmcoreError('DMCore returned HTTP %s' % status, status, kind='http')
    try:
        return json.loads(response_body.decode('utf-8')) if response_body else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        logger.error('DMCore returned invalid JSON (HTTP %s)', status)
        raise DmcoreError('DMCore returned invalid JSON', status, kind='invalid_response') from error


def load_session(token):
    return _request('/api/interview/session/', token)


def save_answer(token, question_id, answer):
    payload = {
        'token': token,
        'answers': [{'question_id': question_id, 'answer': answer[:855]}],
    }
    result = _request('/api/interview/answer/', token, payload)
    if not isinstance(result, dict) or result.get('success') is not True:
        logger.error('DMCore did not confirm saving question_id=%s', question_id)
        raise DmcoreError('DMCore did not confirm saving the answer', kind='invalid_response')
    return result


def complete_interview(token):
    result = _request('/api/interview/complete/', token, {})
    if not isinstance(result, dict) or result.get('success') is not True:
        logger.error('DMCore did not confirm interview completion')
        raise DmcoreError('DMCore did not confirm interview completion', kind='invalid_response')
    return result


def decode_interview_link(encoded, expires_at, signature, now=None):
    key = os.environ.get('DMCORE_API_KEY', '').strip()
    if not key:
        logger.error('DMCore configuration missing required .env variable: DMCORE_API_KEY')
        raise DmcoreError('Interview link verification is not configured', 503, kind='configuration')
    if (not isinstance(encoded, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', encoded)
            or not isinstance(signature, str) or not re.fullmatch(r'[0-9a-f]{64}', signature)):
        raise DmcoreError('Invalid interview link', 400, kind='invalid_link')
    if not isinstance(expires_at, str) or not re.fullmatch(r'[0-9]+', expires_at):
        raise DmcoreError('Invalid interview link', 400, kind='invalid_link')
    expiration = int(expires_at)
    expected = hmac.new(key.encode('utf-8'), f'{encoded}.{expires_at}'.encode('utf-8'), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise DmcoreError('Invalid interview link', 400, kind='invalid_link')
    if expiration <= int(time.time() if now is None else now):
        raise DmcoreError('Interview link has expired', 410, kind='expired')
    try:
        raw = base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4))
        payload = json.loads(raw.decode('utf-8'))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise DmcoreError('Invalid interview link', 400, kind='invalid_link') from error
    if not isinstance(payload, dict) or set(payload) != {'candidate', 'questions'}:
        raise DmcoreError('Invalid interview link', 400, kind='invalid_link')
    candidate = payload.get('candidate')
    questions = payload.get('questions')
    if not isinstance(candidate, dict) or set(candidate) != {'name'} or not isinstance(candidate['name'], str):
        raise DmcoreError('Invalid interview link', 400, kind='invalid_link')
    if not isinstance(questions, list):
        raise DmcoreError('Invalid interview link', 400, kind='invalid_link')
    normalized_questions = []
    for question in questions:
        if (not isinstance(question, dict) or set(question) != {'field_name', 'description'}
                or not isinstance(question['field_name'], str) or not isinstance(question['description'], str)):
            raise DmcoreError('Invalid interview link', 400, kind='invalid_link')
        description = question['description'].strip()
        if description:
            normalized_questions.append({'field_name': question['field_name'], 'description': description})
    if not normalized_questions:
        raise DmcoreError('No interview questions are available right now', 422, kind='no_questions')
    return {'candidate': {'name': candidate['name']}, 'questions': normalized_questions}
