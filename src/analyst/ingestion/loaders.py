from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import WebBaseLoader

DATA_DIR = "data"

def load_pdf(file_path:str):
    
    loader = PyMuPDFLoader(file_path)
    docs = loader.load()
    return docs 

def load_text(file_path:str):
    loader = TextLoader(file_path)
    docs = loader.load()
    return docs 

def load_from_web(url:str):
    loader = WebBaseLoader(url)
    docs = loader.load()
    return docs 
