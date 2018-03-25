from django.shortcuts import render
from django.views.generic import View
from apps.goods.models import Goods,GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner,GoodsSKU
from django_redis import get_redis_connection
from django.core.cache import cache
from apps.order.models import OrderGoods
from django.core.paginator import Paginator


# http://127.0.0.1:8000
# /
class IndexView(View):
    """首页"""
    def get(self, request):
        """显示"""
        # 判断是否有缓存
        context =cache.get('chache_data')
        if context is None:
            # 获取商品的分类信息
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
        # 导入缓存模块
            context = {
            'types': types,
            'index_banner': index_banner,
            'promotion_banner': promotion_banner,
            'cart_count': 0
            }

        # 设置缓存的数据
            cache.set('cache_data', context, 3600)
        # 组织模板上下文
        cart_count = 0
        # 判断用户是否已登录
        if request.user.is_authenticated():
            conn = get_redis_connection('default')
            cart_key = 'cart_%s'%request.user.id
            cart_count = conn.hlen(cart_key)
        # 更新字典的数据
        context.update(cart_count=cart_count)

        # 使用模板
        return render(request, 'index.html', context)


# 商品详情处理视图
class DetailView(View):
    def get(self,request,good_id):

        # 获取模型数据
        try:
            connt = GoodsSKU.objects.get(id=good_id)
        except GoodsSKU.DoesNotExist:
            return render(request ,'index.html',{'errmsg':'参数有误'})

        # 最新商品推荐
        news_goods =GoodsSKU.objects.filter(type=connt.type).order_by('-create_time')[:2]
        # 获取最新的评论
        order_skus = OrderGoods.objects.filter(sku=connt).order_by('-update_time')
        # 获取同一商品SPU的商品
        sam_skus = Goods.objects.filter(name=connt.goods).exclude(id=connt.id)
        type1 = GoodsType.objects.all()

        # 判断用户是否登录，如过登录显示购物车数量
        cart_count = 0
        if request.user.is_anonymous():
            count = get_redis_connection('default')
            cont_key = 'cart_%s'%request.user.id
            cart_count=count.hlen(cont_key)
        # 添加用户历史浏览记录
            history_key = 'history_%s'%request.user.id
            # 删除列表里面相同的元素
            count.lrem(history_key,0,good_id)
            # 在添加进列表
            count.lpush(history_key,good_id)
            # 保存前5个值
            count.ltrim(history_key,0,4)
        # 组织模板上行文
        context ={
            'connt' : connt,
            'news_goods':news_goods,
            'order_skus':order_skus,
            'sam_skus':sam_skus,
            'cart_count':cart_count,
            'type1': type1
        }
        # 发送数据
        return render(request,'detail.html',context)

# 商品列表处理视图
class ListDateView(View):
    # 获取点击事件get数据拿到类数据
    def get(self,request,good_id,page):


        # 拿到类型的数据
        type = GoodsType.objects.get(id = good_id)
        # 拿到所有商品信息
        types = GoodsSKU.objects.all()
        # 获取排序方式
        # sort=price: 按照商品的价格(price)从低到高排序
        # sort=hot: 按照商品的人气(sales)从高到低排序
        # sort=default: 按照默认排序方式(id)从高到低排序
        sort = request.GET.get('sort')
        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')
        # 获取最新商品信息
        news_goods=GoodsSKU.objects.filter(type=type).order_by('-create_time')[0:2]
        # 拿到全部商品类
        type1 = GoodsType.objects.all()
        # 获取分页
        paginator = Paginator(skus,2)
        page = int(page)
        if page > paginator.num_pages:
            page = 1
        # 获取page的内容
        page_skus = paginator.page(page)
        num_pages = paginator.num_pages
        pages = range(1,num_pages+1)
        # 显示数据
        context = {
            'skus':skus,
            'type':type,
            'types':types,
            'news_goods':news_goods,
            'sort':sort,
            'type1':type1,
            'page_skus':page_skus,
            'pages':pages
        }
        return render(request,'list.html',context)










