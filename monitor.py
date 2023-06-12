import os
import sys
import re
import datetime
import json

import yaml
import pymysql
import redis
import paramiko


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

        # connect mysql server
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

        # starting connect redis server
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

    def get_connection(self):
        sql = "SELECT `id`, `ip_addr`,`port`,`username`,`password`,`listen_ports` FROM connect_info WHERE `is_true` = 0;"
        self.cursor.execute(sql)
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
        
        return connection_list

    def base_info(self, id, host, port, username, password, port_list):
        """get server base info(ip,cpu,memory,disk,internet,port)"""
        
        # ping info detail
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

            # view cpu info detail
            stdin, stdout, stderr = ssh_client.exec_command("cat /proc/loadavg")
            cpu_response = stdout.read().decode()
            cpu_usage_rate = re.findall("(\d+)/(\d+)", cpu_response)[0]
            count_cpu = int(cpu_usage_rate[1])
            used_cpu = int(cpu_usage_rate[0])
            proportion = str(round(int(cpu_usage_rate[0])/int(cpu_usage_rate[1]), 2) * 100)
            cpu = {"count_cpu": count_cpu, "used_cpu": used_cpu, "proportion": proportion}

            # memory info
            stdin, stdout, stderr = ssh_client.exec_command("free -k")
            memory_response = stdout.read().decode()
            memory = re.findall("Mem:.*?(\d+).*?(\d+)", memory_response)[0]
            count_memory = int(memory[0])
            used_memory = int(memory[1])
            proportion = str(round(used_memory/count_memory, 2) * 100)
            memory = {"count_memory": count_memory, "used_memory": used_memory, "proportion": proportion}

            # disk info
            stdin, stdout, stderr = ssh_client.exec_command("df -Hk")
            disk_response = stdout.read().decode()
            disk_response = re.findall("(.*?)\s+(\d+).*?(\d+).*?(\d+).*?(\d+%)", disk_response)
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
            proportion = str(round(int(used_disk) / int(count_disk), 2) * 100)
            disk_info = {"count_disk": count_disk, "used_disk": used_disk, "proportion": proportion, "info": disk_info_list}

            # port info
            port_info_list = []
            for port in port_list:
                stdin, stdout, stderr = ssh_client.exec_command("rpm -qa | grep net-tools")
                if stdout is None:
                    # install net-tools
                    sftp = paramiko.Transport(sock=(host, port))
                    sftp.connect(username=username, password=password)
                    rpm = paramiko.SFTPClient.from_transport(sftp)
                    rpm_file = os.path.join(os.path.join(os.path.join(sys.path[0], "base"), "rpms"), "net-tools-2.0-0.25.20131004git.el7.x86_64.rpm")
                    rpm.put(rpm_file, "/root/")
                    sftp.close()
                    stdin, stdout, stderr = ssh_client.exec_command("rpm -ivh /root/net-tools-2.0-0.25.20131004git.el7.x86_64.rpm")
                    stdin, stdout, stderr = ssh_client.exec_command("rm -rf /root/net-tools-2.0-0.25.20131004git.el7.x86_64.rpm")
                stdin, stdout, stderr = ssh_client.exec_command("netstat -tunlp | grep %s" % port)
                port_response = stdout.read().decode()
                if port_response:
                    port_info_list.append({"port": port, "status": "listen"})
                else:
                    port_info_list.append({"port": port, "status": "closed"})
            port_info = port_info_list

        except paramiko.ssh_exception.AuthenticationException:
            ip = 0
            ssh_status = "failed"
            cpu = "-"
            memory = "-"
            disk_info = "-"
            port_info = "-"

        except paramiko.ssh_exception.NoValidConnectionsError:
            ip = 1
            ssh_status = "failed"
            cpu = "-"
            memory = "-"
            disk_info = "-"
            port_info = "-"

        finally:
            try:
                ssh_client.close()
            except Exception:
                pass

        return {
            "id": id,
            "IP": ip,
            "ssh_status": ssh_status,
            "cpu": cpu,
            "memory": memory,
            "disk": disk_info,
            "port_info": port_info
        }

    def info_save(self, data):
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
        
        try:
            self.cursor.execute(sql, data)
            
            # Correct self growth value
            sql = "SELECT COUNT(*) FROM server_info;"
            self.cursor.execute(sql)
            sql = "ALTER TABLE server_info auto_increment = %s;" % str(int(self.cursor.fetchone()[0]) + 1)
            self.cursor.execute(sql)

            self.db.commit()
        except FileExistsError:
            pass
        return 0

    def main(self):
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

        for item in base_info_list:
            if self.info_save(data=item) == 0:
                pass
            else:
                Myprint(grade=1, info="Server detection faild %s" % str(connection.get("host")))

    def __del__(self):
        try:
            self.cursor.close()
            self.db.close()
        except Exception:
            pass


if __name__ == "__main__":
    monitor = Monitor()
    monitor.main()