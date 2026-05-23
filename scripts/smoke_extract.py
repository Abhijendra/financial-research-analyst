from analyst.ingestion.loaders import load_text
from analyst.extraction.structured import build_full_extractor, attach_provenance
import sys 
from analyst.schemas.provenance import Provenance

def main(path: str):

    doc = load_text(path)
    text = doc[0].page_content
    chain = build_full_extractor()
    provenance = Provenance(source=path, document_type="earnings_report")

    result = chain.invoke({"document_text": text})
    enriched = attach_provenance(result, provenance)

    print(enriched["financials"])
    print(enriched["risks"])
    print(enriched["sentiment"])
    print(enriched["provenance"])

if __name__ == "__main__":
    main(sys.argv[1])

