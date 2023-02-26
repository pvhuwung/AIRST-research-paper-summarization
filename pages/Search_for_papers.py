

import os
import streamlit as st

# Define folder path
folder_path = "pdf_folder"

# Get list of PDF files in folder
pdf_files = [f for f in os.listdir(folder_path) if f.endswith(".pdf")]

# Define function to download PDF file
def download_pdf(pdf_file):
    with open(os.path.join(folder_path, pdf_file), "rb") as f:
        data = f.read()
        st.download_button(label="Download", data=data, file_name=pdf_file)

# Define main function
def main():
    st.title(":mag_right: :blue[AIRST] Search for Papers")
    # Add search bar
    search_term = st.text_input("Search for PDF files:")
    matching_files = [f for f in pdf_files if search_term.lower() in f.lower()]

    # Display PDF files matching search term
    if len(matching_files) == 0:
        st.write("No PDF files found.")
    else:
        for pdf_file in matching_files:
            st.write(pdf_file)
            download_pdf(pdf_file)

if __name__ == "__main__":
    main()
