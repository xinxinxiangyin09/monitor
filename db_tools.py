"""
插件，用于操作数据库
"""

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
# 自定义日志

class Data(object):
    def __init__(self) -> None:
        config_path = os.path.join(sys.path[0], "config.yaml")
        # 寻找配置文件路径
        try:
            f = open(config_path, "r")
            self.config = yaml.load(f.read(), Loader=yaml.FullLoader)
            # 加载配置文件
        except FileNotFoundError:
            Myprint(grade=1, info="The configuration file does not exist. Please checking %s." % config_path)
            sys.exit()
            # 未找到配置文件
        except yaml.scanner.ScannerError:
            Myprint(grade=1, info="The configuration file format is incorrect. Please note that it is in JSON format.")
            sys.exit()
            # json格式错误，无法转换python对象
        except Exception as err:
            Myprint(grade=1, info = "Unknown critical error. %s" % err)
            sys.exit()
            # 未知错误
        
        # 连接MySQL
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
            # 尝试连接数据库
        except pymysql.err.OperationalError as err:
            if "Can't connect to MySQL" in str(err):
                info = "Mysql server is faild or not running."
                # 连接数据库失败，可能MySQL未运行或者配置错误
            elif "Unknown database" in str(err):
                info = "Database 'monitor' does not exist ."
                # 未知错误
            Myprint(grade=1, info=info)
            sys.exit()

        # 连接redis
        try:
            self.redis_db = redis.Redis(
                host=str(self.config.get("redis_server").get("host")),
                port=int(self.config.get("redis_server").get("port")),
                password=str(self.config.get("redis_server").get("password")),
                db = int(self.config.get("redis_server").get("db"))
            )
            self.redis_db.get("key*")
            # 成功连接redis
        except redis.exceptions.ResponseError as err:
            if "username-password pair" in str(err):
                Myprint(grade=1, info="Redis server username or password is faild.")
            sys.exit()
            # redis连接失败，密码错误
        except Exception:
            Myprint(grade=1, info="Redis server unkonw error.")
            # redis连接失败，未知错误

    # 加载主页数据
    def index_data(self):
        sql = "SELECT id FROM connect_info;"
        self.cursor.execute(sql)
        host_id_list = []
        for host_id in self.cursor.fetchall():
            host_id_list.append(host_id.get("id"))
        host_id_list.reverse()
        # 获取设备标识符

        server_info_list = []
        for host_id in host_id_list:
            sql = "SELECT host_id,ip_status,ssh_status,cpu_proportion,memory_proportion,disk_proportion,ports_info,created FROM server_info WHERE host_id = %s ORDER BY created LIMIT 1;"
            self.cursor.execute(sql, [host_id,])
            server_info = self.cursor.fetchall()[0]
            # 联合查询，获取设备信息

            sql = "SELECT ip_addr FROM connect_info WHERE id = %s and is_true = 0;" % server_info["host_id"]
            self.cursor.execute(sql)
            server_info["ip_addr"] = self.cursor.fetchall()[0]["ip_addr"]
            ports_info = server_info.get("ports_info")
            # 单表查询，获取端口信息

            try:
                ports_info = json.loads(ports_info)
                server_info["ports_info"] = ports_info
            except AttributeError:
                ports_info = None
            except TypeError:
                ports_info = None
            finally:
                server_info_list.append(server_info)
            # 结构化端口数据

        return server_info_list
        
    # 加载详情页数据
    def detail_data(self, host_id):
        sql = "SELECT connect_info.ip_addr,host_id,ip_status,ssh_status,cpu_used,cpu_count,cpu_proportion,memory_count,memory_used,memory_proportion,disk_count,disk_used,disk_proportion,disk_detail,ports_info,created FROM server_info,connect_info WHERE connect_info.id = server_info.host_id AND server_info.host_id = %s ORDER BY created desc LIMIT 1;"
        self.cursor.execute(sql, [host_id, ])
        # 右连接查询，connect_info作为主表，server_info作为辅表，获取设备详细信息

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
        # 规范设备信息的数据

        data["disk_detail"] = disk_detail
        data["ports_info"] = ports_info
        # 数据载入PYTHON对象，用于返回前端

        return data

    def __del__(self):
        self.cursor.close()
        self.db.close()
        self.redis_db.close()
        # 关闭连接的数据库，减少服务器性能开销

# if __name__ == "__main__":
#     db = Data()
# 程序入口，本程序由后台主程序app.py调用，无需运行，只做加载