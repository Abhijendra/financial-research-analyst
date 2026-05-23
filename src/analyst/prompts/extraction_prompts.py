from langchain_core.prompts import ChatPromptTemplate


FINANCIALS_PROMPT: ChatPromptTemplate = ChatPromptTemplate.from_messages(
        [
            ('system', 'You are a financial data extractor. Extract only facts explicitly stated in the supplied text. Do not infer currency, units, or dates that are not present. If a required field is missing, leave it null where allowed; otherwise the extraction should fail rather than be invented.'),
            ('human', 'Document:\n\n{document_text}')
        ]
    )

RISKS_PROMPT: ChatPromptTemplate = ChatPromptTemplate.from_messages(
    [
        ('system', 'You are a risk extractor. List down all the risks disclosed in the supplied text. For each risk, set `source_excerpt` to a VERBATIM quote from the text - do not paraphrase. Do not invent risks that are not stated. If the text discloses no risks return empty list.'),
        ('human', 'Document:\n\n{document_text}')
    ]
)


SENTIMENT_PROMPT : ChatPromptTemplate = ChatPromptTemplate.from_messages(
    [
        ('system', 'You are a sentiment extractor. Extract and assess overall sentiment expressed by the Author about company performance. Use only the signal present in the text. Quote the same or minimum paraphrase it in `rationale`. Note: `label` and `score` must agree in sign: positive → score ≥ 0, negative → score ≤ 0, neutral → score near 0.'),
        ('human', 'Document:\n\n{document_text}')
    ]
)