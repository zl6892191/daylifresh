from django.contrib import admin
from apps.goods.models import GoodsType,IndexPromotionBanner,GoodsSKU,Goods,GoodsImage,IndexGoodsBanner,IndexTypeGoodsBanner



# 首页促销信息管理类
class Fater(admin.ModelAdmin):
    # 重写父类save_model的方法
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        from celery_tasks.tasks import mkdir_index
        # 只要执行重写或发送便给celery发送任务
        mkdir_index.delay()
        print('任务以发送')

    def delete_model(self, request, obj):
        # 管理员只要有删除操作便发送celery操作
        super().delete_model(request, obj)
        from celery_tasks.tasks import mkdir_index
        mkdir_index.delay()
# 商品管理页面
class GoodsTypeAdmin(Fater):
    pass
# 商品促销管理页面
class IndexPromotionBannerAdmin(Fater):
    pass
# 商品轮播管理页面
class IndexGoodsBannerAdmin(Fater):
    pass
# 商品分类展示管理页面
class IndexTypeGoodsBannerAdmin(Fater):
    pass
admin.site.register(GoodsType,GoodsTypeAdmin)
admin.site.register(IndexPromotionBanner,IndexPromotionBannerAdmin)
admin.site.register(IndexGoodsBanner,IndexGoodsBannerAdmin)
admin.site.register(IndexTypeGoodsBanner,IndexTypeGoodsBannerAdmin)

# Register your models here.
