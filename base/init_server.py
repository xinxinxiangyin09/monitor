# init all base server

import sys
import re
import datetime
import os


def myPrint(info, grade=0):
    nowDate = lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
    log = content + '\n'
    with open(log_dir, 'a+') as f:
        f.write(log)


class Init(object):
    def __init__(self):
        pass

    def py_version(self):
        # check python version
        version = re.match("(\d+\.\d+.\d+)", sys.version).group()
        if version == "3.6.5":
            myPrint(info="Your Python version was personally tested by the author and you can successfully run the script !")
            return 0
        else:
            myPrint(grade=2, info="Your Python version was %s but need version was %s, inform you that the author of your Python version has not yet tested it !" % (version, "3.6.5"))
            return 1

    def db_init(self):
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml")
        try:
            import yaml
        except Exception:
            myPrint(info="The environment lacks dependencies %s and cannot load the yaml configuration file." % "PyYAML")
            sys.exit()

        try:
            f = open(config_path, 'r')
        except Exception:
            myPrint(grade=1, info="The configuration file does not exist, please check %s" % config_path)
            sys.exit()

        try:
            config = yaml.load(f.read(), Loader=yaml.FullLoader)
            myPrint(info="Current configuration information was %s." % config)
            f.close()
        except yaml.YAMLError as err:
            myPrint(grade=1, info="Configuration file loading failed, possibly due to formatting error, %s" % err)
            sys.exit()

        # check redis server
        try:
            import redis
        except Exception as err:
            myPrint(grade=1, info="Redis checked is failed, Please install the dependent package redis. %s" % err)
            sys.exit()

        try:
            redis = redis.Redis(
                host=str(config.get("redis_server").get("host")),
                port=int(config.get("redis_server").get("port")),
                username=str(config.get("redis_server").get("user")),
                password=str(config.get("redis_server").get("password")),
                db=int(config.get("redis_server").get("db"))
            )
            myPrint(info="Congratulations, your redis server is ready to use !")
        except Exception:
            myPrint(grade=1, info="Redis server checked is failed, Please confirm the connection information, %s" % config.get("db_redis"))
            sys.exit()

        redis.close()

        # check mysql server
        try:
            import pymysql
        except Exception as err:
            myPrint(grade=1, info="PyMySQL checked is failed, Please install the dependent package PyMySQL. %s" % err)
            sys.exit()

        try:
            db = pymysql.connect(
                host=str(config.get("mysql_server").get("host")),
                port=int(config.get("mysql_server").get("port")),
                user=str(config.get("mysql_server").get("username")),
                password=str(config.get("mysql_server").get("password")),
                # database=str(config.get("db_mysql").get("database")),
                database="mysql",
                charset=str(config.get("mysql_server").get("charset"))
            )

            myPrint(info="Congratulations, your MySQL server is ready to use !")
        except pymysql.Error as err:
            myPrint(grade=1, info="MySQL server connection failed, Please confirm the connection information, %s" % err)
            sys.exit()

        # create database
        cursor = db.cursor()
        try:
            cursor.execute("CREATE DATABASE `%s` CHARACTER SET 'utf8mb4' COLLATE 'utf8mb4_general_ci';" % config.get("mysql_server").get("database"))
            db.commit()
            myPrint(info="Successfully created database %s." % config.get("mysql_server").get("database"))
        except pymysql.Error as err:
            if "database exists" in str(err):
                myPrint(grade=0, info="MySQL database %s already exists, no need to create it again." % config.get("mysql_server").get("database"))
            else:
                myPrint(grade=1, info="MySQL created database %s was failed. Please check account %s permissions for %s" % (config.get("mysql_server").get("database"), config.get("db_mysql").get("user"), err))
                sys.exit()
        cursor.close()
        db.close()


        # create table desc
        db = pymysql.connect(
            host=str(config.get("mysql_server").get("host")),
            port=int(config.get("mysql_server").get("port")),
            user=str(config.get("mysql_server").get("username")),
            password=str(config.get("mysql_server").get("password")),
            database=str(config.get("mysql_server").get("database")),
            # database="mysql",
            charset=str(config.get("mysql_server").get("charset"))
        )
        cursor = db.cursor()

        sql_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "init.sql")
        f = open(sql_path, "r", encoding="utf-8")
        sql = f.read().replace("(\n", "(").replace(",\n", ",").replace(")\n", ")").replace("(\n", "").replace(",\n", ",").replace("  ","")
        f.close()

        # close foregin key
        # cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

        create_table_sql_list = []
        insert_data_sql_list = []
        for sql in sql.split(";\n"):
            sql = sql.replace("\n", "").replace("\r", "")
            if "CREATE TABLE" in sql:
                create_table_sql_list.append(sql + ";")
            elif "INSERT INTO" in sql:
                insert_data_sql_list.append(sql + ";")

        # create table
        myPrint(info="Starting create table...")
        for sql in create_table_sql_list:
            try:
                cursor.execute(sql)

                myPrint(info="done-----%s" % sql)
            except pymysql.err.OperationalError as err:
                table_name = re.findall("Table '(.*)'", str(err))[0]
                if "already exists" in str(err):
                    myPrint(info="The data table %s already exists." % table_name)
                else:
                    myPrint(grade=1, info="unknown error, %s. %s" % (err, sql))
                    sys.exit()

        myPrint(info="Starting insert data...")
        for sql in insert_data_sql_list:
            try:
                cursor.execute(sql)
                myPrint(info="done----%s" % sql)
            except pymysql.err.ProgrammingError as err:
                if "You have an error in your SQL syntax" in str(err):
                    myPrint(grade=1, info="SQL syntax error. %s" % sql)
                    sys.exit()
                else:
                    myPrint(grade=1, info="unknown error. %s" % err)
                    sys.exit()
            except Exception as err:
                myPrint(grade=1, info="unknown error, %s. %s" % (err, sql))
                sys.exit()
        db.commit()
        myPrint(info="MySQL database initialization completed.")

        # open foregin key
        # cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

        cursor.close()
        db.close()

    def main(self):

        # starting check python version
        myPrint(info="Starting checking Python version...")
        pip_result = self.py_version()
        while True:
            if pip_result == 0:
                break
            else:
                while True:
                    select_number = input("Please enter whether to continue<Y is Contine, N is Stop>:").upper()
                    try:
                        if select_number is not None:
                            break
                        else:
                            continue
                    except ValueError:
                        print("Please enter the correct option")
                        continue
                if select_number == "Y":
                    break
                elif select_number == "N":
                    myPrint(grade=1, info="User actively exits !")
                    sys.exit()
                else:
                    myPrint(grade=1, info="Exception occurred, exiting the program !")
                    sys.exit()

        # starting init database
        myPrint(info="Starting init db environment...")
        self.db_init()


if __name__ == "__main__":
    init = Init()
    init.main()
