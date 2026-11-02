import time
from duckduckgo_search import DDGS


def search_external(query: str) -> dict:
    """Busca informações e imagens na web."""
    try:
        # Pausa de 1,5 segundos para tentar enganar o bloqueio do DuckDuckGo
        time.sleep(1.5)

        results = []
        with DDGS() as ddgs:
            # Busca as 6 primeiras imagens
            for r in ddgs.images(query, max_results=6):
                results.append(
                    {
                        "title": r.get("title"),
                        "image_url": r.get("image"),
                        "thumbnail": r.get("thumbnail"),
                    }
                )

        if results:
            return {"ok": True, "results": results}

        return {"ok": False, "message": "Nenhuma imagem encontrada para este modelo."}

    except Exception as e:
        erro_str = str(e).lower()
        # Se for erro de limite de busca (Ratelimit)
        if "ratelimit" in erro_str or "202" in erro_str:
            return {
                "ok": False,
                "message": "O buscador bloqueou temporariamente as buscas. Aguarde 2 minutos e tente novamente.",
            }

        return {"ok": False, "message": f"Erro na busca: {e}"}
