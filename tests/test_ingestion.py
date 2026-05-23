from analyst.ingestion.chunking import recursive_split
from analyst.ingestion.loaders import load_text
from langchain_core.documents import Document 

# pytest only collects functions prefixed with `test_`.

def test_recursive_split_respects_chunk_size():
    chunks = recursive_split(docs=[Document(page_content="word " * 500)], chunk_size=200)
    assert len(chunks) > 1
    assert all(len(c.page_content) <= 200 for c in chunks)


def test_recursive_split_propagates_metadata():
    doc = Document(page_content= "alpha "*300, metadata={"ticker": "ABC", "source": "f.pdf"})
    chunks = recursive_split([doc])
    assert all(c.metadata["ticker"]=="ABC" for c in chunks)

def test_load_text(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("Q4 revenue rose by 12%")
    docs = load_text(file_path=str(f))
    assert len(docs) == 1
    assert docs[0].metadata["source"] == str(f)