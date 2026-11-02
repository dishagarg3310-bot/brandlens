"""Retrieve the guideline passages and approved facts most relevant to a draft.

Only the retrieved items are shown to the AI, and the AI may cite only those
passage ids (evidence-or-silence). TF-IDF keeps this light enough for free hosting
and needs no model download, so no guideline text leaves the server for embedding.
"""


def retrieve(query, items, text_of, k=4, min_items=3):
    """Return up to k items ranked by similarity to the query, in original order.

    items   : list of dicts (guideline passages or facts)
    text_of : function returning the searchable text of one item
    min_items: if fewer than this many items match, the list is filled up so the
               AI is never left with too little context.
    If the corpus is small or anything goes wrong, all items are returned.
    """
    items = list(items)
    if len(items) <= k:
        return items
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        docs = [text_of(i) for i in items]
        matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit_transform(docs + [query])
        sims = cosine_similarity(matrix[-1], matrix[:-1]).ravel()
    except Exception:
        return items

    order = sorted(range(len(items)), key=lambda i: (-sims[i], i))
    chosen = [i for i in order if sims[i] > 0][:k]
    for i in order:
        if len(chosen) >= min(min_items, len(items)):
            break
        if i not in chosen:
            chosen.append(i)
    chosen.sort()
    return [items[i] for i in chosen]
