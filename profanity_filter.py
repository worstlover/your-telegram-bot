"""
Multi-language profanity filter for Persian, English, and Persian-Latin text
"""

import re
import json
import logging
from typing import List, Dict, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class ProfanityFilter:
    """Advanced profanity filter supporting multiple languages and scripts"""
    
    def __init__(self):
        self.profanity_words = self._load_profanity_words()
        self._compile_patterns()
        
    def _load_profanity_words(self) -> Dict[str, List[str]]:
        """Load profanity words from JSON file"""
        profanity_file = Path("data/profanity_words.json")
        
        # Default profanity words if file doesn't exist
        default_words = {
            "english": [
                "fuck", "shit", "damn", "bitch", "asshole", "bastard", "crap",
                "piss", "hell", "bloody", "stupid", "idiot", "moron", "dumb",
                "wtf", "omg", "lmao", "lol", "stfu", "gtfo", "fml", "bs"
            ],
            "persian": [
                "کیر", "کس", "جنده", "لاشی", "حرومزاده", "کونی", "گاو", "خر",
                "احمق", "مسخره", "چرت", "مزخرف", "ریدم", "گه", "عن", "کثیف",
                "لعنتی", "بیناموس", "هرزه", "پدرسگ", "مادرجنده", "خارکسده",
                "کیری", "کسکش", "جاکش", "بیشرف", "فاحشه", "روسپی"
            ],
            "persian_latin": [
                "kir", "kos", "jende", "lashi", "haramzade", "kuni", "gav", "khar",
                "ahmagh", "maskhare", "chert", "mozakhraf", "ridam", "goh", "an",
                "kasif", "lanati", "binamoos", "harze", "pedarsag", "madarjende",
                "kharkosde", "kiri", "koskesh", "jakesh", "bisharaf", "fahesha",
                "roospi", "koon", "kon", "kose", "kose nanat", "boro gmshoo",
                "gmshoo", "gomsho", "khafe sho", "khafeh sho", "shut up"
            ]
        }
        
        try:
            if profanity_file.exists():
                with open(profanity_file, 'r', encoding='utf-8') as f:
                    loaded_words = json.load(f)
                    # Merge with default words
                    for lang in default_words:
                        if lang in loaded_words:
                            # Combine and deduplicate
                            combined = list(set(default_words[lang] + loaded_words[lang]))
                            loaded_words[lang] = combined
                        else:
                            loaded_words[lang] = default_words[lang]
                    return loaded_words
        except Exception as e:
            logger.error(f"Error loading profanity words: {e}")
            
        return default_words
    
    def _compile_patterns(self):
        """Compile regex patterns for efficient matching"""
        self.patterns = {}
        
        for language, words in self.profanity_words.items():
            # Create pattern with word boundaries
            if language == "english" or language == "persian_latin":
                # For Latin scripts, use word boundaries
                pattern_words = []
                for word in words:
                    # Handle leetspeak and variations
                    word_pattern = self._create_flexible_pattern(word)
                    pattern_words.append(word_pattern)
                pattern = r'\b(?:' + '|'.join(pattern_words) + r')\b'
            else:
                # For Persian script, match whole words or parts
                pattern_words = []
                for word in words:
                    # Add word boundaries for Persian
                    pattern_words.append(re.escape(word))
                pattern = r'(?:^|\s)(?:' + '|'.join(pattern_words) + r')(?:\s|$|[^\u0600-\u06FF])'
            
            self.patterns[language] = re.compile(pattern, re.IGNORECASE | re.UNICODE)
    
    def _create_flexible_pattern(self, word: str) -> str:
        """Create flexible pattern to catch variations and leetspeak"""
        # Simple approach - just escape the word
        return re.escape(word.lower())
    
    def contains_profanity(self, text: str) -> Tuple[bool, List[str]]:
        """
        Check if text contains profanity
        Returns: (has_profanity, list_of_found_words)
        """
        if not text:
            return False, []
        
        found_words = []
        
        # Check each language pattern
        for language, pattern in self.patterns.items():
            matches = pattern.findall(text)
            if matches:
                found_words.extend([match.strip() for match in matches if match.strip()])
        
        # Additional checks for mixed scripts and creative spellings
        found_words.extend(self._check_creative_spellings(text))
        
        # Remove duplicates
        found_words = list(set(found_words))
        
        return len(found_words) > 0, found_words
    
    def _check_creative_spellings(self, text: str) -> List[str]:
        """Check for creative spellings and mixed scripts"""
        found = []
        text_lower = text.lower()
        
        # Common creative spellings and bypasses
        creative_patterns = [
            # English variations
            (r'f+u+c+k+', 'fuck'),
            (r's+h+i+t+', 'shit'),
            (r'b+i+t+c+h+', 'bitch'),
            (r'd+a+m+n+', 'damn'),
            
            # Persian-Latin variations
            (r'k+i+r+', 'kir'),
            (r'k+o+s+', 'kos'),
            (r'j+e+n+d+e+', 'jende'),
            (r'k+u+n+i+', 'kuni'),
            
            # Mixed patterns
            (r'[f]+[*@#$%]+[u]+[*@#$%]+[c]+[*@#$%]+[k]+', 'f*ck'),
            (r'[s]+[*@#$%]+[h]+[*@#$%]+[i]+[*@#$%]+[t]+', 's*it'),
        ]
        
        for pattern, word in creative_patterns:
            if re.search(pattern, text_lower):
                found.append(word)
        
        return found
    
    def filter_text(self, text: str) -> str:
        """
        Filter profanity from text by replacing with asterisks
        """
        if not text:
            return text
        
        filtered_text = text
        
        # Replace profanity in each language
        for language, pattern in self.patterns.items():
            def replace_match(match):
                word = match.group(0)
                return '*' * len(word)
            
            filtered_text = pattern.sub(replace_match, filtered_text)
        
        return filtered_text
    
    def get_severity_score(self, text: str) -> int:
        """
        Get severity score of profanity (0-10)
        0 = clean, 10 = highly inappropriate
        """
        has_profanity, found_words = self.contains_profanity(text)
        
        if not has_profanity:
            return 0
        
        # Base score
        score = len(found_words) * 2
        
        # Increase score for certain high-severity words
        high_severity_words = ['fuck', 'کیر', 'کس', 'jende', 'kir', 'kos']
        for word in found_words:
            if any(severe in word.lower() for severe in high_severity_words):
                score += 3
        
        # Cap at 10
        return min(score, 10)
    
    def add_word(self, word: str, language: str):
        """Add a new profanity word to the list"""
        if language in self.profanity_words:
            if word not in self.profanity_words[language]:
                self.profanity_words[language].append(word)
                self._compile_patterns()
                self._save_profanity_words()
    
    def _save_profanity_words(self):
        """Save profanity words to file"""
        try:
            Path("data").mkdir(exist_ok=True)
            with open("data/profanity_words.json", 'w', encoding='utf-8') as f:
                json.dump(self.profanity_words, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving profanity words: {e}")
