from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client
from tiantian import settings
import os
# 自定义存储类
class FDFSStorage(Storage):
    def __init__(self, client_conf=None, nginx_url=None):
        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF

        self.client_conf = client_conf

        if nginx_url is None:
            nginx_url = settings.FDFS_NGINX_URL

        self.nginx_url = nginx_url
    # 保存文件
    def _save(self, name, content):
        client = Fdfs_client(self.client_conf)
        # 获取文件内容
        file_content = content.read()
        cont = client.upload_by_buffer(file_content)

        if cont is None or cont.get('Status') != 'Upload successed.':
            raise Exception('上传文件失败！')
        # file_id = cont['Remote file_id']
        file_id = cont.get('Remote file_id')
        return file_id
    # 判断文件是否重复
    def exists(self,name):
        return False

    # 返回可访问文件地址
    def url(self,name):
        return self.nginx_url + name




