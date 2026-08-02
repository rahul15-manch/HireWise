import asyncio
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request

oauth = OAuth()
oauth.register(
    name='google',
    client_id='123',
    client_secret='123',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
)

print("OAuth client initialized")
