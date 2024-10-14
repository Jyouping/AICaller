import secrets
from flask import Flask, request, redirect, session, send_from_directory
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from openai import OpenAI
from pathlib import Path
import requests

app = Flask(__name__)

app.secret_key = secrets.flask_secret
_api_key1 = secrets.openai_api_key1
_api_key2 = secrets.openai_api_key2 
_secret_account_sid = secrets.secret_account_sid
_secret_auth_token = secrets.secret_auth_token
TWILIO_PHONE_NUMBER = "+16506484063";
dest_number = "+14084775376"
# Set initial prompt for the conversation context
INITIAL_PROMPT_en_US = "You are doing a role playing, being a person called Shunping to book a restaurant with 5 people around dinner time, 6:00-8:00pm. It must be tonight. Your telephone is 408123456. You will need wait the next response to answer. And you can conclude the message if you confirm the booking but you need to make sure you name is delivered. Also said goodbye to end the conversation if you cannot book it. You should only output the sentence you need to really say."
server_location = "https://ba38-73-93-166-237.ngrok-free.app"
INITIAL_PROMPT_zh_TW = "你正在進行角色扮演，扮演一個叫做邱先生的人要預訂餐廳，你為5個人預訂晚餐，okay的入座時間是6點到8點，時間只能是今天晚上，不要問其他天。你的電話號碼是12345678，講號碼是前面要加「電話是」。你需要等待下一個回應再做回答。確認預定之前要確保姓名告知對方，如果確認預訂，則可以用 goodbye 結束對話。因為沒有位置或其他因素預定失敗的話也需要用 goodbye 結束對話，你應該只輸出你實際需要說的句子，記住你是要預訂的客人不是店員，對話要人性化不要太制式，對話不要太長。"
HINTS_en_US = "o'clock, restaurant, book, time, date, phone number, name, Shunping, confirmed"
HINTS_zh_TW = "餐廳, 時間, 電話, 姓名, 預定, 確認"

end_words = ["goodbye", "再見"]

openai_client = OpenAI(api_key=_api_key2)

client = Client(_secret_account_sid, _secret_auth_token)

use_phone_boost = True
use_open_ai_voice = True
language = "zh-TW"

if language == "en-US":
    INITIAL_PROMPT = INITIAL_PROMPT_en_US
    HINTS_PROMPT = HINTS_en_US
else:
    INITIAL_PROMPT = INITIAL_PROMPT_zh_TW
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
        voice="alloy",
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
        response.play(server_location + "/audios/speech.mp3")
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
        url= server_location + "/initial_voice"  # TwiML URL for handling the call
    )

    return f"Call initiated: {call.sid}"

@app.route("/dry_run", methods=['POST'])
def dry_run():
    print("dry_run")
    caller_message = request.form.get('msg')
    print("handle_input...", caller_message)
    if 'chat_history' not in session:
        session['chat_history'] = INITIAL_PROMPT  # Start with the initial prompt

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

    # If the caller says "goodbye," end the call
    if "goodbye" in caller_message.lower():
        response.hangup()
        return str(response)

    # Retrieve or initialize conversation history from the session
    if 'chat_history' not in session:
        session['chat_history'] = INITIAL_PROMPT  # Start with the initial prompt

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
        response.play(server_location + "/audios/speech.mp3")
    else:
        response.say(agent_response)

    # Continue the loop by asking for more input
    for end_word in end_words:
        if end_word in caller_message.lower() or end_word in agent_response.lower():
            print("end word", end_word)
            response.hangup()
    else:
        response.redirect('/voice')

    return str(response)

def get_chatgpt_response(caller_message):
    response = openai_client.chat.completions.create(model="gpt-4o-mini",  # Or other models like "gpt-3.5-turbo"
    messages=[
#        {"role": "system", "content": "You are being a customer, try to book the restaurant, and the user is restaurant, so you need to answer that as a customer"},  # System message to set behavior
        {"role": "user", "content": caller_message},  # User message to pass the input
    ])
    print("[DEBUG]",caller_message)
    print("[DEBUG]",response)
    return response


@app.route("/answer", methods=['GET', 'POST'])
def answer_call():
    """Respond to incoming phone calls with a brief message."""
    # Start our TwiML response

    resp = VoiceResponse()

    # Read a message aloud to the caller
    resp.say("Thank you for calling! Have a great day.", voice='Polly.Amy')

    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=6000)

