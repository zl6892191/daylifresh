from django.shortcuts import render,redirect
from django.views.generic import View
from utils.mixin import LoginReuiredMixin
from apps.user.models import Address
from apps.goods.models import GoodsSKU
from django_redis import get_redis_connection
from django.http import JsonResponse,HttpResponse
from apps.order.models import OrderInfo,OrderGoods
from django.db import transaction
from alipay import AliPay
from tiantian import settings
from django.core.urlresolvers import reverse


# 用户订单页面
class PlaceOrderView(LoginReuiredMixin,View):
    def post(self, request):
        # 获取登录用户
        user = request.user

        # QueryDict getlist
        # 获取用户所要购买的商品的id

        sku_ids = request.POST.getlist('sku_ids')

        # 获取用户收货地址的信息
        addrs = Address.objects.filter(user=user)

        # 获取redis链接
        conn = get_redis_connection('default')

        # 拼接key
        cart_key = 'cart_%d' % user.id

        # 遍历sku_ids获取用户所要购买的商品的信息
        skus = []
        total_count = 0
        total_amount = 0
        for sku_id in sku_ids:
            # 根据id查找商品的信息
            sku = GoodsSKU.objects.get(id=sku_id)

            # 从redis中获取用户所要购买的商品的数量
            count = conn.hget(cart_key, sku_id)

            # 计算商品的小计
            amount = sku.price * int(count)

            # 给sku对象增加属性count和amount
            # 分别保存用户要购买的商品的数目和小计
            sku.count = count
            sku.amount = amount

            # 追加商品的信息
            skus.append(sku)

            # 累加计算用户要购买的商品的总件数和总金额
            total_count += int(count)
            total_amount += amount

        # 运费: 运费表: 100-200
        transit_price = 10

        # 实付款
        total_pay = total_amount + transit_price

        # 组织模板上下文
        context = {
            'addrs': addrs,
            'skus': skus,
            'total_count': total_count,
            'total_amount': total_amount,
            'transit_price': transit_price,
            'total_pay': total_pay,
            'sku_ids': ','.join(sku_ids)
        }

        # 使用模板
        return render(request, 'place_order.html', context)

# 用户订单提交VIew
class CommitView(LoginReuiredMixin,View):
    # 设置数据库事物
    @transaction.atomic
    def post(self,request):
        # 判断用户是否登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res':0,'errmsg':'请先登录！'})
        # 获取参数
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')
        # 参数完整性校验
        if not all([addr_id,pay_method,sku_ids]):
            return JsonResponse({'res':1,'errmsg':'参数不完整'})
        # 检验支付方式是否合法
        if pay_method  not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res':2,'errmsg':'支付方式不合法'})
        # 组织订单信息ID
        from datetime import datetime
        order_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(user.id)
        print(order_id)

        # 检验用户地址是否合法
        try:
            addr = Address.objects.get(id = addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res':3,'errmsg':'收货地址有误'})
        # 订单运费
        transit_price = 10
        # 总数量，总价格
        total_count = 0
        total_price = 0
        # 尝试提交，数据下面跟新，并设保存点

        sid = transaction.savepoint()
        try:
            order = OrderInfo.objects.create(
                user = user,
                addr = addr,
                pay_method = pay_method,
                total_count = total_count,
                transit_price = transit_price,
                total_price = total_price,
                order_id = order_id
            )
            # 给数据库OrderGoods里面添加数据
            # 链接数据库
            conn = get_redis_connection('default')
            # 拼接key
            cart_key = "cart_%d"%user.id
            # 从sku_ids中拿出商品ID
            good_id = sku_ids.split(',')
            for i in good_id:
                try:
                    # select * from df_goods_sku where id=<sku_id> for update;
                    # sku = GoodsSKU.objects.get(id=sku_id)
                    print('user: %d try get lock' % user.id)
                    sku = GoodsSKU.objects.select_for_update().get(id = i)
                    print('user: %d get locked' % user.id)
                except GoodsSKU.DoesNotExist:
                    # 回滚事务到sid保存点
                    transaction.savepoint_rollback(sid)
                    return JsonResponse({'res': 4, 'errmsg': '商品信息错误'})
                count = conn.hget(cart_key, i)
                print(count)
                # 判断订单数量是否大于库存数量
                if int(count)> sku.stock:
                    # 回滚保存点
                    transaction.savepoint_rollback(sid)
                    return JsonResponse({'res:':5,'errmsg':'库存量不足！'})
                total_price += sku.price*int(count)
                total_count += int(count)
                # 添加数据给OrderGoods
                OrderGoods.objects.create(
                    order = order,
                    sku = sku,
                    count = count,
                    price = sku.price
                )
                # 增加销量，减少库存
                sku.stock -= int(count)
                sku.sales += int(count)
                sku.save()
                # 更新数据库 OrderInfo
                order.total_count = total_count
                order.total_price = total_price
                order.save()
        except Exception as e:
            print(e)
            # 回滚保存点
            transaction.savepoint_rollback(sid)
            return JsonResponse({'res':6,'errmsg':'添加订单失败'})
        # 删除购物车的记录
        conn.hdel(cart_key,*sku_ids)
        return JsonResponse({'res':7,'errmsg':'添加订单成功！'})


# /order/pay 支付页面处理视图
class AlipayView(View):
    def post(self,request):
        # 获取订单ID
        user = request.user
        order_id = request.POST.get('order_id')
        print('000000000')
        print(order_id)
        # 判断用户是否已登录
        if not user.is_authenticated:
            return JsonResponse({'res':0,'errmsg':'请先登录!'})
        # 校验ID的完整性
        if not all([order_id]):
            return JsonResponse({'res':1,'errmsg':'缺少参数!'})
        # 判断订单ID是否合法
        try:
            sku =OrderInfo.objects.get(order_id = order_id,
                                        user = user,
                                        order_status = 1,
                                        pay_method = 3 )
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res':2, 'errmsg':'无效的订单！'})
        # 初始化alipay的参数
        alipay = AliPay(
            appid = settings.ALIPAY_APP_ID,  # 应用APPID
            app_notify_url=settings.ALIPAY_APP_NOTIFY_URL,  # 默认回调url
            app_private_key_path=settings.APP_PRIVATE_KEY_PATH,  # 应用私钥文件路径
            # 支付宝的公钥文件，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_path=settings.ALIPAY_PUBLIC_KEY_PATH,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug = settings.ALIPAY_DEBUG  # 默认False，False代表线上环境，True代表沙箱环境
        )
        # 调用接口函数并组织函数
        # 获取订单号，订单金额，
        total_pay = sku.total_price + sku.transit_price
        # 电脑网站支付

        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no =order_id, # 商户订单号
            total_amount =str(total_pay), # 订单总金额
            subject ='天天生鲜%s'%order_id, # 订单标题
            return_url  ='http://127.0.0.1:8000/order/check',
            notify_url  =None # 可选, 不填则使用默认notify url
            )


        # 拼接发送地址
        pay_url = settings.ALIPAY_GATEWAY_URL + order_string
        return JsonResponse({'res':3,'pay_url':pay_url,'errmsg':'ok'})


