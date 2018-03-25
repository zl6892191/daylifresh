import re
from django.shortcuts import render,redirect
from apps.user.models import User,Address
from django.core.urlresolvers import reverse
from django.views.generic import View
from tiantian.settings import SECRET_KEY,EMAIL_FROM
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.http import HttpResponse
from django.core.mail import send_mail
from django.contrib.auth import authenticate, login, logout
from utils.mixin import LoginReuiredMixin
from django_redis import get_redis_connection
from apps.goods.models import GoodsSKU
from celery_tasks.tasks import send_register_active_email
from datetime import datetime
from apps.order.models import OrderInfo,OrderGoods
from django.core.paginator import Paginator

# 注册首页
def register1(request):
    return render(request,'register.html')

def index(request):
    return render(request,'index.html')

# 验证注册信息
def register_handle(request):
    username = request.POST.get('user_name')
    password = request.POST.get('pwd')
    email = request.POST.get('email')
    # 校验数据的完整性
    if not all([username,password,email]):
        return render(request,'register.html',{'errmsg':'数据不完整'})

    # 判断邮箱是否为真
    if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$',email):
        return render(request,'register.html',{'errmsg':'邮箱格式不正确'})
    # 校验用户名是否已注册
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist :
        user = None
    if user is not None:
        return render(request, 'register.html', {'errmsg': '用户已存在，请重新输入'})
    # 创建用户并提交
    user =User.objects.create_user(username,email,password)
    # 改为0表示未激活
    user.is_active =0
    user.save()
    # 如果注册成功访问首页
    return redirect(reverse('goods:index'))
    # 注册业务处理 往数据里面提交信息


def register(request):
    if request.method == 'GET':
        return render(request, 'register.html')
    else:
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        # 校验数据的完整性
        if not all([username, password, email]):
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        # 判断邮箱是否为真
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})
        # 校验用户名是否已注册
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
        if user is not None:
            return render(request, 'register.html', {'errmsg': '用户已存在，请重新输入'})
        # 创建用户并提交
        user = User.objects.create_user(username, email, password)
        # 改为0表示未激活
        user.is_active = 0
        user.save()
        # 判断用户是否以激活 加密

        # 如果注册成功访问首页
        return redirect(reverse('goods:index'))


class RegisterView(View):

    def get(self,request):
        return render(request, 'register.html')

    def post(self,request):
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        # 校验数据的完整性
        if not all([username, password, email]):
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        # 判断邮箱是否为真
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})
        # 校验用户名是否已注册
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
        if user is not None:
            return render(request, 'register.html', {'errmsg': '用户已存在，请重新输入'})
        # 创建用户并提交
        user = User.objects.create_user(username, email, password)
        # 改为0表示未激活
        user.is_active = 0
        user.save()
        # 账户加密
        serializer = Serializer(SECRET_KEY, 3600)
        info = {'confirm':user.id}
        # token字符串类型需要解密
        token = serializer.dumps(info)
        token = token.decode()
        # 发送邮件
        # subject = '天天生鲜欢迎您'
        # message1 = """
        #         <h1>%s,欢迎你成为天天生鲜的会员！</h1><br/>
        #         请点击下激活你的您的账号（连接一个小时内有效）<br/>
        #         <a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.8000/user/active/%s</a>
        #         """% (username,token,token)
        # sender = EMAIL_FROM
        # receiver =[email]
        # print(receiver)
        # send_mail(subject,'',sender,receiver,html_message=message1)
        # 使用celery来发送邮件
        send_register_active_email.delay(email,username,token)
        # 如果注册成功访问首页
        return redirect(reverse('user:login'))

