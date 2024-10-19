from django.core.validators import RegexValidator
from django.conf import settings



# ===================能提供的服务==============================
SERVICES = [
    {
        'service': '滑雪门票',
        'icon': settings.MEDIA_URL + ''
    },    
    {
        'service': '往返车票',
        'icon': settings.MEDIA_URL + ''
    },
    {
        'service': '酒店住宿',
        'icon': settings.MEDIA_URL + ''
    },
    {
        'service': '雪具租赁',
        'icon': settings.MEDIA_URL + ''
    },
    {
        'service': '人身保险',
        'icon': settings.MEDIA_URL + ''
    },
]

SERVICE_NAMES = [i['service'] for i in SERVICES]
SERVICE_STRING_RE = '|'.join(SERVICE_NAMES)
SERVICE_STRING_SHOW = ' '.join(SERVICE_NAMES)

# ============================================================



# =========================================正则检查器=======================================
pattern_slope = r'^(初级道\-\d+) (中级道\-\d+) (高级道\-\d+)$'
Validator_slope = RegexValidator(pattern_slope, '请用形如这样的格式来表示雪道的组成: "初级道-3 中级道-5 高级道-2"')

pattern_schedule = r'^(\S+:\S+ )*(\S+:\S+)$'
Validator_schedule = RegexValidator(pattern_schedule, '请用形如这样的格式来表示行程安排: "第一天9点:出发 第一天11点:到达 第一天16点:返程"')

pattern_service = fr'^({SERVICE_STRING_RE} )*{SERVICE_STRING_RE}'
Validator_service = RegexValidator(pattern_service, '请使用空格分隔各个服务。可选服务有：'+SERVICE_STRING_SHOW)




# =======================================================================================

