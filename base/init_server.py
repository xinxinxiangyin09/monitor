# 初始化所有基础环境，本次初始化mysql,redis,python-env

import sys
import re
import datetime
import os


def myPrint(info, grade=0):
    """
    自定义输出日志信息
    info: 输出日志
    grade: 日志等级，默认一般，1为异常，2为告警，3为未知
    """
    nowDate = lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 匿名函数，简化语法
    if grade == 0:
        content = "[%s] info %s" % (nowDate(), info)
    elif grade == 1:
        content = "[%s] error %s" % (nowDate(), info)
    elif grade == 2:
        content = "[%s] warning %s" % (nowDate(), info)
    else:
        content = "[%s] unknown %s" % (nowDate(), info)

    print(content)
    log_dir = os.path.join(os.path.join(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0], "log"), "init.log")
    # 获取项目日志位置
    log = content + '\n'
    with open(log_dir, 'a+') as f:
        f.write(log)


class Init(object):
    def __init__(self):
        pass

    def py_version(self):
        # 检查PYTHON版本是否兼容
        version = re.match("(\d+\.\d+.\d+)", sys.version).group()
        if version == "3.6.5":
            myPrint(info="Your Python version was personally tested by the author and you can successfully run the script !")
            return 0
        else:
            myPrint(grade=2, info="Your Python version was %s but need version was %s, inform you that the author of your Python version has not yet tested it !" % (version, "3.6.5"))
            return 1

    def db_init(self):
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml")
        # 获取配置文件位置，用于加载配置

        try:
            import yaml
        except Exception:
            myPrint(info="The environment lacks dependencies %s and cannot load the yaml configuration file." % "PyYAML")
            sys.exit()
        # 加载pip依赖，正常加载则向下运行，异常加载直接退出

        try:
            f = open(config_path, 'r')
        except Exception:
            myPrint(grade=1, info="The configuration file does not exist, please check %s" % config_path)
            sys.exit()
        # 探测配置文件是否存在，存在则向下运行，不存在退出

        try:
            config = yaml.load(f.read(), Loader=yaml.FullLoader)
            myPrint(info="Current configuration information was %s." % config)
            f.close()
        except yaml.YAMLError as err:
            myPrint(grade=1, info="Configuration file loading failed, possibly due to formatting error, %s" % err)
            sys.exit()
        # 加载配置文件，检查配置格式是否为json格式，若符合向下运行，不符合则退出

        try:
            import redis
        except Exception as err:
            myPrint(grade=1, info="Redis checked is failed, Please install the dependent package redis. %s" % err)
            sys.exit()
        # 检查pip依赖包：redis，正常导入则向下运行，异常则退出


        try:
            redis = redis.Redis(
                host=str(config.get("db_redis").get("host")),
                port=int(config.get("db_redis").get("port")),
                username=str(config.get("db_redis").get("user")),
                password=str(config.get("db_redis").get("password")),
                db=int(config.get("db_redis").get("db"))
            )
            # 尝试连接REDIS服务
            myPrint(info="Congratulations, your redis server is ready to use !")
        except Exception:
            myPrint(grade=1, info="Redis server checked is failed, Please confirm the connection information, %s" % config.get("db_redis"))
            sys.exit()
            # redis服务异常，退出

        redis.close()
        # 测试REDIS服务是否正常连接

        try:
            import pymysql
        except Exception as err:
            myPrint(grade=1, info="PyMySQL checked is failed, Please install the dependent package PyMySQL. %s" % err)
            sys.exit()
        # 测试pip依赖包：pymysql

        try:
            db = pymysql.connect(
                host=str(config.get("db_mysql").get("host")),
                port=int(config.get("db_mysql").get("port")),
                user=str(config.get("db_mysql").get("user")),
                password=str(config.get("db_mysql").get("password")),
                # database=str(config.get("db_mysql").get("database")),
                database="mysql",
                charset=str(config.get("db_mysql").get("charset"))
            )
        # 尝试连接Mysql服务

            myPrint(info="Congratulations, your MySQL server is ready to use !")
        except pymysql.Error as err:
            myPrint(grade=1, info="MySQL server connection failed, Please confirm the connection information, %s" % err)
            sys.exit()
        # MySQL服务连接失败

        cursor = db.cursor()
        # 创建MySQL游标
        try:
            cursor.execute("CREATE DATABASE `%s` CHARACTER SET 'utf8mb4' COLLATE 'utf8mb4_general_ci';" % config.get("db_mysql").get("database"))
            db.commit()
            myPrint(info="Successfully created database %s." % config.get("db_mysql").get("database"))
            # 执行SQL语句，创建数据库
        except pymysql.Error as err:
            if "database exists" in str(err):
                myPrint(grade=0, info="MySQL database %s already exists, no need to create it again." % config.get("db_mysql").get("database"))
                # 数据库存在，跳过该步骤，向下运行
            else:
                myPrint(grade=1, info="MySQL created database %s was failed. Please check account %s permissions for %s" % (config.get("db_mysql").get("database"), config.get("db_mysql").get("user"), err))
                sys.exit()
                # 数据库创建失败，退出程序
        cursor.close()
        db.close()
        # 关闭MySQL的游标和连接

        # 连接数据库，与上边连接不同的是，本次连接的数据库为上次创建的数据库
        db = pymysql.connect(
            host=str(config.get("db_mysql").get("host")),
            port=int(config.get("db_mysql").get("port")),
            user=str(config.get("db_mysql").get("user")),
            password=str(config.get("db_mysql").get("password")),
            database=str(config.get("db_mysql").get("database")),
            # database="mysql",
            charset=str(config.get("db_mysql").get("charset"))
        )
        cursor = db.cursor()
        # 成功连接MySQL，创建游标用于操作数据库

        sql_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "init.sql")
        # 获取SQL文件路径
        f = open(sql_path, "r", encoding="gbk")
        # 加载数据库初始化的SQL文件
        sql = f.read().replace("(\n", "(").replace(",\n", ",").replace(")\n", ")").replace("(\n", "").replace(",\n", ",").replace("  ","")
        f.close()
        # 读取SQL文件的内容并过滤PYTHON无法识别的语法模块，例如注释，换行符，制表符等

        create_table_sql_list = []
        insert_data_sql_list = []
        for sql in sql.split(";\n"):
            sql = sql.replace("\n", "").replace("\r", "")
            if "CREATE TABLE" in sql:
                create_table_sql_list.append(sql + ";")
            elif "INSERT INTO" in sql:
                insert_data_sql_list.append(sql + ";")
        # 分离加载出来的SQL语句，按照建表和导入数据分割SQL，便于后期分离运行，减少服务器性能开销

        myPrint(info="Starting create table...")
        for sql in create_table_sql_list:
            try:
                cursor.execute(sql)
                myPrint(info="done-----%s" % sql)
                # 执行建表SQL成功
            except pymysql.err.OperationalError as err:
                table_name = re.findall("Table '(.*)'", str(err))[0]
                # 捕获异常信息，为用户提供故障解决思路
                if "already exists" in str(err):
                    # 表存在
                    myPrint(info="The data table %s already exists." % table_name)
                else:
                    myPrint(grade=1, info="unknown error, %s. %s" % (err, sql))
                    sys.exit()
                    # 操作错误，退出

        myPrint(info="Starting insert data...")
        for sql in insert_data_sql_list:
        # 遍历导入数据的SQL，循环导入
            try:
                cursor.execute(sql)
                myPrint(info="done----%s" % sql)
                # 执行导入SQL成功
            except pymysql.err.ProgrammingError as err:
                # 捕获异常信息，为用户提供故障解决思路
                if "You have an error in your SQL syntax" in str(err):
                    myPrint(grade=1, info="SQL syntax error. %s" % sql)
                    sys.exit()
                    # SQL语法错误
                else:
                    myPrint(grade=1, info="unknown error. %s" % sql)
                    sys.exit()
                    # 未知错误
            except Exception as err:
                myPrint(grade=1, info="unknown error, %s. %s" % (err, sql))
                sys.exit()
        db.commit()
        # 提交数据库修改
        myPrint(info="MySQL database initialization completed.")

        cursor.close()
        db.close()

    def main(self):
        # 主运行类方法，调用重新类方法，避免大量重复性代码
        myPrint(info="Starting checking Python version...")
        pip_result = self.py_version()
        # 检查PYTHON版本
        while True:
            # 死循环，用于用户操作递归
            if pip_result == 0:
                break
            else:
                while True:
                    select_number = input("Please enter whether to continue<Y is Contine, N is Stop>:").upper()
                    # 捕获用户输入信息，判断下一步是否继续
                    try:
                        if select_number is not None:
                            break
                        else:
                            continue
                    except ValueError:
                        print("Please enter the correct option")
                        # 用户输入指令错误，进入死循环
                        continue
                if select_number == "Y":
                    # 用户继续，跳出死循环
                    break
                elif select_number == "N":
                    myPrint(grade=1, info="User actively exits !")
                    sys.exit()
                    # 用户终止，退出程序
                else:
                    myPrint(grade=1, info="Exception occurred, exiting the program !")
                    sys.exit()
                    # 异常退出

        myPrint(info="Starting init db environment...")
        self.db_init()
        # 初始化数据库的数据信息，建表、导入基础数据

if __name__ == "__main__":
    # 程序入口
    init = Init()
    # 创建实例，调用类方法
    init.main()
    # 调用主程序运行
