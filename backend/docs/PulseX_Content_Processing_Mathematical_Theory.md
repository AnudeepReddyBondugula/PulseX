# PulseX Content Processing — Mathematical Theory

## Purpose

This document describes the mathematical and algorithmic theory behind the deterministic processing of `ContentItem` objects in PulseX v0.1.

The processing pipeline is:

```text
ContentItem
    │
    ├── Deduplication
    │
    ├── Relevance scoring
    │
    ├── Topic extraction
    │
    └── Importance scoring / ranking
```

The goal of v0.1 is not to build a sophisticated recommendation system. The goal is to use deterministic, explainable, testable heuristics that can later be replaced or enriched by AI-based processing.

---

# 1. Mathematical notation

Let the collection of content items be:

\[
C = \{c_1,c_2,\ldots,c_n\}
\]

Each content item \(c\) has properties such as:

- title \(T(c)\)
- body text \(B(c)\)
- URL \(U(c)\)
- content hash \(H(c)\)
- source \(S(c)\)
- publication time \(t_p(c)\)

For a particular item, the processing pipeline produces:

\[
c \rightarrow
\left(
\text{duplicate},
\text{relevance},
\text{topics},
\text{importance}
\right)
\]

---

# 2. Deduplication

## 2.1 Objective

Deduplication determines whether an incoming content item has already been represented by an earlier item.

For each item we calculate three deterministic identity signals:

1. Content hash
2. Canonical URL
3. Normalized title

Let:

\[
h(c) = \text{content hash}
\]

\[
u(c) = \text{canonical URL}
\]

\[
\tau(c) = \text{normalized title}
\]

We maintain three sets containing signals from previously accepted items:

\[
H_{seen}, U_{seen}, T_{seen}
\]

An item \(c\) is considered a duplicate when:

\[
D(c) =
\begin{cases}
1 & \text{if } h(c)\in H_{seen}
\lor u(c)\in U_{seen}
\lor \tau(c)\in T_{seen}\\
0 & \text{otherwise}
\end{cases}
\]

Therefore:

\[
D(c)=1
\]

means the item is a duplicate.

Otherwise:

\[
D(c)=0
\]

means the item is unique.

---

## 2.2 Content hash

The normalizers create a deterministic SHA-256 content hash.

Conceptually, the input is:

\[
x =
T(c)
\;||\;
U(c)
\;||\;
\text{content}(c)
\]

where \(||\) means concatenation using a separator.

The hash is:

\[
H(c)=SHA256(x)
\]

SHA-256 produces a fixed-size 256-bit digest.

The purpose is deterministic identity, not semantic similarity.

Two identical normalized inputs produce the same hash:

\[
x_1=x_2 \Rightarrow SHA256(x_1)=SHA256(x_2)
\]

A different input normally produces a different digest.

---

## 2.3 URL canonicalization

Before comparing URLs, PulseX canonicalizes them.

The current normalization:

- lowercases the scheme
- lowercases the hostname
- removes default HTTP/HTTPS ports
- removes a trailing path slash
- removes URL fragments

Conceptually:

\[
u(c)=
canonicalize(U(c))
\]

For example:

```text
HTTPS://EXAMPLE.COM/article/#section
```

becomes:

```text
https://example.com/article
```

Fragments are ignored because they normally identify a location inside the same document rather than a separate article.

Query parameters are currently preserved.

Therefore:

```text
/article?id=1
```

and:

```text
/article?id=2
```

remain distinct.

---

## 2.4 Title normalization

The title normalization function is:

\[
\tau(T)=collapseWhitespace(lowercase(trim(T)))
\]

For example:

```text
"  OpenAI   Releases
A New Model  "
```

becomes:

```text
"openai releases a new model"
```

This catches exact-title duplicates where differences are only formatting or capitalization.

It deliberately does not perform semantic similarity.

Therefore:

```text
"OpenAI releases a new model"
```

and:

```text
"OpenAI announces another model"
```

are different normalized titles.

