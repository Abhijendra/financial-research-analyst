"""Demo of the router chain across invoke / batch / stream / async surfaces.

The point of this script is the lesson from Week 2: once a pipeline is built
out of Runnables, `.invoke`, `.batch`, `.stream`, `.ainvoke`, `.abatch`, and
`.astream` come for free. No code changes between modes — same `chain` object,
different call.
"""

import asyncio
from pprint import pprint

from analyst.chains.router import build_router_chain
from analyst.ingestion.loaders import load_text


def _read(path: str) -> str:
    docs = load_text(path)
    return "\n\n".join(d.page_content for d in docs)


def demo_invoke(chain, sample: dict) -> None:
    print("\n=== .invoke (one doc) ===")
    result = chain.invoke(sample)
    classification = result["classification"]
    print(f"document_type : {classification.document_type}")
    print(f"confidence    : {classification.confidence:.2f}")
    print(f"reason        : {classification.reason}")
    print("--- extraction ---")
    pprint(result["extraction"])


def demo_batch(chain, samples: list[dict]) -> None:
    print(f"\n=== .batch ({len(samples)} docs) ===")
    results = chain.batch(samples)
    for i, r in enumerate(results):
        c = r["classification"]
        print(f"[{i}] {c.document_type} (conf={c.confidence:.2f})")


async def demo_astream(chain, sample: dict) -> None:
    print("\n=== .astream (one doc) ===")
    # For structured pipelines, astream yields incremental dict updates as each
    # step of the LCEL graph completes (assign-style chains stream per-key).
    async for chunk in chain.astream(sample):
        print("chunk:", chunk)


async def demo_abatch(chain, samples: list[dict]) -> None:
    print(f"\n=== .abatch ({len(samples)} docs) ===")
    results = await chain.abatch(samples)
    for i, r in enumerate(results):
        c = r["classification"]
        print(f"[{i}] {c.document_type} (conf={c.confidence:.2f})")


def main() -> None:
    chain = build_router_chain()

    doc_text = _read("data/test.txt")
    sample = {"document_text": doc_text}
    # Same doc twice — enough to exercise batch fan-out without needing more
    # data in the repo. Swap in real files when available.
    samples = [sample, sample]

    demo_invoke(chain, sample)
    demo_batch(chain, samples)
    asyncio.run(demo_astream(chain, sample))
    asyncio.run(demo_abatch(chain, samples))


if __name__ == "__main__":
    main()
