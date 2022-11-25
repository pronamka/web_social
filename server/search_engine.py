import re
from collections import Counter

from PyPDF2 import PdfFileReader, errors, PdfReader
from server.database import DataBase


class EditsBuilder:
    alphabets = {'en': 'abcdefghijklmnopqrstuvwxyz'}

    def __init__(self, word: str, language: str = 'en'):
        self.splits = self._build_splits(word)
        self.language = language

    def all_edits(self):
        deletes = self._build_deletes()
        transposes = self._build_transposes()
        replaces = self._build_replaces()
        inserts = self._build_inserts()
        return set(deletes + transposes + replaces + inserts)

    def _build_deletes(self) -> list:
        return [L + R[1:] for L, R in self.splits if R]

    def _build_transposes(self) -> list:
        return [L + R[1] + R[0] + R[2:] for L, R in self.splits if len(R) > 1]

    def _build_replaces(self) -> list:
        return [L + c + R[1:] for L, R in self.splits
                if R for c in self.alphabets.get(self.language)]

    def _build_inserts(self) -> list:
        return [L + c + R for L, R in self.splits for c in
                self.alphabets.get(self.language)]

    @staticmethod
    def _build_splits(word) -> list:
        return [(word[:i], word[i:]) for i in range(len(word) + 1)]


class SpellingCorrector:

    def __init__(self):
        self.all_words = Counter(self._get_all_words())
        self.words_amount = sum(self.all_words.values())

    def edit_spelling(self, word):
        """Most probable spelling correction for word."""
        return max(self._get_candidates(word), key=self.calculate_probability)

    def _get_candidates(self, word):
        """Generate possible spelling corrections for word."""
        return self.known([word]) or self.known(self.build_simple_edits(word)) or \
            self.known(self.build_complex_edits(word)) or [word]

    def known(self, words):
        """The subset of `words` that appear in the dictionary of WORDS."""
        return set(w for w in words if w in self.all_words)

    def calculate_probability(self, word):
        """Probability of `word`."""
        return self.all_words[word] / self.words_amount

    @staticmethod
    def build_simple_edits(word):
        """All edits that are one edit away from `word`."""
        return EditsBuilder(word, 'en').all_edits()

    def build_complex_edits(self, word):
        """All edits that are two edits away from `word`."""
        res = (e2 for e1 in self.build_simple_edits(word)
               for e2 in self.build_simple_edits(e1))
        return res

    @staticmethod
    def _get_all_words():
        return re.findall(r'\w+', open('testing/words.txt', mode='r').read())


class Searcher:
    search_request = "SELECT post_id, raw_text FROM posts WHERE (raw_text LIKE " \
                     "'{}' OR title LIKE '{}') AND verified=1"
    corrector = SpellingCorrector()
    database = DataBase()

    @classmethod
    def _search_one(cls, query: str, limit: int = 5) -> list:
        sql_query = '%' + query + '%'
        res = cls.database.get_all(cls.search_request.format(sql_query, sql_query))
        if not res:
            return []
        res = {i[0]: cls.count_appearances(query, i[1]) for i in res}
        res = sorted(res.items(), key=lambda x: x[1], reverse=True)
        return [i[0] for i in res[:limit]]

    @staticmethod
    def count_appearances(word, text):
        count = 0
        for i in text.split():
            if word in i:
                count += 1
        return count

    @classmethod
    def search_post(cls, query: str, limit: int = 5, start_with: int = 0, strictly: bool = False) -> tuple:
        all_words = query.split(' ')
        modified_request = ''
        results = []
        if strictly:
            for i in all_words:
                results += cls._search_one(i, limit + start_with)
            return [i[0] for i in Counter(results).most_common(start_with + limit)
                    [start_with:]], query
        for i in all_words:
            correction = cls.corrector.edit_spelling(i)
            modified_request += correction + ' '
            results += cls._search_one(correction, limit+start_with)
        return [i[0] for i in Counter(results).most_common(start_with+limit)
                [start_with:]], modified_request.strip()


def check_integrity(stream) -> bool:
    """Check if it is possible to read the file.
    If it is not, PdfReader will raise PdfReadError while initializing.
    :param stream: an instance of tempfile.SpooledTemporaryFile
    :returns: True, if the file was read successfully;
              False, if an error occurred while reading (file is corrupted)"""
    try:
        PdfReader(stream)
        return True
    except errors.PdfReadError:
        return False


def get_text(name: str) -> str:
    """Get text from a pdf file saved on disk."""
    print(name)
    doc = PdfFileReader(name)
    text = ''
    for i in doc.pages:
        try:
            text += i.extract_text()
        except TypeError as e:
            print(f'An error occurred: {e}; The piece of text will be excluded from search.')
    return text


class SearchManagerTools:
    database = DataBase(database_name='web_social_v4.db', access_level=4)

    def write_all_documents(self):
        all_articles = self.database.get_all('SELECT post_id, title FROM posts')
        excluded_files = []
        for i in all_articles:
            try:
                text = get_text(i[1]).replace('"', '')
                text = text.replace(chr(0), '')
                self.database.update(f'''UPDATE posts SET text=QUOTE("{text}") WHERE post_id={i[0]}''')
            except errors.PdfReadError:
                excluded_files.append(i)
                print('File corrupted: ' + i[1])
                self.database.update(f'UPDATE posts SET verified=3 WHERE post_id={i[0]}')
        print(excluded_files)


if __name__ == '__main__':
    searcher = Searcher()
    while True:
        print(searcher.search_post(input('Search: '), 10))
