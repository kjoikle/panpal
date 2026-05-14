import base64
import asyncio
from django.conf import settings


async def synthesize_and_send(text: str, send_func) -> None:
    """
    Generate speech from text using ElevenLabs and send base64 audio chunks
    over WebSocket. Falls back to sending text-only if TTS is unavailable.
    """
    api_key = settings.ELEVENLABS_API_KEY
    if not api_key:
        await send_func({'type': 'text_transcript', 'text': text})
        return

    try:
        from elevenlabs.client import ElevenLabs

        client = ElevenLabs(api_key=api_key)

        # Run synchronous ElevenLabs call in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        audio_bytes = await loop.run_in_executor(
            None,
            lambda: _generate_audio(client, text)
        )

        # Send transcript alongside audio
        await send_func({'type': 'text_transcript', 'text': text})

        # Send audio as a single chunk (turbo model is fast enough)
        await send_func({
            'type': 'audio_chunk',
            'data': base64.b64encode(audio_bytes).decode('utf-8'),
        })
        await send_func({'type': 'audio_end'})

    except Exception as e:
        # If TTS fails, still deliver the text
        await send_func({'type': 'text_transcript', 'text': text})
        await send_func({'type': 'tts_error', 'message': str(e)})


def _generate_audio(client, text: str) -> bytes:
    """Synchronous ElevenLabs audio generation (SDK v1.x)."""
    voice_id = settings.ELEVENLABS_VOICE_ID
    audio_generator = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id='eleven_turbo_v2',
        output_format='mp3_44100_128',
    )
    return b''.join(chunk for chunk in audio_generator if chunk)