---

## 2.5 Deduplication complexity

The implementation uses sets.

For a set membership operation:

\[
x \in S
\]

the expected average complexity is:

\[
O(1)
\]

For \(n\) content items, the complete deterministic pass is approximately:

\[
O(n)
\]

This is substantially better than comparing every item against every previous item, which would approach:

\[
O(n^2)
\]

for a naive pairwise comparison.

---

## 2.6 First-occurrence policy

PulseX currently keeps the first occurrence and marks later matching items as duplicates.

Given:

```text
A, B, C
```

where:

\[
D(B)=1
\]

and:

\[
D(C)=1
\]

the first item remains in the unique set.

This is an ordering policy, not a statement that the first source is necessarily the highest-quality source.

Source preference can be incorporated later into ranking.

---

# 3. Relevance scoring

## 3.1 Objective

Relevance asks:

> How strongly does this item appear to be related to AI/ML?

The v0.1 implementation is keyword based.

Let the configured keyword set be:

\[
K=\{k_1,k_2,\ldots,k_m\}
\]

For a text \(X\), define a keyword match function:

\[
M(X,k)=
\begin{cases}
1 & \text{if keyword } k \text{ occurs in } X\\
0 & \text{otherwise}
\end{cases}
\]

Matching is case-insensitive and uses phrase/word boundaries.

---

## 3.2 Distinct keyword matching

For text \(X\), the set of matched keywords is:

\[
K_X =
\{k\in K \mid M(X,k)=1\}
\]

The implementation counts distinct matched keywords rather than total occurrences.

Let:

\[
N(X)=|K_X|
\]

Then the text relevance score is:

\[
R(X)=\min\left(\frac{N(X)}{5},1\right)
\]

The denominator 5 is the current saturation point.

Therefore:

| Distinct matched keywords | Score |
|---:|---:|
| 0 | 0.0 |
| 1 | 0.2 |
| 2 | 0.4 |
| 3 | 0.6 |
| 4 | 0.8 |
| 5 | 1.0 |
| 6+ | 1.0 |

The cap prevents keyword count from growing without bound.

---

# 4.3 Title and body relevance

For each item we calculate:

\[
R_T=R(T(c))
\]

for the title, and:

\[
R_B=R(B(c))
\]

for the body.

The body is assembled from the available descriptive content.

For articles it may include:

\[
B(c)=description+content+summary
\]

For research papers it may include:

\[
B(c)=abstract+summary
\]

The final relevance score is:

\[
R(c)=
w_T R_T+w_B R_B
\]

with the current default weights:

\[
w_T=0.7
\]

\[
w_B=0.3
\]

Therefore:

\[
R(c)=0.7R_T+0.3R_B
\]

The score is bounded:

\[
0\le R(c)\le1
\]

---

## 3.4 Example

Suppose the title contains three distinct configured keywords.

Then:

\[
R_T=\frac{3}{5}=0.6
\]

Suppose the body contains two distinct keywords:

\[
R_B=\frac{2}{5}=0.4
\]

Therefore:

\[
R(c)
=
0.7(0.6)+0.3(0.4)
\]

\[
=0.42+0.12
\]

\[
=0.54
\]

So:

\[
R(c)=0.54
\]

---

## 3.5 Relevance threshold

The current default threshold is:

\[
\theta=0.2
\]

An item is relevant when:

\[
R(c)\ge\theta
\]

and irrelevant when:

\[
R(c)<\theta
\]

Thus:

\[
Relevant(c)=
\begin{cases}
1 & R(c)\ge0.2\\
0 & R(c)<0.2
\end{cases}
\]

The threshold is configuration rather than hardcoded business logic.

---

# 4.4 Topic extraction

Topic extraction is related to relevance but is a separate operation.

Let the set of PulseX topics be:

\[
P=\{p_1,p_2,\ldots,p_r\}
\]

Each topic \(p\) has a configured keyword set:

\[
K_p
\]

A topic is assigned when at least one of its keywords matches the item's text.

