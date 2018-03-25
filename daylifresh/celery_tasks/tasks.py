import os
from celery import Celery
from tiantian.settings import EMAIL_FROM
from django.core.mail import send_mail
from apps.goods.models import GoodsType,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner
from django.template import loader
from tiantian.settings import BASE_DIR
# 创建celery对象
app = Celery('celery_tasks.tasks',broker='redis://192.168.44.160:6379/2')


# 封装函数
@app.task
def send_register_active_email(to_email,username,token):
    subject = '天天生鲜欢迎您'
    message1 = """
                  <h1>%s,欢迎你成为天天生鲜的会员！</h1><br/>
                  请点击下激活你的您的账号（连接一个小时内有效）<br/>
                  <a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.8000/user/active/%s</a>
                  """ % (username, token, token)
    sender = EMAIL_FROM
    receiver = [to_email]
    print(receiver)
    send_mail(subject, '', sender, receiver, html_message=message1)


@app.task
def mkdir_index():
    types = GoodsType.objects.all()

    # 获取首页的轮播商品的信息
    index_banner = IndexGoodsBanner.objects.all().order_by('index')

    # 获取首页的促销活动的信息
    promotion_banner = IndexPromotionBanner.objects.all().order_by('index')

    # 获取首页分类商品的展示信息
    for type in types:
        # 获取type种类在首页展示的图片商品的信息和文字商品的信息
        image_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1)
        title_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0)

        # 给type对象增加属性title_banner,image_banner
        # 分别保存type种类在首页展示的文字商品和图片商品的信息
        type.title_banner = title_banner
        type.image_banner = image_banner
    cart_conn = 0
    context = {
        'types': types,
        'index_banner': index_banner,
        'promotion_banner': promotion_banner,
        'cart_conn':cart_conn
        }
    # 获取模板数据
    temp = loader.get_template('static_index.html')
    # 渲染模数据
    static_index = temp.render(context)
    # 拼接路径
    index_path = os.path.join(BASE_DIR,'static/index.html')
    # 写入文件
    with open(index_path,'w') as f:
        f.write(static_index)

    print(static_index)