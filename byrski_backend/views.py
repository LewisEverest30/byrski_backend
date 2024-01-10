import json
from django.http import JsonResponse, HttpResponse

def test_view(request):
    print(request.GET)
    return HttpResponse('this is a test page')

ret = '''
<form method='post' action='/testpost'>用户名: <input type='text' name='uname'><input type='submit' value='提交'></form>
'''

def testpost_view(request):
    if request.method == "GET":
        return HttpResponse(ret)
     
    elif request.method == "POST":
        uname = request.POST["uname"]
        if uname!='':
            print(uname)
            return HttpResponse("post success")
        else:
            return HttpResponse("uname null")
          