Formally:

\[
TopicMatch(c,p)=
\begin{cases}
1 & \exists k\in K_p:M(X(c),k)=1\\
0 & \text{otherwise}
\end{cases}
\]

Therefore the extracted topic set is:

\[
Topics(c)=
\{p\in P\mid TopicMatch(c,p)=1\}
\]

An item can have zero, one, or multiple topics.

For example:

\[
Topics(c)=
\{
LLM,
AI\_AGENTS,
MULTIMODAL\_AI
\}
\]

Topic extraction does not assign an importance score.

---

# 4.5 Why topic matching is binary

Suppose an article contains:

```text
LLM
large language model
language model
```

The current topic classifier does not assign three LLM points.

It simply determines:

\[
TopicMatch(c,LLM)=1
\]

This prevents repeated mentions of the same concept from artificially inflating the topic representation.

Topic extraction answers:

> Does this topic apply?

It does not answer:

> How important is this topic?

---

# 5. Importance scoring

## 5.1 Objective

Importance ranking combines multiple signals into a single score:

\[
I(c)\in[0,1]
\]

The current model uses:

1. Recency
2. Relevance
3. Source quality
4. Technical/research significance

The final equation is:

\[
I(c)=
w_RR_c+
w_{rel}R_c+
w_SS_c+
w_GG_c
\]

where:

- \(R_c\) = recency score
- \(R_c\) in the relevance context = relevance score
- \(S_c\) = source quality
- \(G_c\) = significance score

To avoid ambiguity, define the relevance variable as \(Q_c\):

\[
I(c)=
w_RR_c+
w_QQ_c+
w_SS_c+
w_GG_c
\]

with current weights:

\[
w_R=0.25
\]

\[
w_Q=0.30
\]

\[
w_S=0.20
\]

\[
w_G=0.25
\]

The default weights sum to:

\[
0.25+0.30+0.20+0.25=1
\]

Therefore, if every component is in \([0,1]\):

\[
0\le I(c)\le1
\]

---

# 5.2 Recency score

Recency uses exponential decay.

Let:

\[
\Delta t
\]

be the age of the content in hours.

The current half-life is:

\[
H=48\text{ hours}
\]

The recency score is:

\[
R_c=
2^{-\Delta t/H}
\]

Equivalently:

\[
R_c=
\left(\frac12\right)^{\Delta t/H}
\]

This guarantees:

\[
R_c=1
\]

when:

\[
\Delta t=0
\]

and:

\[
R_c=0.5
\]

when:

\[
\Delta t=48
\]

hours.

---

## 5.3 Recency examples

| Age | Calculation | Score |
|---:|---|---:|
| 0 h | \(2^0\) | 1.000 |
| 24 h | \(2^{-0.5}\) | 0.707 |
| 48 h | \(2^{-1}\) | 0.500 |
| 72 h | \(2^{-1.5}\) | 0.354 |
| 96 h | \(2^{-2}\) | 0.250 |
| 144 h | \(2^{-3}\) | 0.125 |

The half-life interpretation is useful:

> Every 48 hours, the recency contribution is reduced by half.

---

# 5.4 Why exponential decay?

A linear decay such as:

\[
R=1-\frac{\Delta t}{T}
\]

has undesirable behavior:

- it reaches exactly zero at \(T\)
- it requires a hard cutoff
- small changes near the cutoff can produce large discontinuities

Exponential decay provides a smooth decline:

\[
R(\Delta t)=2^{-\Delta t/H}
\]

and never becomes exactly zero for finite \(\Delta t\).

---

# 5.5 Source quality

Each configured source has a quality score:

\[
S(c)\in[0,1]
\]

For example:

\[
S(OpenAI)=1.0
\]

\[
S(Anthropic)=1.0
\]

\[
S(NVIDIA)=0.95
\]

An unknown source currently receives:

\[
S(unknown)=0.5
\]

This is a prior about source reliability/authority.

It is not a measure of article quality.

