from analyst.schemas.provenance import Provenance

def attach_provenance(result: dict, provenance: Provenance) -> dict:
    """Attach ingestion metadata to an extractor's output.

      Provenance comes from the chunk, not the LLM — kept out of every
      extraction schema on purpose so the model can't hallucinate source paths
      or page numbers. Pure function, does not mutate `result`.
    """    
    return {**result, "provenance": provenance}