# 拿到token 进行激活操作
class ActiveView(View):
    def get(self,request,token):
        serializer = Serializer(SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            user_id = info['confirm']
            # 开始激活
            user = User.objects.get(id=user_id)
            # 设置激活
            user.is_active = 1
            user.save()
            # 激活成功跳转至登录页面
            return redirect(reverse('user:login'))
        except SignatureExpired as e:
            return HttpResponse('激活已失效，请重新激活！')


# 用户中心累
# class User_Center_Info(View):
class User_Center_Info(LoginReuiredMixin,View):
    def get(self,request):
        # 获取默认信息
        user = request.user
        address = Address.objects.get_default_address(user)
        # 获取浏览记录
        conn = get_redis_connection('default')
        # 拼接查询的KEY
        history = 'history_%s'%user.id
        # 查询最近前5个的信息
        sku_ids = conn.lrange(history,0,4)
        # 根据这5个信息查询里面的数据
        skus = []
        for sku_id in sku_ids:
            sku = GoodsSKU.objects.get(id = sku_id)
            skus.append(sku)
        # 替换
        context ={
            'page':'user',
            'address': address,
            'skus':skus
        }
        return render(request,'user_center_info.html',context)

# 用户订单类
# class User_Center_Order(View):
class User_Center_Order(LoginReuiredMixin, View):
    def get(self,request,page):
        # 获取参数
        user = request.user
        # 从OrderInfo拿取数据
        orders = OrderInfo.objects.filter(user=user).order_by('-create_time')
        for order in orders:
            # 获取订单商品的信息
            order_skus = OrderGoods.objects.filter(order = order)
            for order_sku in order_skus:
                # 获取数量和单价的小计
                amount = order_sku.price * order_sku.count
                # 将数据添加到order_sku属性里面
                order_sku.amount = amount
            # 获取支付状态
            order.status_title = OrderInfo.ORDER_STATUS[order.order_status]
            order.total_pay = order.total_price + order.transit_price
            # 将商品订单信息添加到order
            order.order_skus = order_skus
            # 设计分页
        paginator = Paginator(orders,1)
        # 获取订单内容
        page = int(page)
        # 判断页码
        if page > paginator.num_pages:
            page = 1
        # 获取第几页内容
        order_page = paginator.page(page)
        print(type(order_page))
        # 处理页码内容
        #处理页码列表
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(num_pages - 2, num_pages + 3)
        # 组织内容上下文
        context = {
                'order_page':order_page,
                'pages':pages,
                'page':'order'
            }
        return render(request, 'user_center_order.html', context)

# 用户收地址类
# class User_Center_Site(View):
class User_Center_Site(LoginReuiredMixin, View):
    def get(self,request):
        # 判断用户
        user = request.user
        address = Address.objects.get_default_address(user)
        # 组织模板上下文
        context = {
            'address': address,
            'page': 'address'
        }

        # 使用模板
        return render(request, 'user_center_site.html', context)
    def post(self,request):
        # 接受参数
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        email = request.POST.get('zip_code')
        phone = request.POST.get('phone')
        # 验证参数
        if not all([receiver,addr,phone]):
            return render(request,reverse('user:address'),{'errmsg':'你输入的信息不完整！'})
        # 添加收货地址
        user =request.user
        address = Address.objects.get_default_address(user)
        is_default = True
        if address is not None:
            is_default = False
        # 添加收货地址
        Address.objects.create(
                        user = user,
                        receiver = receiver,
                        addr = addr,
                        phone = phone,
                        is_default = is_default
        )
        return redirect(reverse('user:address'))




# Create your views here.

class LoginView(View):
    def get(self,request):
        username = request.COOKIES.get('username')
        checked = 'checked'
        if username is  None:
            username = ''
            checked = ''
        return render(request, 'login.html',{'username':username,'checked':checked})


    def post(self,request):
        # 拿到账户名
        username = request.POST.get('username')
        # 拿到密码
        password = request.POST.get('pwd')
        # 校验账号密码
        remenber = request.POST.get('remenber')
        # 校验完整性
        if not all([username,password]):
            return render(request,'login.html',{'errmsg':'参数不完整'})
        # 验证账号密码
        user = authenticate(username=username,password=password)
        if user is not None:
            if user.is_active:
                login(request,user)
                # 跳转到之前地址栏的地址
                next_url = request.GET.get('next',reverse('goods:index'))

                response = redirect(next_url)
                if remenber == 'on':
                    response.set_cookie('username',username,max_age=7*24*3600)
                else:
                    response.delete_cookie('username')





                return response
            else:
                # 用户未激活
                return render(request, 'login.html', {'errmsg': '用户未激活'})
        else:
            # 用户名或密码错误
            return render(request, 'login.html', {'errmsg': '用户名或密码错误'})



# 退出账户
class LoginOut(View):

    def get(self,request):

        logout(request)

        return redirect(reverse('user:login'))




