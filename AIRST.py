import streamlit as st
from pages.Search_for_papers import Search_for_papers
#from pages.Upload import Upload
from pages.Summarize import Summarize
from pages.Ask_Everything import Ask_Everything

# Create a Streamlit app with sidebar

def main():
    st.title(':medical_symbol: :blue[AI R]esearch :blue[S]ummary :blue[T]ool   	')
    st.write('Welcome to our AI Research Summary Tool! Our app uses state-of-the-art AI technology to help healthcare professionals quickly and easily access and understand the latest research and findings related to healthcare.')
    st.write('Our tool is designed to convert research articles into a variety of formats that are easy to understand and consume. This tool will allow healthcare professionals to quickly and easily access and digest the latest research and findings, as well as create informative and engaging presentations for their colleagues and patients.')
    
if __name__ == '__main__':
    main()
