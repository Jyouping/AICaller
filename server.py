import secrets_key
from flask import Flask, request, redirect, session, send_from_directory
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from openai import OpenAI
from pathlib import Path
from prompts import Prompt
import requests
from flask_sockets import Sockets, Rule
import base64
import json
import logging
from streaming import StreamingAPI
from voice_mapping import VoiceConfig

app = Flask(__name__)
sockets = Sockets(app)


app.secret_key = secrets_key.flask_secret
_api_key1 = secrets_key.openai_api_key1
_api_key2 = secrets_key.openai_api_key2 
_secret_account_sid = secrets_key.secret_account_sid
_secret_auth_token = secrets_key.secret_auth_token
TWILIO_PHONE_NUMBER = "+16506484063";
dest_number = "+14084775376"
# Set initial prompt for the conversation context
server_location = "7229-73-93-166-237.ngrok-free.app"
stream_server_location = "0.tcp.us-cal-1.ngrok.io:16691"
HINTS_en_US = "o'clock, restaurant, book, time, date, phone number, name, Shunping, confirmed"
HINTS_zh_TW = "餐廳, 時間, 電話, 姓名, 預定, 確認"

end_words = ["good bye", "再見", "goodbye", "再见"]

openai_client = OpenAI(api_key=_api_key2)

client = Client(_secret_account_sid, _secret_auth_token)

use_phone_boost = True
use_open_ai_voice = True
use_streaming = False
language = "zh-TW"

voice_mapping = VoiceConfig(language)

if language == "en-US":
    HINTS_PROMPT = HINTS_en_US
else:
    HINTS_PROMPT = HINTS_zh_TW

def get_greeing_text(language):
    if language == "zh-TW":
        return "哈囉，可以聽得見嗎"
    else:
        return "Hello"


def openai_speech(message):
    speech_file_path = Path(__file__).parent / "audios/speech.mp3"
    response = openai_client.audio.speech.create(
        model="tts-1",
        voice=voice_mapping.get_open_ai_voice(),
        input=message
    )
    response.stream_to_file(speech_file_path)


@app.route('/audios/<path:filename>', methods=['GET'])
def serve_audio(filename):
    return send_from_directory('audios', filename)


@app.route("/initial_voice", methods=['GET', 'POST'])
def initial_voice():
    print("initial_voice")
    return voice(greeting=True)

@app.route("/voice", methods=['GET', 'POST'])
def voice(greeting=False):
    print("voice")
    response = VoiceResponse()
    if use_streaming:   #Not supported
        print(f'wss://{server_location}/media_stream')
        response.connect().stream(url=f'wss://{server_location}/media_stream')
        response.pause(20)
        return str(response)

    if use_phone_boost:
        gather = Gather(input='speech', speechModel='phone_call', action='/handle_input', method='POST', speechTimeout='auto', language=language, timeout=3, hints=HINTS_PROMPT, enhanced=True)
    else:
        gather = Gather(input='speech', speechModel='deepgram_nova-2', action='/handle_input', method='POST', speechTimeout='auto', language=language, timeout=3, hints=HINTS_PROMPT)
 
    response.append(gather)

        # Use Twilio's Gather to collect speech or input from the caller
        #gather.say("Hi! Hello!")
        # If no input was received, ask the caller again
    if greeting:
        greeting_text = "hello"
        openai_speech(get_greeing_text(language))
        response.play(f"https://{server_location}/audios/speech.mp3")
    response.redirect('/voice')
    return str(response)


@app.route("/test", methods=['POST'])
def test():
    print("test")
    return f"Successful\n"

@app.route("/make_call", methods=['POST'])
def make_call():
    #customer_phone_number = request.form.get('phone_number')  # Customer's phone number from POST request
    session.clear()
    # Create an outbound call
    print("receive phone call to test ")
    call = client.calls.create(
        to=dest_number,  # The customer's phone number
        from_=TWILIO_PHONE_NUMBER,  # Your Twilio phone number
        url= f"https://{server_location}/initial_voice"  # TwiML URL for handling the call
    )
    return f"Call initiated: {call.sid}"

@app.route("/dry_run", methods=['POST'])
def dry_run():
    print("dry_run")
    caller_message = request.form.get('msg')
    print("handle_input...", caller_message)
    if 'chat_history' not in session:
        prompt = Prompt(lang=language, name='王大明')
        session['chat_history'] = prompt.get_prompt() # Start with the initial prompt

    # Append the caller's message to the chat history
    session['chat_history'] += f"\nCaller: {caller_message}"

    # Send the updated conversation history to ChatGPT
    agent_response = get_chatgpt_response(session['chat_history'])
    agent_response = agent_response.choices[0].message.content

    # Append ChatGPT's response to the chat history
    session['chat_history'] += f"\nAssistant: {agent_response}"

    return f"agent_response{agent_response}\n"

