"""
设备监控
"""

import os
import sys
import re
import datetime
import json

import yaml
import pymysql
import redis
import paramiko


# 自定义日志
def Myprint(info, grade=0):
    nowDate = lambda : datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if grade == 0:
        content = "[%s] info %s" % (nowDate(), info)
    elif grade == 1:
        content = "[%s] error %s" % (nowDate(), info)
    elif grade == 2:
        content = "[%s] warning %s" % (nowDate(), info)
    else:
        content = "[%s] unkonw %s" % (nowDate(), info)
    log_dir = os.path.join(os.path.join(os.path.split(os.path.abspath(__file__))[0], "log"), "monitor.log")
    log = content + '\n'
    print(content)
    with open(log_dir, 'a+') as f:
        f.write(log)


class Monitor(object):
    def __init__(self) -> None:
        config_path = os.path.join(sys.path[0], "config.yaml")
        try:
            f = open(config_path, "r")
            self.config = yaml.load(f.read(), Loader=yaml.FullLoader)
        except FileNotFoundError:
            Myprint(grade=1, info="The configuration file does not exist. Please checking %s." % config_path)
            sys.exit()
        except yaml.scanner.ScannerError:
            Myprint(grade=1, info="The configuration file format is incorrect. Please note that it is in JSON format.")
            sys.exit()
        except Exception as err:
            Myprint(grade=1, info = "Unknown critical error. %s" % err)
        # 读取配置文件

        try:
            self.db = pymysql.connect(
                host=str(self.config.get("mysql_server").get("host")),
                port=int(self.config.get("mysql_server").get("port")),
                user=str(self.config.get("mysql_server").get("username")),
                password=str(self.config.get("mysql_server").get("password")),
                database=str(self.config.get("mysql_server").get("database")),
                charset=str(self.config.get("mysql_server").get("charset"))
            )
            self.cursor = self.db.cursor()
        except pymysql.err.OperationalError as err:
            if "Can't connect to MySQL" in str(err):
                info = "Mysql server is faild or not running."
            elif "Unknown database" in str(err):
                info = "Database 'monitor' does not exist ."
            Myprint(grade=1, info=info)
            sys.exit()
        # 连接MySQL

        try:
            self.redis_db = redis.Redis(
                host=str(self.config.get("redis_server").get("host")),
                port=int(self.config.get("redis_server").get("port")),
                password=str(self.config.get("redis_server").get("password")),
                db = int(self.config.get("redis_server").get("db"))
            )
            self.redis_db.get("key*")
        except redis.exceptions.ResponseError as err:
            if "username-password pair" in str(err):
                Myprint(grade=1, info="Redis server username or password is faild.")
            sys.exit()
        # 连接redis

    def get_connection(self):
        sql = "SELECT `id`, `ip_addr`,`port`,`username`,`password`,`listen_ports` FROM connect_info WHERE `is_true` = 0;"
        self.cursor.execute(sql)
        # 获取用户配置的服务器连接信息
        connection_list = []
        for connection in self.cursor.fetchall():
            ports = []
            for port in connection[5].split(","):
                ports.append(int(port))
            connection_list.append(
                {
                    "id": connection[0],
                    "host": connection[1],
                    "port": connection[2],
                    "username": connection[3],
                    "password": connection[4],
                    "ports": ports,
                }
            )
        # 端口信息规范化，字符串转换为列表操作

        return connection_list

    def base_info(self, id, host, port, username, password, port_list):
        """探测服务器基本信息，IP，CPU，内存，磁盘，端口"""
        
        host_status_source = os.popen("ping %s -c4" % host).read()
        try:
            response = re.findall("(\d+) packets transmitted, (\d+) received, (\d+)% packet loss, time (\d+)ms", host_status_source)[0]
            if int(response[2]) < 1:
                ip = 0
            else:
                ip = 1
                cpu = "-"
                memory = "-"
                disk_info = "-"
                port_info = "-"
        except IndexError:
            ip = 1
            cpu = "-"
            memory = "-"
            disk_info = "-"
            port_info = "-"
        # ping对方主机，判断IP是否存活

        try:
            # login remote linux server
            # print(host, port, username, password)
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
            ssh_client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=15
            )

            ssh_status = "runing"
            # 连接SSH服务，定义SSH状态，runing和faild

            stdin, stdout, stderr = ssh_client.exec_command("cat /proc/loadavg")
            # 执行shell命令
            cpu_response = stdout.read().decode()
            # 转换返回信息，用于读取和分析
            cpu_usage_rate = re.findall("(\d+)/(\d+)", cpu_response)[0]
            # 分析返回信息中的数据
            count_cpu = int(cpu_usage_rate[1])
            # CPU的总进程数
            used_cpu = int(cpu_usage_rate[0])
            # CPU的正在运行的进程数
            proportion = str(round(int(cpu_usage_rate[0])/int(cpu_usage_rate[1]), 2) * 100)
            cpu = {"count_cpu": count_cpu, "used_cpu": used_cpu, "proportion": proportion}
            # 将规范后的数据载入PYTHON对象

            stdin, stdout, stderr = ssh_client.exec_command("free -k")
            # 执行shell
            memory_response = stdout.read().decode()
            # 转换返回信息
            memory = re.findall("Mem:.*?(\d+).*?(\d+)", memory_response)[0]
            # 分析返回信息
            count_memory = int(memory[0])
            # 总内存数
            used_memory = int(memory[1])
            # 占用内存数
            proportion = str(round(used_memory/count_memory, 2) * 100)
            # 百分比转换
            memory = {"count_memory": count_memory, "used_memory": used_memory, "proportion": proportion}
            # 将规范后的数据载入PYTHON对象

            stdin, stdout, stderr = ssh_client.exec_command("df -Hk")
            # 执行shell
            disk_response = stdout.read().decode()
            # 转换返回信息
            disk_response = re.findall("(.*?)\s+(\d+).*?(\d+).*?(\d+).*?(\d+%)", disk_response)
            # 分析返回信息

            disk_info_list = []
            count_disk = 0
            used_disk = 0
            for info in disk_response:
                count_disk += int(info[1])
                used_disk += int(info[2])
                disk_info_list.append(
                    {
                        "path": info[0],
                        "count_disk": int(info[1]),
                        "used_disk": int(info[2]),
                        "not_used_disk": int(info[3]),
                        "proportion": info[4]
                    }
                )
            # 遍历获取的各路径信息，规范化后载入PYTHON对象
            proportion = str(round(int(used_disk) / int(count_disk), 2) * 100)
            # 百分比计算
            disk_info = {"count_disk": count_disk, "used_disk": used_disk, "proportion": proportion, "info": disk_info_list}
            # 载入大字典

            port_info_list = []
            for port in port_list:
                stdin, stdout, stderr = ssh_client.exec_command("rpm -qa | grep net-tools")
                # 探测是否安装net-tools
                if stdout is None:
                    sftp = paramiko.Transport(sock=(host, port))
                    # 创建SFTP对象
                    sftp.connect(username=username, password=password)
                    # 连接SFTP
                    rpm = paramiko.SFTPClient.from_transport(sftp)
                    # 本地包转换为字节表示
                    rpm_file = os.path.join(os.path.join(os.path.join(sys.path[0], "base"), "rpms"), "net-tools-2.0-0.25.20131004git.el7.x86_64.rpm")
                    # 将本地包载入字节对象
                    rpm.put(rpm_file, "/root/")
                    # 用sftp推送包到对方服务器
                    sftp.close()
                    # 关闭SFTP连接，避免占用性能
                    stdin, stdout, stderr = ssh_client.exec_command("rpm -ivh /root/net-tools-2.0-0.25.20131004git.el7.x86_64.rpm")
                    # 安装net-tools
                    stdin, stdout, stderr = ssh_client.exec_command("rm -rf /root/net-tools-2.0-0.25.20131004git.el7.x86_64.rpm")
                    # 删除上传的包
                stdin, stdout, stderr = ssh_client.exec_command("netstat -tunlp | grep %s" % port)
                # 查看端口占用情况
                port_response = stdout.read().decode()
                if port_response:
                    port_info_list.append({"port": port, "status": "listen"})
                else:
                    port_info_list.append({"port": port, "status": "closed"})
                # 规范化数据字典
            port_info = port_info_list
            # 重载

        except paramiko.ssh_exception.AuthenticationException:
            ip = 0
            ssh_status = "failed"
            cpu = "-"
            memory = "-"
            disk_info = "-"
            port_info = "-"
        # IP正常通信，SSH连接失败，所有信息为空

        except paramiko.ssh_exception.NoValidConnectionsError:
            ip = 1
            ssh_status = "failed"
            cpu = "-"
            memory = "-"
            disk_info = "-"
            port_info = "-"
        # SSH模块加载失败

        finally:
            try:
                ssh_client.close()
            except Exception:
                pass
        # 无论上述代码怎么运行，必须关闭SSH连接，减少性能开销

        return {
            "id": id,
            "IP": ip,
            "ssh_status": ssh_status,
            "cpu": cpu,
            "memory": memory,
            "disk": disk_info,
            "port_info": port_info
        }
        # 返回检测的信息

    def info_save(self, data):
        """保存历史信息"""
        sql = "INSERT INTO server_info(`host_id`,`ip_status`,`ssh_status`,`cpu_used`,`cpu_count`,`cpu_proportion`,`memory_count`,`memory_used`,`memory_proportion`,`disk_count`,`disk_used`,`disk_proportion`,`disk_detail`,`ports_info`) VALUE (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);"
        if data.get("ssh_status") == "failed":
            ssh_status = 1
        else:
            ssh_status = 0
        try:
            disk_info = json.dumps(data.get("disk").get("info"))
            port_info = json.dumps(data.get("port_info"))
        except AttributeError:
            disk_info = port_info = None
        try:
            data = [
                int(data.get("id")),
                int(data.get("IP")),
                int(ssh_status),
                int(data.get("cpu").get("used_cpu")),
                int(data.get("cpu").get("count_cpu")),
                str(data.get("cpu").get("proportion")),
                int(data.get("memory").get("count_memory")),
                int(data.get("memory").get("used_memory")),
                str(data.get("memory").get("proportion")),
                int(data.get("disk").get("count_disk")),
                int(data.get("disk").get("used_disk")),
                str(data.get("disk").get("proportion")),
                disk_info,
                port_info
            ]
            # 规范数据类型，避免入库因数据类型报bug
        except AttributeError:
            data = [
                int(data.get("id")),
                int(data.get("IP")),
                int(ssh_status),
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None
            ]
        # 规范数据入库

        try:
            self.cursor.execute(sql, data)
            
            # Correct self growth value
            sql = "SELECT COUNT(*) FROM server_info;"
            self.cursor.execute(sql)
            sql = "ALTER TABLE server_info auto_increment = %s;" % str(int(self.cursor.fetchone()[0]) + 1)
            self.cursor.execute(sql)
            self.db.commit()
            # 重载自增长值，避免ID过大出现空符，占用索引，避免增加MySQL负担
        except FileExistsError:
            pass
        return 0

    def main(self):
        """主程序"""
        connection_list = self.get_connection()
        base_info_list = []
        for connection in connection_list:
            Myprint(info="Starting detection server %s..." % str(connection.get("host")))
            base_info_list.append(self.base_info(
                id=int(connection.get("id")),
                host=str(connection.get("host")),
                port=int(connection.get("port")),
                username=str(connection.get("username")),
                password=str(connection.get("password")),
                port_list=list(connection.get("ports"))
            ))
            Myprint(info="Server detection completed %s..." % str(connection.get("host")))
        # 遍历连接配置，调用检测模块，连接每台服务器做检测并返回检测数据

        for item in base_info_list:
            if self.info_save(data=item) == 0:
                pass
            else:
                Myprint(grade=1, info="Server detection faild %s" % str(connection.get("host")))
        # 调用保存模块，保存历史信息

    def __del__(self):
        try:
            self.cursor.close()
            self.db.close()
        except Exception:
            pass
        # 断开MySQL连接

        try:
            self.redis_db.close()
        except Exception:
            pass
        # 断开redis连接

if __name__ == "__main__":
    monitor = Monitor()
    monitor.main()
    # 程序主入口，调用调度器索引，运行程序