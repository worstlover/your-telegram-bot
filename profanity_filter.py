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
    
    def __init__(self, file_path: str = "data/profanity_words.json"):
        self.file_path = file_path
        self.profanity_words = self._load_profanity_words()
        self._compile_patterns()
        
    def _load_profanity_words(self) -> Dict[str, List[str]]:
        """Load profanity words from JSON file"""
        profanity_file = Path(self.file_path)
        
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
                "لعنتی", "بیناموس", "هرزه", "پدرسگ", "مادرجنده", "خارکسده", "کوسکش", "حرامزاده", "کسخل"
            ]
        }
        
        try:
            Path("data").mkdir(exist_ok=True) # Ensure data directory exists
            if profanity_file.exists():
                with open(profanity_file, 'r', encoding='utf-8') as f:
                    words = json.load(f)
                    # Merge default with loaded to ensure all languages exist
                    for lang, default_list in default_words.items():
                        if lang not in words:
                            words[lang] = default_list
                        else: # Add any new default words that might be missing in loaded file
                            for word in default_list:
                                if word not in words[lang]:
                                    words[lang].append(word)
                    return words
            else:
                self._save_profanity_words(default_words) # Save defaults if file doesn't exist
                return default_words
        except Exception as e:
            logger.error(f"Error loading profanity words: {e}. Using default words.")
            return default_words

    def _compile_patterns(self):
        """Compile regex patterns for all loaded words."""
        self.patterns = {
            "english": [],
            "persian": [],
            "persian_latin": [] # For transliterated Persian words
        }
        
        # English words
        for word in self.profanity_words.get("english", []):
            self.patterns["english"].append(re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE))
        
        # Persian words (Arabic script)
        for word in self.profanity_words.get("persian", []):
            # Match exact word or partial matches for common suffixes/prefixes
            self.patterns["persian"].append(re.compile(r'\b' + re.escape(word), re.IGNORECASE))
            self.patterns["persian"].append(re.compile(re.escape(word) + r'\b', re.IGNORECASE))
            self.patterns["persian"].append(re.compile(re.escape(word), re.IGNORECASE)) # General match

            # Add common transliterations
            if word == "کیر":
                self.patterns["persian_latin"].append(re.compile(r'\b(kir|keer|kyr)\b', re.IGNORECASE))
            elif word == "کس":
                self.patterns["persian_latin"].append(re.compile(r'\b(kos|koss|khas)\b', re.IGNORECASE))
            elif word == "جنده":
                self.patterns["persian_latin"].append(re.compile(r'\b(jende|jande|jandeh)\b', re.IGNORECASE))
            elif word == "لاشی":
                self.patterns["persian_latin"].append(re.compile(r'\b(lashi|lashy)\b', re.IGNORECASE))
            elif word == "حرومزاده":
                self.patterns["persian_latin"].append(re.compile(r'\b(haroomzadeh|harumzadeh)\b', re.IGNORECASE))
            elif word == "کونی":
                self.patterns["persian_latin"].append(re.compile(r'\b(kooni|kuni)\b', re.IGNORECASE))
            # Add more as needed for common transliterations
            
    def contains_profanity(self, text: str) -> Tuple[bool, List[str]]:
        """Check if text contains profanity."""
        found_words = []
        
        # Check English patterns
        for pattern in self.patterns["english"]:
            if pattern.search(text):
                found_words.append(pattern.search(text).group(0))
        
        # Check Persian patterns
        for pattern in self.patterns["persian"]:
            if pattern.search(text):
                found_words.append(pattern.search(text).group(0))

        # Check Persian-Latin transliteration patterns
        for pattern in self.patterns["persian_latin"]:
            if pattern.search(text):
                found_words.append(pattern.search(text).group(0))
                
        return len(found_words) > 0, list(set(found_words)) # Return unique found words
    
    def replace_profanity(self, text: str, replace_char: str = '*') -> str:
        """Replace profanity with a specified character."""
        filtered_text = text
        
        for pattern in self.patterns["english"]:
            filtered_text = pattern.sub(lambda m: replace_char * len(m.group(0)), filtered_text)
            
        for pattern in self.patterns["persian"]:
             filtered_text = pattern.sub(lambda m: replace_char * len(m.group(0)), filtered_text)

        for pattern in self.patterns["persian_latin"]:
            filtered_text = pattern.sub(lambda m: replace_char * len(m.group(0)), filtered_text)
        
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
        high_severity_words = ['fuck', 'کیر', 'کس', 'jende', 'kir', 'kos', 'حرامزاده', 'کوسکش']
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
                self._save_profanity_words(self.profanity_words)
                logger.info(f"Added new profanity word: '{word}' to '{language}' list.")
            else:
                logger.info(f"Word '{word}' already exists in '{language}' list.")
        else:
            logger.warning(f"Language '{language}' not found in profanity word lists.")
    
    def remove_word(self, word: str, language: str) -> bool:
        """Remove a profanity word from the list"""
        if language in self.profanity_words:
            if word in self.profanity_words[language]:
                self.profanity_words[language].remove(word)
                self._compile_patterns()
                self._save_profanity_words(self.profanity_words)
                logger.info(f"Removed profanity word: '{word}' from '{language}' list.")
                return True
            else:
                logger.info(f"Word '{word}' not found in '{language}' list.")
                return False
        else:
            logger.warning(f"Language '{language}' not found in profanity word lists.")
            return False

    def _save_profanity_words(self, words_to_save: Dict[str, List[str]]):
        """Save profanity words to file"""
        try:
            Path("data").mkdir(exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(words_to_save, f, ensure_ascii=False, indent=4)
            logger.info(f"Profanity words saved to {self.file_path}")
        except Exception as e:
            logger.error(f"Error saving profanity words: {e}")