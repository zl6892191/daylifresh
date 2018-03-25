from django.shortcuts import render,redirect
from django.views.generic import View
from django.http import HttpResponse,JsonResponse
from apps.goods.models import GoodsSKU
from django_redis import get_redis_connection

class CartAddView(View):
    def post(self,request):
        # 获取POST提交的数据
        user =request.user
        sku_id = request.POST.get('good_id')
        count = request.POST.get('count')
        # 判断用户是否登录
        if not user.is_authenticated():
            return JsonResponse({'res':0,'errmsg':'请先登录'})
        # 判断数据的完整性
        if not all([sku_id,count]):
            return JsonResponse({'res':1,'errmsg':'数据无效'})
        # 添加的数据不合法
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res':2,'errmsg':'提交的参数只能为数字'})
        # 判断添加的数量是否大于库存量
        sku = GoodsSKU.objects.get(id = sku_id)
        if count >sku.stock :
            return JsonResponse({'res':3,'errmsg':'添加数量大于库存量'})
        # 校验完成，添加数量进redis数据库
        # 链接数据库
        connt = get_redis_connection('default')
        # 拼接键
        sku_key = 'cart_%s'% user.id
        # 拿出值，判断之前是否有值存在
        sku_val = connt.hget(sku_key,sku_id)
        if sku_val:
            count += int(sku_val)
        # 相加后添加进redis数据库
        connt.hset(sku_key, sku_id, count)
        # 获取用户购物车中商品的条目数
        cart_count = connt.hlen(sku_key)
        # 返回处理数据
        return JsonResponse({'res':4,'cart_count':cart_count,'errmsg':'数据以保存成功！'})
# Create your views here.



# 购物车页面
class CartView(View):
    def get(self,request):
        user = request.user
        # 从数据库redis中获取商品的数目和ID
        connt = get_redis_connection('default')
        # 拼接键
        sku_key = 'cart_%d' % user.id
        # 根据键取数据库里面的值
        cart_dict = connt.hgetall(sku_key)
        a = cart_dict
        # 合计和总商品数
        total_count = 0
        total_amount = 0
        sku_list = []
        # 遍历字典分别拿出里面的键和值 cart_dict={'1':'3','2':'3','3':'3'}
        for sku_id,count in cart_dict.items():
            # 遍历出商品ID拿出他额信息
            sku = GoodsSKU.objects.get(id = sku_id)
            # 商品小计
            amount = sku.price * int(count)
            # 给对象sku添加属性
            sku.amount = amount  # 商品小计
            sku.count = count  # 商品的数量
            sku_list.append(sku)  # 添加对象进列表

            # 累加计算商品中的总数目和总价格
            total_amount += amount
            total_count += int(count)
            # 组织上下文
        context = {

                'sku_list':sku_list,
                'total_amount':total_amount,
                'total_count':total_count
            }

        return render(request,'cart.html',context)



class CartUpdateView(View):
    def post(self,request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})

        # 接收参数
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 参数校验
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '参数不完整'})

        # 校验商品id requests urllib
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '商品信息错误'})

        # 校验商品数量count
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 3, 'errmsg': '商品数量必须为有效数字'})

        # 业务处理: 购物车记录更新
        # 获取链接
        conn = get_redis_connection('default')

        # 拼接key
        cart_key = 'cart_%d' % user.id

        # 校验商品的库存量
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})

        # 更新用户购物车中商品数量
        # hset(key, field, value)
        conn.hset(cart_key, sku_id, count)

        # 计算用户购物车中商品的总件数
        # hvals(key)
        cart_vals = conn.hvals(cart_key)

        total_count = 0
        for val in cart_vals:
            total_count += int(val)

        # 返回应答
        return JsonResponse({'res': 5, 'total_count': total_count, 'errmsg': '更新购物车记录成功'})


class CartDeleteView(View):
    def post(self,request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})

        # 接收参数
        sku_id = request.POST.get('sku_id')
        print('---11---')
        print(sku_id)
        # 参数校验
        if not all([sku_id]):
            return JsonResponse({'res': 1, 'errmsg': '参数不完整'})

        # 校验商品id requests urllib
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '商品信息错误'})

        # 业务处理: 删除用户的购物车记录
        # 获取链接
        conn = get_redis_connection('default')

        # 拼接key
        cart_key = 'cart_%d' % user.id

        # 删除记录
        # hdel(key, *fields)
        conn.hdel(cart_key, sku_id)

        # 计算用户购物车中商品的总件数
        # hvals(key)
        cart_vals = conn.hvals(cart_key)

        total_count = 0
        for val in cart_vals:
            total_count += int(val)

        # 返回应答
        return JsonResponse({'res': 3, 'total_count': total_count, 'errmsg': '删除购物车记录成功'})