import asyncio
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request

async def main():
    oauth = OAuth()
    client = oauth.register(
        name='google',
        client_id='123',
        client_secret='123',
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
    )
    
    # Let's check the signature of fetch_access_token or if it accepts redirect_uri
    print("Test ready")

if __name__ == "__main__":
    asyncio.run(main())
