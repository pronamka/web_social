import re
from collections import Counter
from ast import literal_eval
from typing import Union, Generator

from server.database import DataBase


class EditsBuilder:
    """Class for building corrections for misspelled words."""

    alphabets = {'en': 'abcdefghijklmnopqrstuvwxyz'}

    def __init__(self, word: str, language: str = 'en'):
        self.splits = self._build_splits(word)
        self.language = language

    def all_edits(self) -> set:
        """General method for gathering all possible corrections together."""
        deletes = self._build_deletes()
        transposes = self._build_transposes()
        replaces = self._build_replaces()
        inserts = self._build_inserts()
        return set(deletes + transposes + replaces + inserts)

    def _build_deletes(self) -> list:
        """Build corrections by deleting a symbol in each position.
        The amount of correction will be equal to the length of the given word."""
        return [L + R[1:] for L, R in self.splits if R]

    def _build_transposes(self) -> list:
        """Build corrections by moving a letter one symbol right.
        The amount of correction will be equal to the length of the given word minus one."""
        return [L + R[1] + R[0] + R[2:] for L, R in self.splits if len(R) > 1]

    def _build_replaces(self) -> list:
        """Build corrections by replacing each symbol with each letter of the chosen
        alphabet. The amount of corrections will be equal to the
        word's length multiplied by the amount of letters in the chosen alphabet."""
        return [L + c + R[1:] for L, R in self.splits
                if R for c in self.alphabets.get(self.language)]

    def _build_inserts(self) -> list:
        """Build corrections by inserting each letter of the chosen alphabet
        after each symbol in the given word. The amount of correction will be equal
        to (word's length + 1) multiplied by the amount of letters in the chosen alphabet."""
        return [L + c + R for L, R in self.splits for c in
                self.alphabets.get(self.language)]

    @staticmethod
    def _build_splits(word: str) -> list:
        """Build all possible splits for the given word (it is needed not to
        split the word every time any correction is built). The amount of splits
        will be equal to the word's length + 1.
        For example splits for the word `arm`:
                [(``, `arm`), (`a`, `rm`), (`ar`, `m`), (`arm`, ``)]:"""
        return [(word[:i], word[i:]) for i in range(len(word) + 1)]


class SpellingCorrector:
    """Class for correcting spelling mistakes in the
    words. It does not build the corrections, it decides which
    corrections are more accurate and should be given as the result."""

    def __init__(self) -> None:
        self.all_words = Counter(self._get_all_words())
        self.words_amount = sum(self.all_words.values())

    def edit_spelling(self, word: str) -> str:
        """Get most probable spelling correction for word."""
        return max(self._get_candidates(word), key=self.calculate_probability)

    def _get_candidates(self, word: str) -> set:
        """Generate possible spelling corrections for word."""
        return self.known([word]) or self.known(self.build_simple_edits(word)) or \
            self.known(self.build_complex_edits(word)) or [word]

    def known(self, words: Union[list, set, Generator]) -> set:
        """Get the subset of `words` that appear in the dictionary of all words."""
        return set(w for w in words if w in self.all_words)

    def calculate_probability(self, word: str) -> float:
        """Probability of `word`. It depends on how many times the
        word appears in the file with all the words."""
        return self.all_words[word] / self.words_amount

    @staticmethod
    def build_simple_edits(word: str) -> set:
        """Get all edits that are one edit away from `word`."""
        return EditsBuilder(word, 'en').all_edits()

    def build_complex_edits(self, word: str) -> Generator:
        """Get all edits that are two edits away from `word`."""
        res = (e2 for e1 in self.build_simple_edits(word)
               for e2 in self.build_simple_edits(e1))
        return res

    @staticmethod
    def _get_all_words() -> list:
        """Find all words in the file that contains the words. (big.txt)"""
        return re.findall(r'\w+', open('testing/words.txt', mode='r').read())


class Searcher:
    """Class for searching articles."""

    search_request = "SELECT post_id, tags, raw_text FROM posts WHERE (raw_text LIKE " \
                     "'{}' OR title LIKE '{}') AND verified=1"
    corrector = SpellingCorrector()
    database = DataBase()

    @classmethod
    def _search_one(cls, query: str, limit: int = 5) -> list:
        """Search database with ONE word. If the initial request contains
        many words, they should be split and passed one by one to this method.
        :param query: the word that should be searched.
        :param limit: the amount of results needed.
        :returns: a list with the results, sorted by quantity of the word appearances."""
        sql_query = '%' + query + '%'  # wildcard tells sqlite that any symbols can be before or after the word
        res = cls.database.get_all(cls.search_request.format(sql_query, sql_query))
        if not res:
            return []
        res = {i[0]: (i[1], cls._count_appearances(query, i[2])) for i in res}
        res = sorted(res.items(), key=lambda x: x[1][1], reverse=True)
        return [i for i in res[:limit]]

    @staticmethod
    def _count_appearances(word: str, text: str) -> int:
        """Count how many times the  word appears in the text."""
        count = 0
        for i in text.split():
            if word in i:
                count += 1
        return count

    @classmethod
    def search(cls, query: str, limit: int = 5, start_with: int = 0,
               strictly: bool = False, interests: dict = None) -> tuple:
        """General function for searching an article in the database.
        :param query: a string with that should be searched.
        :param limit: how many results are needed.
        :param start_with: how many results that come first should be offset.
        :param strictly: flag for indicating if the words' spelling should be corrected.
        :param interests: interests of a user, that made the request. They can be
                          compared with the post tags to get the most accurate results.
        :returns: a tuple of two: a list with chosen post ids; the request, formatted
                  by spelling corrector."""
        modified_request = ''
        results = []
        for i in words if (words := query.split(' ')) and strictly else cls._get_corrections(words):
            modified_request += i + ' '
            results += cls._search_one(i, limit + start_with)
        best_results = [i[0] for i in Counter(results).most_common(start_with + limit)[start_with:]]
        return cls.calculate_search_score(interests, best_results), modified_request.strip()

    @classmethod
    def calculate_search_score(cls, user_interests: dict, posts: list) -> list:
        """Calculate how many points each post, fetched earlier, gets,
        depending on the amount of word appearances it has, and it's tags similarity
        to the user interests."""
        res = {i[0]: 0 for i in posts}
        points_for_words = 10**(len(str(posts[0][1][1]))-1)
        for i in posts:
            if i[1][0]:
                res[i[0]] = cls.compare_with_interests(user_interests, literal_eval(i[1][0]))
            res[i[0]] += i[1][1]/points_for_words
        return [i[0] for i in sorted(res.items(), key=lambda x: x[1], reverse=True)]

    @classmethod
    def compare_with_interests(cls, user_interests: dict, post_tags: dict, points: int = 1) -> int:
        """Compare the post tags to user interests. For the least specific tags one point is
        given for each overlap, for the next nesting level
        two points for each overlap and so on."""
        score = 0
        for i in post_tags.keys():
            if i in user_interests:
                score += cls.compare_with_interests(user_interests[i], post_tags[i], points + 1) + points
        return score

    @classmethod
    def _get_corrections(cls, words: list) -> str:
        """Build correction for each word from a given list."""
        for i in words:
            yield cls.corrector.edit_spelling(i)
