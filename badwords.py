# badwords.py
BAD_WORDS = [
    # فارسی
    "کیر", "کص", "جنده", "کسخل", "جاکش", "کون", "لاشی", "بی‌شرف",
    # فینگلیش
    "kir", "koskesh", "kos", "koskhol", "jakesh", "koon", "lashi", "bisharaf",
    # انگلیسی
    "fuck", "shit", "bitch", "asshole", "fucker", "dick", "pussy", "bastard"
]

def contains_bad_words(text: str) -> bool:
    if not text:
        return False
    cleaned = text.lower().replace(" ", "").replace("_", "")
    for word in BAD_WORDS:
        if word in cleaned:
            return True
    return False
