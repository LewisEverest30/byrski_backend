from django.core.validators import RegexValidator
from django.conf import settings



# ====================常量==============================
SERVICES = {
    '滑雪门票': {
        'service': '滑雪门票',
        'icon': settings.MEDIA_URL + 'icon/icon3.png'
    },
    '往返车票': {
        'service': '往返车票',
        'icon': settings.MEDIA_URL + 'icon/icon4.png'
    },
    '酒店住宿': {
        'service': '酒店住宿',
        'icon': settings.MEDIA_URL + 'icon/icon5.png'
    },
    '雪具租赁': {
        'service': '雪具租赁',
        'icon': settings.MEDIA_URL + 'icon/icon1.png'
    },
    '人身保险': {
        'service': '人身保险',
        'icon': settings.MEDIA_URL + 'icon/icon2.png'
    },
}

SERVICE_NAMES = [i['service'] for i in list(SERVICES.values())]
SERVICE_STRING_RE = '|'.join(SERVICE_NAMES)
SERVICE_STRING_SHOW = ' '.join(SERVICE_NAMES)


ACTIVITY_GUIDE = {
    0: '未使用活动指引',
    1: '前往大厅租赁区领取雪具',
    2: '在存储柜存放行李，穿戴雪具',
    3: '刷卡过闸机进入雪场',
    4: '新手指南：安全摔倒与站起',
    5: '结束滑雪归还雪卡和装备',
}

# ============================================================



# =========================================正则检查器=======================================
pattern_slope = r'^(初级道\-\d+) (中级道\-\d+) (高级道\-\d+)$'
Validator_slope = RegexValidator(pattern_slope, '请用形如这样的格式来表示雪道的组成: "初级道-3 中级道-5 高级道-2"')

pattern_schedule = r'^(\S+:\S+ )*(\S+:\S+)$'
Validator_schedule = RegexValidator(pattern_schedule, '请用形如这样的格式来表示行程安排: "第一天9点:出发 第一天11点:到达 第一天16点:返程"')

pattern_service = fr'^(({SERVICE_STRING_RE}) )*({SERVICE_STRING_RE})$'
Validator_service = RegexValidator(pattern_service, '请使用空格分隔各个服务。可选服务有：'+SERVICE_STRING_SHOW)




# =======================================================================================

