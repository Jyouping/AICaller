import json
import asyncio
import websocket
import secrets_key
import threading
import time

OPENAI_API_KEY = secrets_key.openai_api_key2 

#LOG_EVENT_TYPES = ["session.updated", "response.audio.delta"]
LOG_EVENT_TYPES = []
VOICE = "alloy"

class StreamingAPI:
	def __init__(self, prompt, end_words, twilio_client, call_sid):
		self.openai_ws = None 
		self.prompt = prompt
		self.end_words = end_words
		self.end_call = False
		self.thread = None
		self.twilio_client = twilio_client	# TODO: change into callback
		self.call_sid = call_sid

	def openai_ws_connect(self, connection, stream_sid):	#connection is to connect flask socket
	    """Connect to the OpenAI WebSocket API."""

	    def send_session_update(ws):
	        session_update = {
	            'type': 'session.update',
	            'session': {
	                'turn_detection': {'type': 'server_vad'},
	                'input_audio_format': 'g711_ulaw',
	                'output_audio_format': 'g711_ulaw',
	                'voice': VOICE,
	                'instructions': self.prompt,
	                'modalities': ["text", "audio"],
	                'temperature': 0.8
	            }
	        }
	        print('Sending session update:', json.dumps(session_update))
	        ws.send(json.dumps(session_update))

	    def on_open(ws):
	        print("Connected to the OpenAI Realtime API")
	        time.sleep(0.25)  # Ensure connection stability
	        send_session_update(ws)

	    def on_message(ws, message):
	        try:
	            response = json.loads(message)
	            if response.get('type') in LOG_EVENT_TYPES:
	                print(f"Received event: {response['type']}", response)

	            if response.get('type') == 'session.updated':
	                print('Session updated successfully:', response)

	            if response.get('type') == 'response.audio_transcript.done':
	            	print(response['transcript'])
	            	msg = response['transcript']
	            	for end_word in self.end_words:
	            		if end_word in msg:
	            			self.end_call = True


	            if response.get('type') == 'response.audio.delta' and 'delta' in response:
	                audio_delta = {
	                    'event': 'media',
	                    'streamSid': stream_sid,
	                    'media': {'payload': response['delta']}
	                }
	                print(f"sending audio...delta sid {stream_sid}")
	                connection.send(json.dumps(audio_delta))
	                if self.end_call:
	                	print(f"ending call...clean up")
	                	connection.close()
	                	self.twilio_client.calls(self.call_sid).update(status='completed')
	                	self.thread.join()

	        except Exception as e:
	            print(f"Error processing OpenAI message: {e}, Raw message: {message}")

	    def on_close(ws):
	        print("Disconnected from the OpenAI Realtime API")

	    def on_error(ws, error):
	        print(f"Error in OpenAI WebSocket: {error}")

	    # Open WebSocket connection to OpenAI API
	    self.openai_ws = websocket.WebSocketApp(
	        'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01',
	        header={
	            'Authorization': f'Bearer {OPENAI_API_KEY}',
	            'OpenAI-Beta': 'realtime=v1'
	        },
	        on_open=on_open,
	        on_message=on_message,
	        on_close=on_close,
	        on_error=on_error
	    )

	    def run_openai_ws():
	        self.openai_ws.run_forever()

	    # Start the OpenAI WebSocket in a separate thread
	    self.thread = threading.Thread(target=run_openai_ws).start()

	    return self.openai_ws