# 验证支付是否成功
class OrderCheckView(LoginReuiredMixin,View):
    def get(self,request):
        # 获取参数
        out_trade_no = request.GET.get('out_trade_no')
        print('===1===')
        # 验证参数的完整性
        if not all([out_trade_no]):
            return HttpResponse('参数有误！')
        # 验证订单号是否正确
        try:
            order = OrderInfo.objects.get(order_id = out_trade_no)
        except OrderInfo.DoesNotExist:
            return HttpResponse('商品不存在！')
        # 初始化alipay的参数
        alipay = AliPay(
            appid=settings.ALIPAY_APP_ID,  # 应用APPID
            app_notify_url=settings.ALIPAY_APP_NOTIFY_URL,  # 默认回调url
            app_private_key_path=settings.APP_PRIVATE_KEY_PATH,  # 应用私钥文件路径
            # 支付宝的公钥文件，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_path=settings.ALIPAY_PUBLIC_KEY_PATH,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=settings.ALIPAY_DEBUG  # 默认False，False代表线上环境，True代表沙箱环境
        )
        # 验证支付结果
        response = alipay.api_alipay_trade_query(
            out_trade_no=out_trade_no,  # 商品订单号
        )
        res_code = response.get('code')
        status = response.get('trade_status')
        print(res_code)
        print(status)
        if res_code == '10000' and status == 'TRADE_SUCCESS':
            # 更新交易状态和支付宝交易号
            order.order_id = out_trade_no
            order.order_status = 4
            order.trade_no = response.get('trade_no')
            order.save()
            return render(request, 'pay_result.html', {'pay_result': '支付成功'})
        else:
            return render(request, 'pay_result.html', {'pay_result': '支付失败'})


# 订单评论处理函数
class CommentView(LoginReuiredMixin,View):
    def get(self,request,order_id):
        user = request.user
        # 判断数据的完整性
        if not all([order_id]):
            return redirect(reverse('user:order', kwargs={"page": 1}))

        # 判断数据是否正确
        try:
            order = OrderInfo.objects.get(user = user, order_id = order_id )
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order', kwargs={"page": 1}))

            # 根据订单的状态获取订单的状态标题
        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]

        # 获取订单商品信息
        order_skus = OrderGoods.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            # 计算商品的小计
            amount = order_sku.count * order_sku.price
            # 动态给order_sku增加属性amount,保存商品小计
            order_sku.amount = amount
            # 动态给order增加属性order_skus, 保存订单商品信息
        order.order_skus = order_skus

        # 使用模板
        return render(request, "order_comment.html", {"order": order})

    def post(self, request, order_id):
        """处理评论内容"""
        user = request.user
        print('--0--')
        # 校验数据
        if not order_id:
            return redirect(reverse('user:order', args=[1]))
        print('---1---')
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("user:order", args=[1]))
        print('---2---')
        # 获取评论条数
        total_count = request.POST.get("total_count")
        total_count = int(total_count)
        print('---3---')
        # 循环获取订单中商品的评论内容 1-total_count
        for i in range(1, total_count + 1):
            # 获取评论的商品的id
            sku_id = request.POST.get("sku_%d" % i)  # sku_1 sku_2
            # 获取评论的商品的内容
            content = request.POST.get('content_%d' % i, '')  # cotent_1 content_2 content_3
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue
            print('---4---')
            order_goods.comment = content
            order_goods.save()

        order.order_status = 5  # 已完成
        order.save()
        print('---5---')
        return redirect(reverse("user:order", args=[1]))