The source score is weighted by:

\[
w_S=0.20
\]

Therefore the maximum source-quality contribution is:

\[
1.0\times0.20=0.20
\]

---

# 5.6 Significance score

The current MVP significance score is heuristic.

Let the configured high-impact title terms be:

\[
G=\{
g_1,g_2,\ldots,g_q
\}
\]

For a title \(T\), let:

\[
N_G(T)
\]

be the number of matched significance terms.

Each matched term contributes:

\[
0.2
\]

subject to a maximum contribution of:

\[
0.6
\]

Therefore:

\[
G_{title}(c)=
\min(0.2N_G(T(c)),0.6)
\]

---

## 5.7 Research-paper bonus

Research papers receive an additional:

\[
0.2
\]

Therefore, for a research paper:

\[
G(c)=
\min(G_{title}(c)+0.2,1)
\]

For an ordinary article:

\[
G(c)=G_{title}(c)
\]

This is a heuristic that reflects PulseX's emphasis on technical research.

---

## 5.8 Significance examples

For an ordinary article:

### Zero matched terms

\[
N_G=0
\]

\[
G=0
\]

### One matched term

\[
N_G=1
\]

\[
G=0.2
\]

### Two matched terms

\[
N_G=2
\]

\[
G=0.4
\]

### Three or more matched terms

\[
N_G\ge3
\]

\[
G=0.6
\]

For a research paper with three matched terms:

\[
G=\min(0.6+0.2,1)=0.8
\]

---

# 5.9 Complete importance example

Suppose an item has:

\[
R_c=0.90
\]

recency,

\[
Q_c=0.80
\]

relevance,

\[
S_c=1.00
\]

source quality, and:

\[
G_c=0.60
\]

significance.

Then:

\[
I(c)=
0.25(0.90)
+
0.30(0.80)
+
0.20(1.00)
+
0.25(0.60)
\]

Calculate each contribution:

\[
0.25(0.90)=0.225
\]

\[
0.30(0.80)=0.240
\]

\[
0.20(1.00)=0.200
\]

\[
0.25(0.60)=0.150
\]

Therefore:

\[
I(c)=0.225+0.240+0.200+0.150
\]

\[
\boxed{I(c)=0.815}
\]

So the item receives an importance score of:

```text
0.815
```

---

# 5.10 Ranking

For a set of relevant items:

\[
C_R=\{c_1,c_2,\ldots,c_k\}
\]

we calculate:

\[
I(c_i)
\]

for every item.

The ranking is then the descending ordering:

\[
I(c_{(1)})\ge
I(c_{(2)})\ge
\ldots\ge
I(c_{(k)})
\]

where \(c_{(1)}\) is the highest-ranked item.

This is not a probabilistic ranking model.

It is a deterministic ordering of scalar importance scores.

---

# 6. Complete deterministic processing equation

The complete v0.1 processing flow can be expressed as:

\[
C
\xrightarrow{D}
C_U
\]

where \(C_U\) is the unique-content set.

Then:

\[
C_U
\xrightarrow{Q}
C_R
\]

where:

\[
C_R=
\{c\in C_U\mid Q(c)\ge\theta\}
\]

For every relevant item:

\[
c\in C_R
\]

we calculate:

\[
Topics(c)
\]

and:

\[
I(c)
\]

Finally:

\[
C_R
\xrightarrow{sort(I,\ descending)}
C_{ranked}
\]

Therefore:

\[
\boxed{
C
\rightarrow
Deduplication
\rightarrow
Relevance
\rightarrow
Topics
\rightarrow
Importance
\rightarrow
Ranking
}
\]

---

# 7. Why these calculations are separated

Each mathematical signal answers a different question.

| Calculation | Question answered |
|---|---|
| Content hash | Is the normalized content identical? |
| Canonical URL | Does this point to the same document? |
| Normalized title | Is this the same title after formatting normalization? |
| Relevance score | Is this content about AI/ML? |
| Topic extraction | Which AI topics does it concern? |
| Recency score | How recent is it? |
| Source quality | How authoritative is the source? |
| Significance score | Does the title indicate potentially important content? |
| Importance score | How strongly should this item be ranked? |

