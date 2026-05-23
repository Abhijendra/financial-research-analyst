from langchain_core.runnables import ConfigurableField, Runnable
from langchain.chat_models import init_chat_model
from analyst.config import settings

def get_chat_model(model: str | None = None, temperature: float | None = None) -> Runnable:
    """Return a runtime-configurable ChatModel.

      Built via `init_chat_model` so the provider/model string (e.g.
      "openai:gpt-4o-mini", "anthropic:claude-3-5-sonnet") is data, not code —
      swapping providers does not require touching any chain that consumes this
      model. The returned Runnable exposes `model` and `temperature` as
      configurable fields, so downstream code can override them per-invocation:

          chain.with_config(configurable={"temperature": 0.2}).invoke(...)

      This is the pattern mandated by CLAUDE.md §6: never hardcode a single
      ChatModel deep inside a chain. The factory exists so chains depend on the
      *interface* (a Runnable), not on `ChatOpenAI` specifically.

      Args:
          model: Provider-prefixed model id. Defaults to `settings.DEFAULT_MODEL`.
          temperature: Sampling temperature. Defaults to `settings.DEFAULT_TEMPERATURE`
              (0.0 — extraction is the primary use case and is not creative).

      Returns:
          A configurable Runnable wrapping the underlying ChatModel.
    """
    if model is None:
        model = settings.DEFAULT_MODEL
    
    if temperature is None:
        temperature = settings.DEFAULT_TEMPERATURE

    llm = init_chat_model(model=model, temperature=temperature)
    return llm.configurable_fields(
        model=ConfigurableField(id="model"),
        temperature=ConfigurableField(id="temperature")
    )

