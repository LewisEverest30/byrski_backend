import datetime
from .models import Activity
import datetime

def set_activity_expire():


    try:
        acti_objs = Activity.objects.filter(signup_ddl_d__lt = datetime.date.today())
        acti_objs.update(registration_status=False)
        return
    except Exception as e:
        print(str(datetime.datetime.now()), repr(e))
        return

