#!/usr/bin/env python3
"""Source registry. Every URL here was verified live on 2026-09-10.
Adding a source = one line. Removing = delete the line. Nothing else to touch."""

# slug, display name, feed url, group
FEEDS = [
    ("interconnects", "Interconnects",      "https://www.interconnects.ai/feed",                 "newsletter"),
    ("aheadofai",     "Ahead of AI",        "https://magazine.sebastianraschka.com/feed",        "newsletter"),
    ("importai",      "Import AI",          "https://importai.substack.com/feed",                "newsletter"),

    ("openai",        "OpenAI",             "https://openai.com/news/rss.xml",                   "lab"),
    ("deepmind",      "Google DeepMind",    "https://deepmind.google/blog/rss.xml",              "lab"),
    ("googleresearch","Google Research",    "https://research.google/blog/rss/",                 "lab"),
    ("googleai",      "Google AI",          "https://blog.google/technology/ai/rss/",            "lab"),
    ("appleml",       "Apple ML",           "https://machinelearning.apple.com/rss.xml",         "lab"),
    ("msresearch",    "Microsoft Research", "https://www.microsoft.com/en-us/research/feed/",    "lab"),
    ("amazonscience", "Amazon Science",     "https://www.amazon.science/index.rss",              "lab"),
    ("nvidiadev",     "NVIDIA Developer",   "https://developer.nvidia.com/blog/feed",            "lab"),
    ("nvidiablog",    "NVIDIA Blog",        "https://blogs.nvidia.com/feed/",                    "lab"),
    ("hfblog",        "Hugging Face",       "https://huggingface.co/blog/feed.xml",              "lab"),

    ("metaeng",       "Meta Engineering",   "https://engineering.fb.com/feed/",                  "eng"),
    ("netflixtech",   "Netflix Tech",       "https://netflixtechblog.com/feed",                  "eng"),
    ("kakaotech",     "Kakao Tech",         "https://tech.kakao.com/feed/",                      "eng"),
    ("naverd2",       "NAVER D2",           "https://d2.naver.com/d2.atom",                      "eng"),
    ("lytech",        "LY Tech",            "https://techblog.lycorp.co.jp/en/feed/index.xml",   "eng"),
]

HF_DAILY = "https://huggingface.co/api/daily_papers"
HF_PAPER = "https://huggingface.co/api/papers/{id}"

# how long we KEEP items in the json store (display windows are smaller, set in index.html)
KEEP_DAYS_PAPERS  = 21
KEEP_DAYS_ARTICLES = 60
