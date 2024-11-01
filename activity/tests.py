

SERVICES = [
    {
        'service': '滑雪门票',
    },    
    {
        'service': '往返车票',
    },
    {
        'service': '酒店住宿',
    },
    {
        'service': '雪具租赁',
    },
    {
        'service': '人身保险',
    },
]

SERVICE_NAMES = [i['service'] for i in SERVICES]
SERVICE_STRING_RE = '|'.join(SERVICE_NAMES)
SERVICE_STRING_SHOW = ' '.join(SERVICE_NAMES)

# ============================================================



# =========================================正则检查器=======================================

pattern_service = fr'^({SERVICE_STRING_RE} )*{SERVICE_STRING_RE}$'

print(pattern_service)