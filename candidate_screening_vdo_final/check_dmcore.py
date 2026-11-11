"""Check DMCore reachability and API-key authentication without printing secrets."""
from pathlib import Path
import socket
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from dotenv import dotenv_values
except ImportError:
    print('FAIL: python-dotenv is not installed')
    raise SystemExit(1)

root = Path(__file__).resolve().parent
values = dotenv_values(root / '.env')
base_url = (values.get('DMCORE_BASE_URL') or '').strip().rstrip('/')
api_key = (values.get('DMCORE_API_KEY') or '').strip()
missing = [name for name, value in (('DMCORE_BASE_URL', base_url), ('DMCORE_API_KEY', api_key)) if not value]
if missing:
    print('FAIL: missing .env variable(s): ' + ', '.join(missing))
    raise SystemExit(1)

request = Request(
    base_url + '/api/interview/session/',
    headers={'X-API-Key': api_key, 'Accept': 'application/json'},
    method='GET',
)
try:
    with urlopen(request, timeout=8) as response:
        status = response.status
except HTTPError as error:
    status = error.code
    error.close()
except (socket.timeout, TimeoutError):
    print('FAIL: DMCore request timed out')
    raise SystemExit(1)
except URLError as error:
    reason = error.reason
    if isinstance(reason, (socket.timeout, TimeoutError)):
        print('FAIL: DMCore request timed out')
    elif isinstance(reason, ConnectionRefusedError):
        print('FAIL: connection refused; start DMCore and confirm the configured host/port')
    else:
        print('FAIL: DMCore is unreachable (' + type(reason).__name__ + ')')
    raise SystemExit(1)
except ConnectionRefusedError:
    print('FAIL: connection refused; start DMCore and confirm the configured host/port')
    raise SystemExit(1)

if status in (401, 403):
    print('FAIL: DMCore rejected DMCORE_API_KEY; compare it with AI_HR_API_KEY')
    raise SystemExit(1)
if status == 400:
    # DMCore authenticates X-API-Key before checking the candidate token.
    # No candidate token is sent by this diagnostic, so 400 confirms the
    # server is reachable and the shared key was accepted.
    print('PASS: DMCore is reachable and accepted X-API-Key (400 is expected without an interview token)')
    raise SystemExit(0)
if 200 <= status < 300:
    print('PASS: DMCore is reachable and accepted X-API-Key (HTTP ' + str(status) + ')')
    raise SystemExit(0)
print('FAIL: DMCore returned HTTP ' + str(status))
raise SystemExit(1)