This separation prevents one metric from being overloaded with multiple meanings.

---

# 8. Important limitations of the MVP model

These formulas are intentionally heuristic.

## 8.1 Keyword matching is not semantic understanding

The relevance system cannot reliably distinguish:

```text
AI as artificial intelligence
```

from every possible unrelated use of the same term.

It also cannot understand context.

---

## 8.2 Keyword count is not importance

An article containing ten AI keywords is not necessarily more important than one containing two.

Keyword count is only being used as a simple relevance signal.

---

## 8.3 Source quality is a prior

A high-quality source can publish an unimportant article.

A lower-scored source can publish an extremely important article.

Therefore:

\[
SourceQuality \neq ArticleQuality
\]

The source-quality term is only one component of the final score.

---

## 8.4 Significance is only a heuristic

Terms such as:

```text
breakthrough
new model
state-of-the-art
benchmark
launch
open source
```

are signals, not proof of significance.

The current system does not understand whether a claimed breakthrough is actually meaningful.

---

## 8.5 Deduplication is not semantic similarity

The current deduplicator catches deterministic duplicates.

It does not reliably catch:

```text
"OpenAI releases new reasoning model"
```

and:

```text
"OpenAI announces its latest reasoning system"
```

if their URLs, hashes, and normalized titles differ.

Semantic deduplication can be considered later.

---

# 9. Why this is appropriate for PulseX v0.1

The MVP is intentionally based on:

- deterministic rules
- bounded scores
- explainable calculations
- configuration
- unit-testable functions
- no external AI dependency for basic filtering/ranking

This gives us a predictable baseline.

Later, AI processing can enrich the pipeline:

```text
Deterministic processing
        ↓
AI enrichment
        ↓
better topics
better relevance
better significance
better summaries
```

The deterministic layer should remain useful even if AI services are unavailable.

---

# 10. Summary of all current formulas

## Deduplication

\[
D(c)=
\mathbf{1}
[
h(c)\in H_{seen}
\lor
u(c)\in U_{seen}
\lor
\tau(c)\in T_{seen}
]
\]

## Text relevance

\[
R(X)=
\min\left(\frac{|K_X|}{5},1\right)
\]

## Overall relevance

\[
Q(c)=
0.7R(T(c))
+
0.3R(B(c))
\]

## Relevance decision

\[
Relevant(c)=
\mathbf{1}[Q(c)\ge0.2]
\]

## Topic assignment

\[
TopicMatch(c,p)=
\mathbf{1}
[
\exists k\in K_p:M(X(c),k)=1
]
\]

## Recency

\[
R_c=
2^{-\Delta t/48}
\]

where \(\Delta t\) is measured in hours.

## Significance

For articles:

\[
G(c)=
\min(0.2N_G(T(c)),0.6)
\]

For research papers:

\[
G(c)=
\min(0.2N_G(T(c))+0.2,1)
\]

## Importance

\[
\boxed{
I(c)=
0.25R_c+
0.30Q(c)+
0.20S(c)+
0.25G(c)
}
\]

with:

\[
0\le I(c)\le1
\]

## Ranking

\[
c_i \succ c_j
\iff
I(c_i)>I(c_j)
\]

---

# 11. Future evolution

The v0.1 mathematical model is intentionally simple.

Potential future improvements include:

1. Semantic duplicate detection.
2. Embedding-based similarity.
3. Learned relevance classification.
4. AI-generated topic classification.
5. Learned source-quality priors.
6. More sophisticated temporal decay.
7. User-specific ranking.
8. Feedback-based ranking.
9. Calibrated probabilistic relevance scores.
10. Evaluation metrics such as precision, recall, F1, NDCG, and ranking correlation.

These should be introduced only after we have real PulseX data and can measure whether the additional complexity actually improves the product.
