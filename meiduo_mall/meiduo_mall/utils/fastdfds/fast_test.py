from fdfs_client.client import Fdfs_client

client = Fdfs_client('./client.conf')
ret = client.upload_by_filename('/home/python/Desktop/upload_Images/kk02.jpeg')
print(ret)
"""
getting connection
<fdfs_client.connection.Connection object at 0x7febb4e44e10>
<fdfs_client.fdfs_protol.Tracker_header object at 0x7febb4e44dd8>
{
'Group name': 'group1', 
'Remote file_id': 'group1/M00/00/00/wKgugVzuQ2yAZRVkAAEXU5wmjPs51.jpeg', 
'Status': 'Upload successed.', 
'Local file name': '/home/python/Desktop/upload_Images/kk02.jpeg', 
'Uploaded size': '69.00KB', 
'Storage IP': '192.168.46.129'}

"""