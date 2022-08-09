import base64
import logging

log = logging.getLogger(__name__)


def decode_token(token: str):
    token = token.split(".")
    return int(base64.b64decode(token[0] + '=='))
