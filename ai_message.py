from openai import OpenAI

client = OpenAI(api_key=api_key2)
# Set your API key here



# Function to send a message to OpenAI
def send_message_to_openai(message):
    response = client.chat.completions.create(model="gpt-3.5-turbo",  # Specify the model
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},  # System message to set behavior
        {"role": "user", "content": message},  # User message to pass the input
    ])
    return response.choices[0].message.content

# Example usage
message = "Hello, can you explain the theory of relativity?"
response = send_message_to_openai(message)
print(response)