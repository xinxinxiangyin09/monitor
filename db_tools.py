"""mysql server return data"""

import os
import sys
import datetime
import json

import pymysql
import yaml
import redis

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
    log_dir = os.path.join(os.path.join(os.path.split(os.path.abspath(__file__))[0], "log"), "db_tools.log")
    log = content + '\n'
    print(content)
    with open(log_dir, 'a+') as f:
        f.write(log)

class Data(object):
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
            sys.exit()
        
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
            self.cursor = self.db.cursor(pymysql.cursors.DictCursor)
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

    def base_info(self, host_id):
        server_info_list = []
        sql = "SELECT host_id,ip_status,ssh_status,cpu_proportion,memory_proportion,disk_proportion,ports_info,created FROM server_info WHERE host_id = %s ORDER BY created DESC LIMIT 1;"
        self.cursor.execute(sql, [host_id,])
        try:
            server_info = self.cursor.fetchall()[0]
        except IndexError:
            server_info = None

        # get ip address
        sql = "SELECT ip_addr,nickname,uuid FROM connect_info WHERE id = %s and is_true = 0;" % server_info["host_id"]
        self.cursor.execute(sql)

        result = self.cursor.fetchall()[0]

        server_info["uuid"] = result["uuid"]
        server_info["ip_addr"] = result["ip_addr"]
        server_info["nickname"] = result["nickname"]

        ports_info = server_info.get("ports_info")



        try:
            ports_info = json.loads(ports_info)
            server_info["ports_info"] = ports_info
        except AttributeError:
            ports_info = None
        except TypeError:
            ports_info = None
        finally:
            server_info_list.append(server_info)

        return server_info_list
        
    def index_data(self):
        sql = "SELECT connect_info.id,group_info.`name` FROM connect_info,group_info WHERE connect_info.group_id = group_info.id;"
        self.cursor.execute(sql)
        host_info_list = []
        for item in self.cursor.fetchall():
            host_info_list.append(item)
        
        group_info_list = []
        for host_info in host_info_list:
            group_info_list.append(host_info.get("name"))
        group_info_list = set(group_info_list)

        host_data = []
        for group_info in group_info_list:
            group_name_list = []
            for host_info in host_info_list:
                if group_info == host_info["name"]:
                    group_name_list.append(host_info["id"])
            host_data.append({group_info: group_name_list})

        data = []
        for host_info in host_data:
            group_name = list(host_info.keys())[0]
            server_info_list = []
            for server_info in host_info[group_name]:
                server_info_list.append(self.base_info(host_id = server_info))
            data.append({"key": group_name, "value": server_info_list})
        # print(data)
        # host_id_list.reverse()
        return data

    def detail_data(self, host_id):
        sql = "SELECT connect_info.ip_addr,host_id,ip_status,ssh_status,cpu_used,cpu_count,cpu_proportion,memory_count,memory_used,memory_proportion,disk_count,disk_used,disk_proportion,disk_detail,ports_info,created FROM server_info,connect_info WHERE connect_info.id = server_info.host_id AND server_info.host_id = %s ORDER BY created desc LIMIT 1;"
        self.cursor.execute(sql, [host_id, ])
        try:
            data = self.cursor.fetchall()[0]
        except Exception:
            data = {}
        try:
            disk_detail = json.loads(data["disk_detail"])
        except Exception:
            disk_detail = None
        try:
            ports_info = json.loads(data["ports_info"])
        except Exception:
            ports_info = None

        data["disk_detail"] = disk_detail
        data["ports_info"] = ports_info

        return data

    def __del__(self):
        self.cursor.close()
        self.db.close()
        self.redis_db.close()


if __name__ == "__main__":
    db = Data()
    index_data = db.index_data()
    print(index_data)