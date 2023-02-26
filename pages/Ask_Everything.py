import streamlit as st
import openai


# Set up OpenAI API credentials
openai.api_key = "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"

def Ask_Everything():
    # Define function to generate OpenAI answers
    def generate_response(prompt):
        completions = openai.Completion.create(
            engine = "text-davinci-003",
            prompt = prompt,
            max_tokens = 1024,
            n = 1,
            stop = None,
            temperature = 0.5,
        )
        message = completions.choices[0].text
        return message #Creating the chatbot interface


    st.title(":male-doctor: :blue[AIRST] automated doctor")
    if 'generated' not in st.session_state:
        st.session_state['generated'] = []

    if 'past' not in st.session_state:
        st.session_state['past'] = []

    def get_text():
        input_text = st.text_input("The Good Doctor: You can ask more than just medical related questions", key = "input")
        return input_text

    user_input = get_text()

    if user_input:
        output = generate_response(user_input)
        st.session_state.past.append(user_input)
        st.session_state.generated.append(output)

    if st.session_state['generated']:
        for i in range(len(st.session_state['generated'])-1, -1, -1):
            message(st.session_state["generated"][i], key=str(i))
            message(st.session_state['past'][i], is_user=True, key=str(i) + '_user')

        
if __name__ == '__main__':
    Ask_Everything()

