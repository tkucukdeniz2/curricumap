"""Classic NLP baselines, trained or prompted only with what the taxonomy author had:
the labelled official programme titles (source) or the domain definitions.

Systems:
  string_1nn     rapidfuzz token-set similarity; label of the most similar official title
                 (ties broken by the plain ratio, then list order)
  charngram_lr   TF-IDF character 2-5-grams + logistic regression trained on official titles
  e5_zeroshot    multilingual-e5-large; domain whose definition embedding is most similar
  e5_1nn         multilingual-e5-large; label of the most similar official title embedding
"""
from __future__ import annotations

import time

import numpy as np
from rapidfuzz import fuzz, process
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from common import DOMAINS, definitions, source_courses, target_courses, write_predictions
from curricumap.taxonomy import normalize

E5 = ("intfloat/multilingual-e5-large", "3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3")


def norm(s: str) -> str:
    return normalize(s, "tr")


def domain_paragraphs() -> list[str]:
    paras = [p.strip() for p in definitions().split("\n\n")]
    by_domain = {d: next(p for p in paras if p.startswith(d + " ")) for d in DOMAINS}
    return [by_domain[d] for d in DOMAINS]


def main() -> None:
    src, tgt = source_courses(), target_courses()
    s_titles, s_labels = [norm(c["title"]) for c in src], [c["domain"] for c in src]
    t_raw = [c["title"] for c in tgt]
    t_titles = [norm(t) for t in t_raw]

    t0 = time.perf_counter()
    rows = []
    for raw, t in zip(t_raw, t_titles):
        # token_set_ratio is 100 whenever one title's words are a subset of the other's
        # ("yabancı dil 1" in "çocuklara yabancı dil öğretimi 1"), so ties are common.
        # Break them by the plain edit-distance ratio, then by list order.
        scores = process.cdist([t], s_titles, scorer=fuzz.token_set_ratio)[0]
        tied = np.flatnonzero(scores == scores.max())
        idx = max(tied, key=lambda i: fuzz.ratio(t, s_titles[i]))
        rows.append({"title": raw, "predicted": s_labels[idx],
                     "detail": f"{s_titles[idx]} ({scores[idx]:.0f}; {len(tied)} tied)"})
    write_predictions("string_1nn", 1, rows)
    print(f"string_1nn: {time.perf_counter() - t0:.3f}s")

    t0 = time.perf_counter()
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)
    clf = LogisticRegression(max_iter=5000, C=10.0)
    clf.fit(vec.fit_transform(s_titles), s_labels)
    pred = clf.predict(vec.transform(t_titles))
    write_predictions("charngram_lr", 1, [{"title": r, "predicted": p} for r, p in zip(t_raw, pred)])
    print(f"charngram_lr: {time.perf_counter() - t0:.3f}s")

    from sentence_transformers import SentenceTransformer
    t0 = time.perf_counter()
    model = SentenceTransformer(E5[0], revision=E5[1], device="cpu")
    enc = lambda xs: model.encode([f"query: {x}" for x in xs], normalize_embeddings=True,  # noqa: E731
                                  batch_size=32)
    t_emb, s_emb, d_emb = enc(t_titles), enc(s_titles), enc(domain_paragraphs())
    zs = np.argmax(t_emb @ d_emb.T, axis=1)
    write_predictions("e5_zeroshot", 1, [{"title": r, "predicted": DOMAINS[i]} for r, i in zip(t_raw, zs)])
    sim = t_emb @ s_emb.T
    nn = np.argmax(sim, axis=1)
    write_predictions("e5_1nn", 1, [{"title": r, "predicted": s_labels[i],
                                     "detail": f"{s_titles[i]} ({sim[k, i]:.3f})"}
                                    for k, (r, i) in enumerate(zip(t_raw, nn))])
    print(f"e5 (both systems, incl. model load): {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
