"""
import paramiko
import os
import sys

ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_client.connect(
    hostname="127.0.0.1",
    port=12305,
    username="root",
    password="0",
    timeout=15
)
print("SSH is runing")

stdin, stdout, stderr = ssh_client.exec_command("rpm -qa | grep net-tools")
result = stdout.read().decode().replace("\r", "").replace("\t", "").replace(" ", "")

port_list = [12305, 12306, 12307, 12308]
for port in port_list:
    stdin, stdout, stderr = ssh_client.exec_command("netstat -tunlp | grep %s" % port)
    result = stderr.read().decode()
    if "bash: netstat" in result:
        print("未安装net-tools")
    else:
        if len(stdout.read().decode()) == 0:
            print("[%s]端口未被监听" % port)
        else:
            print("[%s]端口已被监听" % port)

ssh_client.close()
"""

"""
import random
import string

# creating uuid
ascii_lowercase, number = "abcdef", "1234567890"
uuid = []
for i in range(9):
    uuid.append(random.choice(ascii_lowercase + ascii_lowercase + number))
uuid = "".join(uuid)

print(uuid)
"""

import datetime

data = [{'测试组二': [[{'host_id': 2, 'ip_status': 1, 'ssh_status': 1, 'cpu_proportion': None, 'memory_proportion': None, 'disk_proportion': None, 'ports_info': None, 'created': datetime.datetime(2023, 6, 15, 21, 5, 13), 'uuid': '8a46d', 'ip_addr': '192.168.1.1', 'nickname': '备注名称2'}], [{'host_id': 3, 'ip_status': 0, 'ssh_status': 0, 'cpu_proportion': '1.0', 'memory_proportion': '47.0', 'disk_proportion': 41, 'ports_info': [{'port': 12305, 'status': 'listen'}, {'port': 12306, 'status': 'listen'}, {'port': 12307, 'status': 'closed'}, {'port': 12308, 'status': 'listen'}], 'created': datetime.datetime(2023, 6, 15, 21, 5, 14), 'uuid': 'c56ae', 'ip_addr': '127.0.0.1', 'nickname': '备注名称3'}]]}, {'测试组一': [[{'host_id': 1, 'ip_status': 0, 'ssh_status': 0, 'cpu_proportion': '1.0', 'memory_proportion': '47.0', 'disk_proportion': 41, 'ports_info': [{'port': 80, 'status': 'closed'}, {'port': 445, 'status': 'closed'}, {'port': 12305, 'status': 'listen'}], 'created': datetime.datetime(2023, 6, 15, 21, 5, 13), 'uuid': 'd7acb', 'ip_addr': '10.0.2.15', 'nickname': '备注名称1'}]]}]
for info in data:
    print(data.index(info))