import secrets
from flask import Flask, request, redirect, session
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from openai import OpenAI

app = Flask(__name__)

app.secret_key = secrets.flask_secret
_api_key1 = secrets.vGHheqhAD0uVn28N6A8VkFOL06YvD3rqeHjD1hFl31T3BlbkFJfNRMo20F1kIRXMhCdMdGXA7BwMfe6TLwxHOWQON10A
_api_key2 = secrets.openai_api_key2 
_secret_account_sid = secrets.secret_account_sid
_secret_auth_token = secrets.secret_auth_token
TWILIO_PHONE_NUMBER = "+16506484063";
dest_number = "+14084775376"
# Set initial prompt for the conversation context
INITIAL_PROMPT = "You are doing a role playing, being a person called Shunping, and you want to book a restaurant with 5 people around dinner time, 6:00-8:00pm. Your telephone is 4084775376. You will need wait the next response to answer. And you can conclude the message if you confirm the booking. You should only output the sentence you need to really say."


openai_client = OpenAI(api_key=_api_key2)

client = Client(_secret_account_sid, _secret_auth_token)


@app.route("/voice", methods=['GET', 'POST'])
def voice():
    print("voice")
    response = VoiceResponse()

    # Use Twilio's Gather to collect speech or input from the caller
    gather = Gather(input='speech', action='/handle_input', method='POST', timeout=5)
    #gather.say("Hi! Hello!")
    response.append(gather)

    # If no input was received, ask the caller again
    response.redirect('/voice')

    return str(response)

@app.route("/test", methods=['POST'])
def test():
    print("test")
    return f"Successful\n"

@app.route("/make_call", methods=['POST'])
def make_call():
    #customer_phone_number = request.form.get('phone_number')  # Customer's phone number from POST request

    # Create an outbound call
    print("receive phone call to test ")
    call = client.calls.create(
        to=dest_number,  # The customer's phone number
        from_=TWILIO_PHONE_NUMBER,  # Your Twilio phone number
        url= "https://ba38-73-93-166-237.ngrok-free.app/" + "voice"  # TwiML URL for handling the call
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
def handle_input():
    print("handle_input")
    response = VoiceResponse()

    # Extract the caller's message from Twilio's request
    caller_message = request.form.get('SpeechResult', '')
    print("handle_input...", caller_message)

    # If the caller says "goodbye," end the call
    if "goodbye" in caller_message.lower():
        response.say("Goodbye! Have a great day!")
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
    response.say(agent_response)

    # Continue the loop by asking for more input
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

