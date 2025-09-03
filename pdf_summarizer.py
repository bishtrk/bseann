import os
import sys
import json
import argparse
import requests
from io import BytesIO
from PyPDF2 import PdfReader, errors
from langchain.docstore.document import Document
from langchain.text_splitter import TokenTextSplitter
from langchain_openai import ChatOpenAI
from langchain.chains.summarize import load_summarize_chain
import tiktoken

CONFIG_FILE = 'config-notification.json'

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def download_pdf_from_url(url):
    response = requests.get(url)
    response.raise_for_status()
    return BytesIO(response.content)

def extract_text_from_pdf(pdf_file):
    try:
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except errors.PyPdfError as e:
        raise ValueError(f"Corrupted PDF: {e}")

def chunk_text(text, token_limit=1500):  # for gpt-3.5-turbo, adjust based on model
    splitter = TokenTextSplitter(
        encoding_name="gpt2",  # approximate for gpt-3.5
        chunk_size=token_limit,
        chunk_overlap=100
    )
    return splitter.split_text(text)

def summarize_text(text, llm, retries=3):
    chain = load_summarize_chain(llm, chain_type="map_reduce")
    docs = [Document(page_content=text)]
    for attempt in range(retries):
        try:
            summary = chain.run(docs)
            return summary
        except Exception as e:
            if attempt == retries - 1:
                raise e
            print(f"Retry {attempt+1} due to: {e}")

def save_summary(filename, summary):
    os.makedirs('summary', exist_ok=True)
    base = os.path.splitext(filename)[0]
    with open(f'summary/{base}_summary.txt', 'w') as f:
        f.write(summary)

def log_error(error_msg):
    with open('processing-error.txt', 'a') as f:
        f.write(f"{error_msg}\n")

def main():
    parser = argparse.ArgumentParser(description="Summarize PDFs using AI")
    parser.add_argument('--url', help='URL of PDF to summarize')
    parser.add_argument('--dir', default='input', help='Directory of PDFs to process')
    args = parser.parse_args()

    config = load_config()
    api_key = config['openrouter']['api_key']
    llm = ChatOpenAI(
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        model_name="gpt-3.5-turbo"  # free via OpenRouter
    )

    if args.url:
        try:
            pdf_io = download_pdf_from_url(args.url)
            text = extract_text_from_pdf(pdf_io)
            chunks = chunk_text(text)
            full_summary = ""
            for chunk in chunks:
                summary = summarize_text(chunk, llm)
                full_summary += summary + "\n"
            save_summary('url_download.pdf', full_summary)  # or parse filename from url
        except Exception as e:
            log_error(f"Error processing URL {args.url}: {e}")
    else:
        for root, dirs, files in os.walk(args.dir):
            for file in files:
                if file.lower().endswith('.pdf'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'rb') as f:
                            text = extract_text_from_pdf(f)
                        chunks = chunk_text(text)
                        full_summary = ""
                        for chunk in chunks:
                            summary = summarize_text(chunk, llm)
                            full_summary += summary + "\n"
                        save_summary(file, full_summary)
                    except Exception as e:
                        log_error(f"Error processing {file}: {e}")
                        print(f"Skipped {file} due to error: {e}")

if __name__ == "__main__":
    main()
