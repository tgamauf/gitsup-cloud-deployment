from flask import abort
import hmac
from http import HTTPStatus
from gitsup import update_git_submodules
import os
import sys


def autoupdate(request):
    """
    Execute auto-update if the request contains the correct `X-Hub-Signature`,
    depending on the shared secret key.
    See https://developer.github.com/webhooks/creating/.
    """

    _check_signature(request)

    request_json = request.get_json()
    try:
        trigger_name = request_json["repository"]["name"]
        print(f"Update triggered by repository '{trigger_name}'")
    except KeyError:
        print(f"Failed to get source repository name from request: {request_json}",
              file=sys.stderr)

    try:
        update_git_submodules()
    except ConnectionError as e:
        print(f"{e}", file=sys.stderr)
        abort(HTTPStatus.SERVICE_UNAVAILABLE)
    except (PermissionError, RuntimeError) as e:
        print(f"{e}", file=sys.stderr)
        abort(HTTPStatus.INTERNAL_SERVER_ERROR)

    # Update succeeded
    return "ok"


def _check_signature(request):
    """ Check if we received the correct signature. """

    secret = os.environ["SECRET_TOKEN"]

    header_signature = request.headers.get("X-Hub-Signature")
    if not header_signature:
        print("Header signature missing in request", file=sys.stderr)
        abort(HTTPStatus.FORBIDDEN)

    sha_name, signature = header_signature.split("=")
    if sha_name != "sha1":
        print(f"Signature has invalid digest type: {sha_name}", file=sys.stderr)
        abort(HTTPStatus.NOT_IMPLEMENTED)

    mac = hmac.new(secret.encode("UTF-8"), msg=request.data, digestmod="sha1")

    if not hmac.compare_digest(str(mac.hexdigest()), str(signature)):
        print("Invalid header signature in request", file=sys.stderr)
        abort(HTTPStatus.FORBIDDEN)