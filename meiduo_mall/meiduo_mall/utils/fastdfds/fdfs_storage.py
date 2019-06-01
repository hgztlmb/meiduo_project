from django.core.files.storage import Storage


class FastDFSStorage(Storage):
    def _open(self, name, mode='rb'):
        pass

    def _save(self, name, content):
        pass

    def url(self, name):
        return 'http://192.168.46.129:8888/' + name
