from langchain_text_splitters import RecursiveCharacterTextSplitter


def recursive_split(docs, chunk_size:int=200, chunk_overlap:int=0):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    result = splitter.split_documents(docs)
    return result

