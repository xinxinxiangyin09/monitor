import paramiko
import os
import sys
import telnetlib

"""
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

