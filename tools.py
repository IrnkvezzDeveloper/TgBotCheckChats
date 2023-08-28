from pyrogram import Client


def get_client(number, session_str) -> Client:
    return Client(
        number,
        api_id=6,
        api_hash="eb06d4abfb49dc3eeb1aeb98ae0f581e",
        device_model="Samsung SM-G998B",
        system_version="SDK 31",
        app_version="8.4.1 (2522)",
        lang_code="en",
        session_string=session_str
    )
