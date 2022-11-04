from PyPDF2 import PdfFileReader, errors
import os
from txtai.embeddings import Embeddings
from server.database import DataBase

embeddings = Embeddings({"path": "sentence-transformers/all-MiniLM-L6-v2",
                             "content": True, "objects": True})
embeddings.load('static/embeddings/short_embeddings')


def _get_text(name: str):
    print(name)
    doc = PdfFileReader('static/upload_folder/' + name)
    text = ''
    for i in doc.pages:
        try:
            text += i.extract_text()
        except TypeError as e:
            print(f'An error occurred: {e}; The piece of text will be excluded from search.')
    return text


def search_post(query: str, limit: int = 10):
    result: list = embeddings.search(f'SELECT post_id FROM txtai WHERE '
                      f'SIMILAR("{query}") AND score>=0.15', limit=limit)
    return result


def add_article_to_search(title: str, post_id: int):
    embeddings.upsert([(embeddings.count(), {'post_id': post_id,
                                             'text': _get_text(title)}, None)])
    embeddings.save('static/embeddings')


def remove_article_from_search(post_id: int):
    article_id = embeddings.search(f'SELECT id FROM txtai WHERE post_id="{post_id}"')
    embeddings.delete([article_id[0].get('id')])
    embeddings.save('static/embeddings')


class SearchManagerTools:
    database = DataBase(database_name='web_social_v3.db')

    @staticmethod
    def clear_search():
        embeddings.delete([i for i in range(embeddings.count())])
        embeddings.close()
        for i in os.listdir('static/embeddings'):
            os.remove('static/embeddings/' + i)

    def write_all_documents(self):

        all_articles = self.database.get_all('SELECT post_id, title FROM posts')
        data_package = []
        excluded_files = []
        for n, i in enumerate(all_articles):
            try:
                data_package.append((n, {'post_id': i[0], 'text': _get_text(i[1])}, None))
            except errors.PdfReadError:
                excluded_files.append(i)
                print('File corrupted: ' + i[1])
                DataBase(access_level=3).update(f'UPDATE posts SET verified=3 WHERE post_id={i[0]}')
        embeddings.index(data_package)
        embeddings.save('static/embeddings')

    def write_short_embeddings(self):
        all_articles = self.database.get_all('SELECT post_id, title FROM posts')
        data_package = []
        excluded_files = []
        for n, i in enumerate(all_articles):
            if n > 40:
                break
            try:
                data_package.append((n, {'post_id': i[0], 'text': _get_text(i[1])}, None))
            except errors.PdfReadError:
                excluded_files.append(i)
                print('File corrupted: ' + i[1])
                DataBase(access_level=3).update(f'UPDATE posts SET verified=3 WHERE post_id={i[0]}')
        embeddings.index(data_package)
        embeddings.save('static/embeddings')


"""if __name__ == '__main__':
    embeddings = Embeddings({"path": "sentence-transformers/all-MiniLM-L6-v2",
                             "content": True, "objects": True})
    embeddings.load('static/embeddings')"""