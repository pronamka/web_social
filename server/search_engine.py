from PyPDF2 import PdfFileReader, errors, PdfReader

from server.database import DataBase

search_request = "SELECT post_id, raw_text FROM posts WHERE (raw_text LIKE " \
                 "'{}' OR title LIKE '{}') AND verified=1"


def search_post(query: str, limit: int = 5) -> list:
    query = '%' + query + '%'
    res = DataBase(database_name='web_social_v4.db').get_all("SELECT post_id, raw_text FROM posts WHERE (raw_text LIKE '{}' OR title LIKE '{}')".format(query, query))
    if not res:
        return []
    res = {i[0]: i[1].count(query) for i in res}
    res = sorted(res.items(), key=lambda x: x[1], reverse=True)
    print(res[:limit])
    return [i[0] for i in res[:limit]]


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
    while True:
        print(search_post(input('Search: '), 10))
