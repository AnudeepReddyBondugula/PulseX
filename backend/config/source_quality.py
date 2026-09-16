"""Source quality configuration.

Names must match the source names in backend.config.sources, and
"arXiv" covers every research paper. An unlisted source falls back
to a neutral score rather than being penalised.
"""

SOURCE_QUALITY_SCORES: dict[str, float] = {
    "OpenAI": 1.0,
    "Anthropic": 1.0,
    "Google AI": 1.0,
    "Google DeepMind": 1.0,
    "Microsoft Research": 1.0,
    "Meta AI": 1.0,
    "NVIDIA": 0.95,
    "Hugging Face": 0.95,
    "arXiv": 0.95,
    "MIT Technology Review AI": 0.90,
    "Ars Technica AI": 0.85,
    "TechCrunch AI": 0.80,
    "The Verge AI": 0.80,
    "VentureBeat AI": 0.80,
}
