def rank_prompts(results):
    return sorted(
        results,
        key=lambda r: r.evaluation.score,
        reverse=True
    )
