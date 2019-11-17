import base64
from flask import abort
import hmac
from http import HTTPStatus
from gitsup import update_git_submodules
import googleapiclient.discovery
import os
import sys


def autoupdate(request):
    """
    Execute auto-update if the request contains the correct `X-Hub-Signature`,
    depending on the shared secret key.
    See https://developer.github.com/webhooks/creating/.
    """

    github_api_token, github_webhook_secret = _read_secrets()

    _check_signature(github_webhook_secret, request)

    request_json = request.get_json()
    try:
        trigger_name = request_json["repository"]["name"]
        print(f"Update triggered by repository '{trigger_name}'")
    except KeyError:
        print(f"Failed to get source repository name from request: {request_json}",
              file=sys.stderr)

    try:
        update_git_submodules(token=github_api_token)
    except ConnectionError as e:
        print(f"{e}", file=sys.stderr)
        abort(HTTPStatus.SERVICE_UNAVAILABLE)
    except (PermissionError, RuntimeError) as e:
        print(f"{e}", file=sys.stderr)
        abort(HTTPStatus.INTERNAL_SERVER_ERROR)

    return "ok"


def _read_secrets():
    """
    Get the secrets from the environment. They are stored encrypted, so
    we need to use the Google Key Management Service (KMS) to decrypt
    them.
    """

    crypto_key_id = os.environ["KMS_CRYPTO_KEY_ID"]
    encrypted_github_api_token = os.environ["GITHUB_API_TOKEN"]
    encrypted_github_webhook_secret = os.environ["GITHUB_WEBHOOK_SECRET"]

    kms_client = googleapiclient.discovery.build("cloudkms", "v1")

    github_api_token = _decrypt(kms_client,
                                crypto_key_id,
                                encrypted_github_api_token)
    github_webhook_secret = _decrypt(kms_client,
                                     crypto_key_id,
                                     encrypted_github_webhook_secret)

    return github_api_token, github_webhook_secret


def _decrypt(client, crypto_key_id, encrypted_secret):
    """ Decrypt a secret using the Google Key Management Service. """

    response = client \
        .projects() \
        .locations() \
        .keyRings() \
        .cryptoKeys() \
        .decrypt(name=crypto_key_id, body={"ciphertext": encrypted_secret}) \
        .execute()

    return base64.b64decode(response["plaintext"]).decode("utf-8").strip()


def _check_signature(secret, request):
    """ Check if we received the correct signature. """

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
