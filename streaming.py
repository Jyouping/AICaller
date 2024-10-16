import json
import asyncio
import websockets
import secrets_key
from flask import Flask, request
from flask_socketio import SocketIO, emit

OPENAI_API_KEY = secrets_key.openai_api_key2 

class StreamingAPI:

	def handle_media_stream(message):
	    stream_sid = None  # For tracking stream session ID
	    
	    async def openai_websocket():
	        # Connect to OpenAI Realtime API
	        openai_ws_url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
	        headers = {
	            'Authorization': f'Bearer {OPENAI_API_KEY}',
	            'OpenAI-Beta': 'realtime=v1'
	        }
	        
	        async with websockets.connect(openai_ws_url, extra_headers=headers) as openai_ws:
	            print('Connected to the OpenAI Realtime API')

	            # Send session update to OpenAI WebSocket
	            session_update = {
	                'type': 'session.update',
	                'session': {
	                    'turn_detection': {'type': 'server_vad'},
	                    'input_audio_format': 'g711_ulaw',
	                    'output_audio_format': 'g711_ulaw',
	                    'voice': VOICE,
	                    'instructions': SYSTEM_MESSAGE,
	                    'modalities': ['text', 'audio'],
	                    'temperature': 0.8,
	                }
	            }
	            await asyncio.sleep(0.25)  # Ensure connection stability
	            await openai_ws.send(json.dumps(session_update))
	            print('Session update sent')

	            # OpenAI WebSocket message handler
	            async for openai_message in openai_ws:
	                try:
	                    response = json.loads(openai_message)
	                    if response['type'] in LOG_EVENT_TYPES:
	                        print(f"Received event: {response['type']}", response)
	                    if response['type'] == 'response.audio.delta' and 'delta' in response:
	                        audio_delta = {
	                            'event': 'media',
	                            'streamSid': stream_sid,
	                            'media': {'payload': response['delta']}
	                        }
	                        emit('media', audio_delta)  # Send audio delta back to the client
	                except Exception as e:
	                    print(f"Error processing OpenAI message: {e}, Raw message: {openai_message}")

	    # Handle media stream event from the client (e.g., from Twilio)
	    if message['event'] == 'media':
	        asyncio.run(openai_websocket())  # Handle WebSocket in an async manner
	    elif message['event'] == 'start':
	        stream_sid = message['start']['streamSid']
	        print('Incoming stream has started', stream_sid)
	    else:
	        print('Received non-media event:', message['event'])