# Handle input from caller and send to ChatGPT
@app.route("/handle_input", methods=['POST'])
def handle_input(twilo_transcript=True, message=""):
    print("handle_input")
    response = VoiceResponse()

    # Extract the caller's message from Twilio's request
    if twilo_transcript:
        caller_message = request.form.get('SpeechResult', '')
    else:
        caller_message = message
    print("handle_input...", caller_message)
    # TODO confidence handling

    # If the caller says "goodbye," end the call
    if "goodbye" in caller_message.lower():
        response.hangup()
        return str(response)

    # Retrieve or initialize conversation history from the session
    if 'chat_history' not in session:
        prompt = Prompt(lang=language, name='王大明')
        session['chat_history'] = prompt.get_prompt() # Start with the initial prompt


    # Append the caller's message to the chat history
    session['chat_history'] += f"\nCaller: {caller_message}"

    # Send the updated conversation history to ChatGPT
    agent_response = get_chatgpt_response(session['chat_history'])
    agent_response = agent_response.choices[0].message.content

    # Append ChatGPT's response to the chat history
    session['chat_history'] += f"\nAssistant: {agent_response}"

    # Repeat the conversation back to the caller
    if use_open_ai_voice:
        openai_speech(agent_response)
        response.play(f"https://{server_location}/audios/speech.mp3")
    else:   #TODO voice mapping according to language
        response.say(agent_response, voice=voice_mapping.get_twilio_voice(), language=language)

    # Continue the loop by asking for more input
    for end_word in end_words:
        if end_word in caller_message.lower() or end_word in agent_response.lower():
            print("end word", end_word)
            response.hangup()
    else:
        response.redirect('/voice')

    return str(response)

def get_chatgpt_response(caller_message):
    response = openai_client.chat.completions.create(model="gpt-4o",  # Or other models like "gpt-3.5-turbo"
    messages=[
        {"role": "system", "content": "The assistent is trying to make a reservation for himself, don't let people discover you are not human. Only output the conversation response, dont output the role at beginning"},  # System message to set behavior
        {"role": "user", "content": caller_message},  # User message to pass the input
    ])
    print("[DEBUG]",caller_message)
    print("[DEBUG]",response)
    return response

@sockets.route('/media_stream', websocket=True)
def media_stream(ws):
    app.logger.info(f"Connection accepted")
    prompt = Prompt(lang=language, name='王大明')

    openAIstream = StreamingAPI(prompt.get_prompt(), end_words, client)
    openai_ws = None
    while not ws.closed:
        message = ws.receive()
        if message:
            try:
                data = json.loads(message)
                if data.get('event') == 'media':
                    # test code to reproduce the message
                    '''audio_delta = {
                        'event': 'media',
                        'streamSid': stream_sid,
                        'media': {'payload': data['media']['payload']}
                    }
                    print(f"sending audio...delta sid {stream_sid}")
                    ws.send(json.dumps(audio_delta))'''

                    if openai_ws.sock and openai_ws.sock.connected:
                        audio_append = {
                            'type': 'input_audio_buffer.append',
                            'audio': data['media']['payload']
                        }
                        openai_ws.send(json.dumps(audio_append))
                elif data.get('event') == 'start':
                    stream_sid = data['start']['streamSid']
                    callSid = data['start']['callSid']
                    print(f"Incoming stream has started: {stream_sid}")
                    openai_ws = openAIstream.openai_ws_connect(ws, stream_sid, callSid)
                else:
                    print(f"Received non-media event: {data.get('event')}")
            except Exception as e:
                print(f"Error parsing message: {e}, Message: {message}")

    # Close OpenAI WebSocket when client disconnects
    if openai_ws.sock and openai_ws.sock.connected:
        openai_ws.close()

    response = VoiceResponse() 
    return response.hangup()


@app.route("/answer", methods=['GET', 'POST'])
def answer_call():
    """Respond to incoming phone calls with a brief message."""
    # Start our TwiML response

    resp = VoiceResponse()

    # Read a message aloud to the caller
    resp.say("Thank you for calling! Have a great day.", voice='Polly.Amy')

    return str(resp)


# evil hack to fix socket bug
sockets.url_map.add(Rule('/media_stream', endpoint=media_stream, websocket=True))


if __name__ == "__main__":
    app.logger.setLevel(logging.DEBUG)
    #socketio.run(app, host='0.0.0.0', port=6000, debug=True)
    #app.run(host='0.0.0.0', port=6000)
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler

    server = pywsgi.WSGIServer(('0.0.0.0', 6000), app, handler_class=WebSocketHandler)
    #server = pywsgi.WSGIServer(('0.0.0.0', 6000), app)
    print("Server listening on: http://localhost:" + str(6000))
    server.serve_forever()

