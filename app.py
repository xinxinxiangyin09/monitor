from db_tools import Data
# 导入自定义包，封装操作数据库的方法，减少单文件代码量

from flask import Flask, render_template, jsonify, Markup
# 导入flask框架基础包和扩展插件

app = Flask(__name__)
# 实例化web-socket

@app.template_filter()
def upper_(value):
    return value.upper()
# 添加自定义模板过滤器语法块

app.add_template_filter(upper_)
# 载入实例

@app.route("/")
@app.route("/index")
def index():
    data = Data().index_data()
    # 调用自定义类方法，获取主页信息
    # print(data)
    return render_template("index.html", data=data)
# 主页路由

@app.route("/<host_id>")
def detail(host_id):
    data = Data().detail_data(host_id=host_id)
    # 调用自定义类方法，获取详情页信息
    return render_template("detail.html", data=data)
# 详情页路由