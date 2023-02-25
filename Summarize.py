#import streamlit
import openai
import json
import os
import fitz
import streamlit as st


def Summarize(pdf_file_name):
    # Retrive Key
    OPENAI_API_KEY = ''
    with open('/Users/trongphan/Desktop/hoho/OpenAI.json', 'r') as file_to_read:
        json_data = json.load(file_to_read)
        OPENAI_API_KEY = json_data["OPENAI_API_KEY"]

    openai.api_key = OPENAI_API_KEY

    # get docs file
    doc = fitz.open('/Users/trongphan/Downloads/' + pdf_file_name + '.pdf')

    # get summartization text list
    summary_list = []
    for page in doc:
        text = page.get_text("text")
        # print(text)
        prompt = "Summarize" + pdf_file_name + "by this parts: Abstract Introduction Background or Related Work Methodology or Approach\
            Results or Findings Discussion or Interpretation Conclusion or Summary"+text
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            temperature=0.7,
            max_tokens=120,
            top_p=0.9,
            frequency_penalty=0.0,
            presence_penalty=1
        )
        summary_list.append(response["choices"][0]["text"])
    # print summarization of text
    summary_text = ' '.join(summary_list)
    return summary_text


text = Summarize("Attention")
st.write(text)
