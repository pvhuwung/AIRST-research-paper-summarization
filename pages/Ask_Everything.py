import streamlit as st
import openai


# Set up OpenAI API credentials
openai.api_key = "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"

# Define function to generate OpenAI answers
def generate_answer(prompt, model):
    response = openai.Completion.create(
        engine=model,
        prompt=prompt,
        max_tokens=1024,
        n=1,
        stop=None,
        temperature=0.7,
    )
    answer = response.choices[0].text.strip()
    return answer

# Define Streamlit app
def Ask_Everything():
    st.title(':medical_symbol: :blue[AIRST] Question Answering Tool')
    st.write('Welcome to our AIRST Question Answering Tool! Our app uses the latest AI technology from OpenAI to help you get quick and accurate answers to your questions.')
    
    # Define input prompt and model options
    prompt = st.text_input('Enter your question:')
    model = st.selectbox('Select an AI model:', ['davinci', 'curie', 'babbage', 'ada'])
    
    # Generate and display answer
    if prompt:
        answer = generate_answer(prompt, model)
        st.write('Answer:')
        st.write(answer)

if __name__ == '__main__':
    Ask_Everything()

