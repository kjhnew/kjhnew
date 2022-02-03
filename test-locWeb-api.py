import requests
import json
import psycopg2

import time
#import csv
import datetime
from datetime import timedelta, date
from dateutil.parser import *
import logging, sys, io

import cv2
import numpy as np
import base64
import pickle
from PIL import Image

jstr_saved = ''

def im2json(im):
    """Convert a Numpy array to JSON string"""
    imdata = pickle.dumps(im)
    return base64.b64encode(imdata).decode('ascii')
    jstr = json.dumps({"image": base64.b64encode(imdata).decode('ascii')})
    return jstr

def json2im(jstr):
    """Convert a JSON string back to a Numpy array"""
    imdata = base64.b64decode(jstr)
    return pickle.loads(imdata)
    load = json.loads(jstr)
    imdata = base64.b64decode(load['image'])
    im = pickle.loads(imdata)
    return im

img = cv2.imread('E:\\works\\ETRI\\photo\\200014.png')
#img = cv2.imread('C:\\works\\ETRI\\btn-bell-on.png')
img_jstr1 = im2json(img)
jstr_saved = img_jstr1
#print(img_jstr)
#cv2.imshow('frame', img)

URLBase = 'http://localhost:8091/api'
#URLBase = 'http://192.168.219.204:8091/api'
#URLBase = 'http://124.61.24.153:48091/api'

headers = {'Content-Type': 'application/json; charset=utf-8'} 
cookies = {'session_id': 'sorryidontcare'} 
# res = requests.get(URL, headers=headers, cookies=cookies)

##########################################
# Postgresql API


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'prj_strong_ksoc',
        'USER': 'postgres',
        'PASSWORD': 'h42020)(',
        'HOST': 'dev.h4tech.co.kr',     # 192.168.219.204
        'PORT': '45432',                # '5432',     
    }
}

TB_USER = "tb_user"

TB_PT_ITEMS = "tb_pt_items"
TB_PT_ITEMS4GAME = "tb_pt_items4game"
TB_PT_WEEKLY_PERSONAL = "tb_pt_weekly_personal"
TB_PT_WEEKLY_PLAN = "tb_pt_weekly_plan"
TB_PT_WEEKLY_PLAN_DATA = "tb_pt_weekly_plan_data"

TB_GAMES = "tb_games"

TB_PHYSICAL_MEASURE_CAT = "tb_physical_measure_cat"
TB_PHYSICAL_MEASURE_VALUES = "tb_physical_measure_values"
TB_PHYSICAL_MEASURE_ITEMS = "tb_physical_measure_items"
TB_PHYSICAL_MEASURE_PERSONAL = "tb_physical_measure_personal"

USER_TYPE = {'admin':0, 'coach':1, 'player':10}
DAYOFWEEK = {'일요일':6, '월요일':0, '화요일':1, '수요일':2, '목요일':3, '금요일':4, '토요일':5,
    '일':6, '월':0, '화':1, '수':2, '목':3, '금':4, '토':5}
DAYOFWEEK2STR = {'6':'일요일', '0':'월요일', '1':'화요일', '2':'수요일', '3':'목요일', '4':'금요일', '5':'토요일',}

DAYTIME = {'당일':0, '조조':1, '오전':2, '오후':3, '야간':4}
DAYTIME2STR = {'0':'당일', '1':'조조', '2':'오전', '3':'오후', '4':'야간'}

# H4T Database server - WAN
#conn = psycopg2.connect(host='dev.h4tech.co.kr', dbname='prj_strong_ksoc', user='postgres', \
conn = psycopg2.connect(host='124.61.24.153', dbname='prj_strong_ksoc', user='postgres', \
    password='h42020)(', port='45432')
print(conn)

# local
#conn = psycopg2.connect(host='192.168.219.204', dbname='prj_strong_ksoc', user='postgres', password='h42020)(', port='5432')

cur = conn.cursor() # 성능문제 고려해야 할 듯

############################################################################################################
from functools import wraps

def as_json(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        res = f(*args, **kwargs)
        res = json.dumps(res, ensure_ascii=False).encode('utf8')
        return Response(res, content_type='application/json; charset=utf-8')
    return decorated_function

class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, complex):
            return [obj.real, obj.imag]
        return json.JSONEncoder.default(self, obj)

############################################################################################################
""" common routine """
def makeSuccessResponseMsg(msg):

    return {'result':'Y', 'msg':msg}


def makeErrorResponseMsg(msg):
    data = {'result':'N', 'msg':msg}
    return data
    res = json.dumps(data, ensure_ascii=False).encode('utf8')
    return Response(res, content_type='application/json; charset=utf-8')


def makeErrorResponseMsgResponse(msg):
    data = {'result':'N', 'msg':msg}
    res = json.dumps(data, ensure_ascii=False).encode('utf8')
    return Response(res, content_type='application/json; charset=utf-8')


timeFmt = "%Y-%m-%d %H:%M:%S.%f"   # '2021-03-20 21:00:30.361'
dateFmt = "%Y-%m-%d"   # '2021-03-20'
def str2date(strDt):
    dt = datetime.datetime.strptime(strDt, dateFmt)
    return dt


def date2str(date_):
    return datetime.datetime.strftime(date_, dateFmt)
    #datetime.now().date().strftime("%Y-%m-%d")


def datetime2str(date_time):
    return datetime.datetime.strftime(date_time, timeFmt)

############################################################################################################
""" 기본 DB service function """

def ptid2ptname(cur, ptid):
    query = 'SELECT ptname FROM ' + TB_PT_ITEMS + ' WHERE ptid=%s'
    cur.execute(query, (ptid,))
    r = cur.fetchone()
    if r == None:
        return ''
    else:
        return r[0]


############################################################


def get_photo(cur, userid):

    imdata = None
    query = 'SELECT photo FROM ' + TB_USER + ' WHERE userid=%s '
    print('query = ', query)
    cur.execute(query, (userid,))
    r = cur.fetchone()

    if r != None:
        bytedata = r[0].tobytes()
        # print('len of photo r[10] = ', len(r[10]))
        # print('len of photo bytedata = ', len(bytedata))
        imdata = base64.b64encode(bytedata).decode('ascii')

    return imdata



def get_photostr(cur, userid):

    imdata = None
    query = 'SELECT photostr FROM ' + TB_USER + ' WHERE userid=%s '
    print('query = ', query)
    cur.execute(query, (userid,))
    r = cur.fetchone()
    print('TB_USER ', r)
    if r != None:
        imdata = r[0]

    return imdata



def bytea2data(byteafromdb):

    imdata = None

    if byteafromdb != None:
        bytedata = byteafromdb.tobytes()
        imdata = base64.b64encode(bytedata).decode('ascii')

    return imdata

###########################################################################
# /api
URL = URLBase + '/collect'
# 측위자원수집 관리
'''
data = {"site_id": "*", "building_id": "3004", "floor": "*"}			
print("\ndata = ", data)
apiurl = '/get-dataset-list'
res = requests.post(URL+apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 측위자원수집 데이터세트 목록({apiurl}) == > {res.text}')


data = {"site_id": "*", "building_id": "3004", "floor": "*"}			
print("\ndata = ", data)
apiurl = '/get-ppdataset-list'
res = requests.post(URL+apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 측위자원수집 후처리 데이터세트 목록({apiurl}) == > {res.text}')


data = {"site_id": "*"}			
print("\ndata = ", data)
apiurl = '/get-dataset-filter'
res = requests.post(URL+apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 측위자원 필터 목록({apiurl}) == > {res.text}')
'''

data = {"idx": "18"}			
print("\ndata = ", data)
apiurl = '/get-dataset-details'
res = requests.post(URL+apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 측위자원 상세정보({apiurl}) == > {res.text}')






#exit(0)

#data = Login_post(data)
#print("result ====> ", data['result'], data['game'])
''' 
res = requests.post(URL+'/login', json=data, headers=headers)
print('\n>>>>>>> login post 선수 로그인(정상):', res.text)
data = json.loads(res.text)

if data['result'] == 'Y':
    jstr1 = data['userinfo']['photo']
    print('JSTR ################## >> ', jstr1)
    if jstr1 != None:
        im2 = json2im(jstr1)
        cv2.imshow(data['userinfo']['name'], im2)
        #waits for user to press any key 
        #(this is necessary to avoid Python kernel form crashing)
        cv2.waitKey(0) 
        #closing all open windows 
        cv2.destroyAllWindows()
else:
    print('login failed!!!')

exit(0)
''' 


####################################################################
# /api/pm
URL = URLBase + '/pm'
''' 
# /player-pmlist
params = {'userid': '김태권'} 
print('\n params = ', params)
res = requests.get(URL+'/player-pmlist', params=params)
print('>>>>>> player-pmlist get 데이터 2개 이상 있는 경우: ', res.text)


params = {'userid': '김태권a'} 
print('\n params = ', params)
res = requests.get(URL+'/player-pmlist', params=params)
print('>>>>>> player-pmlist get 데이터 없는 경우: ', res.text)


# /player get
params = {'userid': '김태권aa', 'dt':'2021-05-04'} 
print('\n params = ', params)
res = requests.get(URL+'/player', params=params)
print('>>>>>> player get 선수 데이터 없는 경우: ', res.text)


params = {'userid': '김태권', 'dt':'2021-02-04'} 
print('\n params = ', params)
res = requests.get(URL+'/player', params=params)
print('>>>>>> player get 해당 일자 데이터 없는 경우: ', res.text)


params = {'userid': '김태권'} 
print('\n>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> player get ')
print(' params = ', params)
res = requests.get(URL+'/player', params=params)
print('>>>>>> player get 날자 안보낸 경우: ', res.text)

params = {'userid': '김태권', 'dt':'2021-05-03'} 
print('\n>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> player get ')
print(' params = ', params)
res = requests.get(URL+'/player', params=params)
print('>>>>>> player get 해당 일자 데이터 있음: ', res.text)




# /player post
data = {'userid': '김태권', 'dt':'2021-05-11', 'pms':[
            {
                "pmid":"000",
                "pmvalue1":'20',
                "pmvalue2":'40.5'
            },
            {
                "pmid":"001",
                "pmvalue1":'20',
                "pmvalue2":'50'
            },
            {
                "pmid":"020",
                "pmvalue3":'1000'
            },
            {
                "pmid":"030",
                "pmvalue3":'1000'
            },
        ]
}
print('\n>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> player post ')
print(' data = ', data)
res = requests.post(URL+'/player', json=data, headers=headers)
print('  >>>>>>> player post 추가:', res.text)

# /player delete
params = {'userid': '김태권', 'dt':'2021-05-11'} 
print('\n params = ', params)
res = requests.delete(URL+'/player', params=params)
print('>>>>>> player delete 추가한 일자 삭제 : ', res.text)



data = {'userid': '김태권', 'dt':'2021-05-10', 'pms':[
            {
                "pmid":"000",
                "pmvalue1":'25',
                "pmvalue2":'45.5'
            },]
}
print('\n data = ', data)
res = requests.post(URL+'/player', json=data, headers=headers)
print('>>>>>>> player post 갱신:', res.text)


data = {'userid': '김태권cd', 'dt':'2021-05-04', 'pms':[
            {
                "pmid":"000",
                "pmvalue1":'25',
                "pmvalue2":'45.5'
            },]
}
print('\n data = ', data)
res = requests.post(URL+'/player', json=data, headers=headers)
print('>>>>>>> player post 갱신 없는 선수:', res.text)


data = {'userid': '김태권cc', 'dt':'2021-05-11', 'pms':[
            {
                "pmid":"000",
                "pmvalue1":'25',
                "pmvalue2":'45.5'
            },]
}
print('\n data = ', data)
res = requests.post(URL+'/player', json=data, headers=headers)
print('>>>>>>> player post 갱신 없는 일자:', res.text)


# /player delete
params = {'userid': '김태권', 'dt':'2021-05-04'} 
res = requests.delete(URL+'/player', params=params)
print('\n>>>>>> player delete : ', res.text)
'''

####################################################################
# /api/pt
URL = URLBase + '/pt'

'''
# /pts-catlist get
res = requests.get(URL+'/pts-catlist')
print('\n>>>>>> /pts-catlist get 트레이닝 종목 전체 카테고리 목록: ', res.text)

# /pts-cat get
params = {'cat1': 'Calfs'} 
print('\n params = ', params)
res = requests.get(URL+'/pts-cat', params=params)
print('>>>>>> /pts-cat get 특정 카테고리 Calfs의 트레이닝 종목 목록: ', res.text)

# /pts-cat get
params = {} 
print('\n params = ', params)
#PtPtsCat_get(params)
res = requests.get(URL+'/pts-cat')#, params=params)
print('>>>>>> /pts-cat get 모든 카테고리의 트레이닝 종목 목록: ', res.text)



# /pts-ptcat get
params = {'ptid': '01002'} 
print("\n data = ", params)
res = requests.get(URL+'/pts-ptcat', params=params)
print('>>>>>> /pts-ptcat get 특정종목의 카테고리는?: ', res.text)

# /pts-cat ptget
params = {} 
print("\n data = ", params)
res = requests.get(URL+'/pts-ptcat', params=params)
print('>>>>>> /pts-ptcat get 전체종목 카테고리: ', res.text)
'''

''' 
# /pts-game get
params = {'game': '레스링'} 
print("\n data = ", params)
res = requests.get(URL+'/pts-game', params=params)
print(' >>>>>> /pts-game get 경기종목에 포함된 트레이닝 종목: ', res.text)

# /pts-game post
data = {'game': '레스링', 'pts':[
            {
                "ptid":"00001",
                "ptname":"abdo_bar-01",
                "numoftimes":'10',
                #"weight":'50.5'
            },
            {
                "ptid":"00002",
                "ptname":"abdo_bar-02",
                "numoftimes":'',
                "weight":'44'
            },
            {
                "ptid":"01004",
                "ptname":"calfA_bdum-04",
                "numoftimes":'10',
                "weight":'44'
            },
            {
                "ptid":"02001",
                "ptname":"back_bar-01",
                "numoftimes":'10',
                "weight":'50'
            },
            ]
        }

print("\n data = ", data)
res = requests.post(URL+'/pts-game', json=data, headers=headers)
print('>>>>>>> /pts-game post 레스링에 트레이닝 종목 4개 설정:', res.text)


# /pts-game get
params = {'game': '레스링'} 
print("\n data = ", params)
res = requests.get(URL+'/pts-game', params=params)
print(' >>>>>> /pts-game get 설정 결과 - 4개종목: ', res.text)

data = {'game': '레스링', 'pts':[
            {
                "ptid":"00001",
                "ptname":"abdo_bar-01",
                "numoftimes":'10',
                #"weight":'50.5'
            },
            # {
            #     "ptid":"00002",
            #     "ptname":"abdo_bar-02",
            #     "numoftimes":'',
            #     "weight":'44'
            # },
            # {
            #     "ptid":"01004",
            #     "ptname":"calfA_bdum-04",
            #     "numoftimes":'10',
            #     "weight":'44'
            # },
            {
                "ptid":"02001",
                "ptname":"back_bar-01",
                "numoftimes":'10',
                "weight":'50'
            },
            ]
        }

print("\n data = ", data)
res = requests.post(URL+'/pts-game', json=data, headers=headers)
print('>>>>>>> /pts-game post 2개 종목 제외하고 설정:', res.text)

# /pts-game get
params = {'game': '레스링'} 
print("\n data = ", params)
res = requests.get(URL+'/pts-game', params=params)
print(' >>>>>> /pts-game get 설정 결과 - 2개종목: ', res.text)
''' 


'''
# /pts-game get
params = {'game': '레스링', 'cat1':'abdominals'} 
print("\n data = ", params)
res = requests.get(URL+'/pts-game', params=params)
print(' >>>>>> /pts-game get 경기종목에 포함된 특정 카테고리 트레이닝 종목: ', res.text)



data1 = {'game': '태권도', 'pts':[
            {
                "ptid":"02002",
                "ptname":"back_bar-02",
                "numoftimes":'10',
                "weight":'50.5'
            },]
}
print("\n data = ", data1)
res = requests.post(URL+'/pts-game', json=data1, headers=headers)
print('>>>>>>> /pts-game post 태권도에 트레이닝 종목 일부 추가:', res.text)


params = {'game': '태권도', 'ptid':'00001', }
print("\n data = ", params)
res = requests.delete(URL+'/pts-game', params=params)
print('>>>>>>> /pts-game post 태권도에 특정 트레이닝 종목 삭제:', res.text)


params = {'game': '태권도', 'ptid':'00551', }
print("\n data = ", params)
res = requests.delete(URL+'/pts-game', params=params)
print('>>>>>>> /pts-game post 태권도에 없는 종목 삭제:', res.text)


params = {'game': '태권도'} 
print("\n data = ", params)
res = requests.get(URL+'/pts-game', params=params)
print(' >>>>>> /pts-game get 경기종목에 포함된 트레이닝 종목: ', res.text)

params = {'game': '태권도', 'ptid':'', }
print("\n data = ", params)
res = requests.delete(URL+'/pts-game', params=params)
print('>>>>>>> /pts-game post 태권도에 특정 트레이닝 종목 전체 삭제:', res.text)

params = {'game': '태권도'} 
print("\n data = ", params)
res = requests.get(URL+'/pts-game', params=params)
print(' >>>>>> /pts-game get 경기종목에 포함된 트레이닝 종목: ', res.text)

print("\n data = ", data)
res = requests.post(URL+'/pts-game', json=data, headers=headers)
print('>>>>>>> /pts-game post 태권도에 트레이닝 종목 다시 추가:', res.text)

params = {'game': '태권도'} 
print("\n data = ", params)
res = requests.get(URL+'/pts-game', params=params)
print(' >>>>>> /pts-game get 경기종목에 포함된 트레이닝 종목: ', res.text)

'''


####################################################################
# /api/pt/plan
URL = URLBase + '/pt/plan'

''' 
def temporary_get(userid):

    data = {}
    dt = datetime.datetime.now()
    dtstr = datetime2str(dt)

    query = 'SELECT * FROM ' + TB_PT_WEEKLY_PLAN + ' WHERE userid=%s '
    cur.execute(query, (userid, ))
    rec = cur.fetchone()
    if rec == None:
        data = makeErrorResponseMsg('NO DATA')

    else:
        nameset = rec[3]
        dtbegin = date2str(rec[4])
        dtend = date2str(rec[5])

        query = 'SELECT * FROM ' + TB_PT_WEEKLY_PLAN_DATA + ' WHERE userid=%s '
        print("query  =", query)
        cur.execute(query, (userid,))
        records = cur.fetchall()
        print(records)
        weeklyplan = {}
        for i in range(0, 6):
            weeklyplan[DAYOFWEEK2STR[str(i)]] = {}
            
        print('weeklyplan 0 = ', weeklyplan)

        for r in records:
            ptid = r[4]
            onermpercent = str(r[5])
            param1 = str(r[6])
            param2 = str(r[7])
            param3 = str(r[8])
            ptname = ptid2ptname(cur, ptid)
            aplan = {'ptid':ptid, 'ptname': ptname, 'param1':param1, 'param2':param2, 'param3':param3}

            dayofweekstr = DAYOFWEEK2STR[str(r[2])]     # '월요일'
            weeklyplan[dayofweekstr]['onermpercent'] = onermpercent
            #if weeklyplan.get(dayofweekstr) == None:     # {}
            #    weeklyplan[dayofweekstr] = {}           # {'월요일':{}}
            print('weeklyplan 1 = ', weeklyplan)
            pttimestr = DAYTIME2STR[str(r[3])]
            weeklyplan[dayofweekstr][pttimestr] = []
            weeklyplan[dayofweekstr][pttimestr].append(aplan)
            print('weeklyplan 2 = ', weeklyplan)

        data = {'result':'Y', 'nameset':nameset, 'dtbegin':dtbegin, 'dtend':dtend, 'weeklyplan':weeklyplan} 

    res = json.dumps(data, ensure_ascii=False).encode('utf8')
    print("response data = ", data)
    #return Response(res, content_type='application/json; charset=utf-8')

    return data



def getOrIfBlank2None(dict, key):
    """
    값이 없으면 None
    값이 '' 이면 None
    """
    val = dict.get(key, None)
    if val == '': val = None
    return val


def temporary_post(datain):

    userid = datain.get('userid')
    nameset = datain.get('nameset')
    dtbegin = datain.get('dtbegin')
    dtend = datain.get('dtend')
    weeklyplan = datain.get('weeklyplan')     # {"월요일":{"조조":[{"ptid":"01142", "param1":"32.5", ...

    dt = datetime.datetime.now()
    dtstr = datetime2str(dt)

    query = 'SELECT * FROM ' + TB_PT_WEEKLY_PLAN + ' WHERE userid=%s '
    cur.execute(query, (userid, ))
    rec = cur.fetchone()
    if rec == None:
        # insert
        query = 'INSERT INTO ' + TB_PT_WEEKLY_PLAN + \
            ' (userid, dt, nameset, dtbegin, dtend) \
            VALUES (%s,%s,%s,%s,%s) '
        print("query  = ", query)
        cur.execute(query, (userid, dtstr, nameset, dtbegin, dtend,))
        conn.commit()
    else:
        #update
        query = 'UPDATE ' + TB_PT_WEEKLY_PLAN + ' SET \
            dt=%s, nameset=%s, dtbegin=%s, dtend=%s WHERE userid=%s '
        print("query  =", query)
        cur.execute(query, (dt, nameset, dtbegin, dtend, userid,))
        conn.commit()

    # TB_PT_WEEKLY_PLAN_DATA에 있는 자료 모두 삭제 후 삽입
    query = 'DELETE FROM ' + TB_PT_WEEKLY_PLAN_DATA + ' WHERE userid=%s '
    print('query = ', query)
    cur.execute(query, (userid,))
    conn.commit()            

    dayarr = list(weeklyplan.keys())    #['월요일', '화요일']
    for day in dayarr:      # {"조조":[{"ptid":"01142", "param1":"32.5", ..., "오전":[{"ptid":}]
        print('day = ', day)
        adayplan = weeklyplan[day]
        print('adayplan = ', adayplan)
        dayofweek = str(DAYOFWEEK[day])
        onermpercent = adayplan.pop('onermpercent', None)
        if onermpercent == '': onermpercent = None

        dayplan_timesarr = list(adayplan.keys())     #["onermpercent", '조조', '오전']
        print(dayplan_timesarr)
        for timestr in dayplan_timesarr:    #['조조', '오전']
            print('timesttr = ', timestr)                
            daytime = str(DAYTIME[timestr])
            adaytimeplan = adayplan[timestr]     # [{"ptid":"01142", "param1":"32.5", "param2":"10", "param3":3}, { }]
            print('adaytimeplan = ', adaytimeplan)
            for aplan in adaytimeplan:       # {"ptid":"01142", "param1":"32.5", "param2":"10", "param3":3}
                if len(aplan.keys()) == 0: continue
                print('aplan = ', aplan)
                ptid = aplan['ptid']
                #param1 = aplan.get('param1', None)  # param1 is a string
                param1 = getOrIfBlank2None(aplan, 'param1')  # param1 is a string
                param2 = getOrIfBlank2None(aplan, 'param2')  # param2 is a string
                param3 = getOrIfBlank2None(aplan, 'param3')  # param3 is a string

                query = 'INSERT INTO ' + TB_PT_WEEKLY_PLAN_DATA + \
                    ' (userid, dayofweek, pttime, ptid, onermpercent, param1, param2, param3) \
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)'
                print('query = ', query)
                cur.execute(query, (userid, dayofweek, daytime, ptid, onermpercent, \
                    param1, param2, param3))
                conn.commit()

    #dummy
    data = {'result':'Y'} 
    res = json.dumps(data, ensure_ascii=False).encode('utf8')
    print("response data = ", data)
    #return Response(res, content_type='application/json; charset=utf-8')

    print(data)
    #return {'result': result}

''''''
# /temporary post
data = {"userid":"김코치", "nameset":["홍길동", "홍길동A", "김태권"],
    "dtbegin":'2021-03-22', "dtend":"2021-04-05", 
    'weeklyplan':{
        "월요일":{"onermpercent":"70",
            "조조":[{"ptid":"02001", "param1":32.5, "param2":10, "param3":3}, { }], 
            "오전":[{"ptid":"00001", "param1":33.5, "param2":10, "param3":3}, { }], 
            "오후":[ ], "야간": [ ]}, 
        "화요일":{"onermpercent":"80",            
            "조조":[{"ptid":"03001", "param1":40.5, "param2":5, "param3":3}, { }], 
            "오전":[{"ptid":"00001", "param1":33.5, "param2":10, "param3":3}, { }], 
            "오후":[ ], "야간": [ ]}, 
        "수요일":{"조조":[ ], "오전":[ ], "오후":[ ], "야간": [ ]}, 
        "목요일":{"조조":[ ], "오전":[ ], "오후":[ ], "야간": [ ]}, 
        "금요일":{"조조":[ ], "오전":[ ], "오후":[ ], "야간": [ ]}, 
        "토요일":{"조조":[ ], "오전":[ ], "오후":[ ], "야간": [ ]}}}

print("\ntemporary post ================================> ")
print('data = ', data)
#print(temporary_post(data))
res = requests.post(URL+'/temporary', json=data, headers=headers)
print('>>>>>>> /temporary post 계획임시저장:', res.text)


# /temporary get
params = {'userid': '김코치'} 
print("\ntemporary get ================================> ")
print('params = ', params)
#print(temporary_get(params['userid']))
res = requests.get(URL+'/temporary', params=params)
print('>>>>>> /temporary get 임시저장 계획 가져오기: ', res.text)

params = {'userid': '김치'} 
print("\ntemporary get ================================> ")
print('params = ', params)
#print(temporary_get(params['userid']))
res = requests.get(URL+'/temporary', params=params)
print('>>>>>> /temporary get 임시저장 계획 가져오기 - 없는 코치: ', res.text)

exit(0)

''' '''

##################################################################################################
def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days + 1)):
        yield start_date + timedelta(n)

def getUserid(cur, name):
    query = 'SELECT userid FROM ' + TB_USER + ' WHERE name=%s '
    cur.execute(query, (name,))
    r = cur.fetchone()
    return r[0] if r != None else None


def ptPlanWeekly_post(datain):
    userid = datain.get('userid')
    nameset = datain.get('nameset')
    dtbegin = datain.get('dtbegin')
    dtend = datain.get('dtend')
    weeklyplan = datain.get('weeklyplan')

    # dtbegin~dtend 사이 각 요일에 해당하는 날짜에 데이터 추가/갱신
    print("date = %s ~ %s" % (dtbegin, dtend))
    date_begin = datetime.datetime.strptime(dtbegin, "%Y-%m-%d").date()  
    date_end = datetime.datetime.strptime(dtend, "%Y-%m-%d").date()
    # 날자 검증
    if date_begin > date_end:
        date_temp = date_end
        date_end = date_begin
        date_begin = date_temp
    print(date_begin, date_end)

    playerset = []  # userid set
    for name in nameset:
        id = getUserid(cur, name)
        if id != None: playerset.append(id)
    #
    print('playerset', playerset)
    for dt in daterange(date_begin, date_end):
        dayofweek = str(dt.weekday())   # '0' ~ '5'
        dtstr = date2str(dt)
        dayofweekstr = DAYOFWEEK2STR[dayofweek] #'월요일'
        adayplan = weeklyplan.get(dayofweekstr)
        if adayplan == None: continue

        for playerid in playerset:
            # 해당 일자의 기존 계획은 모두 삭제
            query = 'DELETE FROM ' + TB_PT_WEEKLY_PERSONAL + ' WHERE userid=%s and dt=%s '
            print('query = ', query)
            cur.execute(query, (playerid, dtstr,))
            conn.commit()  

        onermpercent = adayplan.pop('onermpercent', None)
        if onermpercent != None: onermpercent = str(onermpercent)

        dayplan_timesarr = list(adayplan.keys())     #["onermpercent", '조조', '오전']
        print(dayplan_timesarr)
        for timestr in dayplan_timesarr:    #['조조', '오전']        
            print('timesttr = ', timestr)                
            daytime = str(DAYTIME[timestr]) #'1', 
            adaytimeplan = adayplan[timestr]     # [{"ptid":"01142", "param1":"32.5", "param2":"10", "param3":3}, { }]
            print('adaytimeplan = ', adaytimeplan)
            for aplan in adaytimeplan:       # {"ptid":"01142", "param1":"32.5", "param2":"10", "param3":3}
                if len(aplan.keys()) == 0: continue
                print('aplan = ', aplan)
                ptid = aplan['ptid']
                param1 = aplan.get('param1', None)  # param1 is a string
                if param1 != None: param1 = str(param1)
                param2 = aplan.get('param2', None)
                if param2 != None: param2 = str(param2)
                param3 = aplan.get('param3', None)
                if param3 != None: param3 = str(param3)

                for playerid in playerset:
                    # 해당 일자의 기존 계획은 모두 삭제
                    query = 'DELETE FROM ' + TB_PT_WEEKLY_PERSONAL + ' WHERE userid=%s and dt=%s and dayofweek=%s and pttime=%s '
                    print('query = ', query)
                    cur.execute(query, (playerid, dtstr, dayofweek, daytime,))
                    conn.commit()  

                    query = 'SELECT * FROM ' + TB_PT_WEEKLY_PERSONAL + \
                        ' WHERE userid=%s and dt=%s and dayofweek=%s and pttime=%s and ptid=%s'
                    print('query = ', query)
                    cur.execute(query, (playerid, dtstr, dayofweek, daytime, ptid))
                    r = cur.fetchone()
                    print('record = ', r)
                    if r == None:
                        # insert
                        query = 'INSERT INTO ' + TB_PT_WEEKLY_PERSONAL + \
                            ' (userid, dt, dayofweek, onermpercent, pttime, ptid, param1, param2, param3, useridcoach) \
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) '
                        print("query  = ", query)
                        print(playerid, dtstr, dayofweek, onermpercent, daytime, ptid, param1, param2, param3, userid)
                        cur.execute(query, (playerid, dtstr, dayofweek, onermpercent, daytime, ptid, param1, param2, param3, userid,))
                        conn.commit()
                    else:
                        #update - 실제는 update 할 것 없을 것 (사용되지 않는 코드)
                        assert(False)
                        query = 'UPDATE ' + TB_PT_WEEKLY_PERSONAL + ' SET \
                            onermpercent=%s, param1=%s, param2=%s, param3=%s, useridcoach=%s \
                            WHERE  userid=%s and dt=%s and dayofweek=%s and pttime=%s and ptid=%s '
                        print("query  =", query)
                        cur.execute(query, (onermpercent, param1, param2, param3, userid, playerid, dtstr, dayofweek, daytime, ptid,))
                        conn.commit()

    #dummy
    data = {'result':'Y'} 
    res = json.dumps(data, ensure_ascii=False).encode('utf8')
    print("response data = ", data)
    return data
    #return Response(res, content_type='application/json; charset=utf-8')


# /weekly post
data = {"userid":"박코치", "nameset":["홍길동", "홍길동a", "김태권"],
    "dtbegin":'2021-05-06', "dtend":"2021-05-07", 
    'weeklyplan':{
        "월요일":{"onermpercent":"70",
            "조조":[{"ptid":"02001", "param1":'32.5', "param2":'10', "param3":'3'}, { }], 
            "오전":[{"ptid":"00001", "param2":10, "param3":'3'},], 
            "오후":[ ], }, 
        "화요일":{"onermpercent":"80",            
            "조조":[{"ptid":"03001", "param1":40.5, "param2":5, "param3":3}, { }], 
            "오전":[{"ptid":"00001", "param1":33.5, "param2":10, "param3":3}, { }], 
            "오후":[ ], "야간": [ ]}, 
        "수요일":{"조조":[ ], "오전":[ ], "오후":[ ], "야간": [ ]}, 
        "목요일":{"조조":[ ], "오전":[ ], "오후":[ ], "야간": [ ]}, 
        "금요일":{"onermpercent":"80",            
            "조조":[{"ptid":"03001", "param1":40.5, "param2":5, "param3":3}, { }], 
            "오전":[{"ptid":"00001", "param1":33.5, "param2":10, "param3":3}, { }], 
            "오후":[ ], "야간": [ ]}, 
        "토요일":{"조조":[ ], "오전":[ ], "오후":[ ], "야간": [ ]}}}

print("\nptPlanWeekly_post 1 ================================> ")
print(" data = ", data)
#print(ptPlanWeekly_post(data))
res = requests.post(URL+'/weekly', json=data, headers=headers)
print(' >>>>>>> /weekly post 트레이닝 계획 완료/반영 :', res.text)


data = {"userid":"박코치", "nameset":["홍길동", "홍길동A", "김태권"],
    "dtbegin":'2021-05-05', "dtend":"2021-05-08", 
    'weeklyplan':{
        "월요일":{"onermpercent":"70",
            "조조":[{"ptid":"00002", "param1":'32.5', "param2":'10', "param3":'3'}, 
                {"ptid":"00001", "param2":10, "param3":'3'}], 
            "오전":[{"ptid":"00001", "param2":10, "param3":'3'},], 
            "오후":[ ], }, 
        "목요일":{"onermpercent":"80",            
            "조조":[{"ptid":"03001", "param1":40.5, "param2":5, "param3":3}, { }], 
            "오전":[{"ptid":"00001", "param1":33.5, "param2":10, "param3":3}, { }], 
            "오후":[ ], "야간": [ ]}, 
        "금요일":{"onermpercent":"70",            
            "오전":[{"ptid":"00021", "param1":33.5, "param2":10, "param3":3}, { }]}, 
        "토요일":{"onermpercent":"70",            
            "오전":[{"ptid":"00015", "param1":33.5, "param2":10, "param3":3}, { }]},}}

print("\nptPlanWeekly_post 2 ================================> ")
#print(ptPlanWeekly_post(data))
res = requests.post(URL+'/weekly', json=data, headers=headers)
print('\n>>>>>>> /weekly post 트레이닝 계획 완료/반영(토요일): 없는 선수 포함', res.text)
''' 

'''
##################################################################################################
def weekly_get(datain):

    userid = datain.get('userid')
    name = datain.get('name')
    dtbegin = datain.get('dtbegin')
    dtend = datain.get('dtend')

    # dtbegin 은 월요일로 한정하지 않음.
    # 기간이 1주 이상일 경우를 고려하지 않음

    playerid = getUserid(cur, name)
    # dtbegin~dtend 사이 
    print("date = %s ~ %s" % (dtbegin, dtend))
    date_begin = datetime.datetime.strptime(dtbegin, "%Y-%m-%d").date()  
    date_end = datetime.datetime.strptime(dtend, "%Y-%m-%d").date()
    # 날자 검증
    if date_begin > date_end:
        date_temp = date_end
        date_end = date_begin
        date_begin = date_temp
    print(date_begin, date_end)

    weeklyplan = {}
    for dt in daterange(date_begin, date_end):
        dayofweek = str(dt.weekday())   # '0' ~ '5'
        dayofweekstr = DAYOFWEEK2STR[dayofweek]
        weeklyplan[dayofweekstr] = {}

        dtstr = date2str(dt)
        
        query = 'SELECT * FROM ' + TB_PT_WEEKLY_PERSONAL + \
            ' WHERE userid=%s and dt=%s '
        print('query = ', query)
        cur.execute(query, (playerid, dtstr, ))
        records = cur.fetchall()
        print(records)
        adayplan = {'onermpercent':''}

        for r in records:
            onermpercent = str(r[13]) if r[13] != None else ''
            adayplan['onermpercent'] = onermpercent     # 모든 ptid에 대하여 동일한 것으로 가정함 
            pttime = str(r[4])      # '1'
            pttimestr = DAYTIME2STR[pttime]
            if adayplan.get(pttimestr) == None:
                adayplan[pttimestr] = []
            ptid = r[5]
            ptname = ptid2ptname(cur, ptid)
            param1 = (r[6])
            param2 = (r[7])
            param3 = (r[8])
            if param1 != None: param1 = str(param1)
            if param2 != None: param2 = str(param2)
            if param3 != None: param3 = str(param3)

            aplan = {'ptid':ptid, 'ptnam':ptname, 'param1':param1, 'param2':param2, 'param3':param3}

            if adayplan.get(pttimestr) == None:
                adayplan[pttimestr] = []           
            adayplan[pttimestr].append(aplan)
            print('adayplan[pttimestr] 2 = ', adayplan[pttimestr])

        weeklyplan[dayofweekstr] = adayplan
        print('weeklyplan 2 = ', weeklyplan)

    data = {'result':'Y', 'name':name, 'dtbegin':dtbegin, 'dtend':dtend, 'weeklyplan':weeklyplan} 


    return data


# /personal-weekly get
params = {"userid":"박코치", "name":"홍길동", "dtbegin":'2021-05-03', "dtend":"2021-05-08"}
print("\nPtPlanPersonalWeekly_get 1 ================================> \n params = ", params)
#print(weekly_get(params))
res = requests.get(URL+'/personal-weekly', params=params)
print(' >>>>>>> /personal-weekly get 홍길동의 선택된 1주 트레이닝 계획:', res.text)


params = {"userid":"박코치", "name":"홍길동a", "dtbegin":'2021-05-10', "dtend":"2021-05-15"}
print("\nPtPlanPersonalWeekly_get 2 ================================>  \n params = ", params)
#print(weekly_get(params))
res = requests.get(URL+'/personal-weekly', params=params)
print('>>>>>>> /personal-weekly get 데이터 없는 경우 :', res.text)

exit(0)
''' '''

##################################################################################################
# /personal-weekly post

def weekly_post(datain):
    userid = datain.get('userid')
    name = datain.get('name')
    dtbegin = datain.get('dtbegin')
    dtend = datain.get('dtend')
    weeklyplan = datain.get('weeklyplan')

    playerid = getUserid(cur, name)

    # dtbegin~dtend 사이 각 요일에 해당하는 날짜에 데이터 추가/갱신
    print("date = %s ~ %s" % (dtbegin, dtend))
    date_begin = datetime.datetime.strptime(dtbegin, "%Y-%m-%d").date()  
    date_end = datetime.datetime.strptime(dtend, "%Y-%m-%d").date()
    # 날자 검증
    if date_begin > date_end:
        date_temp = date_end
        date_end = date_begin
        date_begin = date_temp
    print(date_begin, date_end)

    # 해당일자 데이이터를 삭제한 후 추가해야 한다.(업데이트 아님)
    for dt in daterange(date_begin, date_end):
        dayofweek = str(dt.weekday())   # '0' ~ '5'
        dtstr = date2str(dt)
        dayofweekstr = DAYOFWEEK2STR[dayofweek] #'월요일'

        print("=====DAY = ", dt, dayofweekstr)

        # 기존 데이터 삭제
        query = 'DELETE FROM ' + TB_PT_WEEKLY_PERSONAL + ' WHERE userid=%s and dt=%s '
        print('query = ', query)
        cur.execute(query, (playerid, dtstr))
        conn.commit()  

        adayplan = weeklyplan.get(dayofweekstr)
        print('adayplan', adayplan)
        if adayplan == None: continue

        onermpercent = adayplan.pop('onermpercent', None)
        if onermpercent != None: onermpercent = str(onermpercent)

        dayplan_timesarr = list(adayplan.keys())     #["onermpercent", '조조', '오전']
        print(dayplan_timesarr)
        for timestr in dayplan_timesarr:    #['조조', '오전']        
            print('===========timesttr = ', timestr)                
            daytime = str(DAYTIME[timestr]) #'1', 
            adaytimeplan = adayplan[timestr]     # [{"ptid":"01142", "param1":"32.5", "param2":"10", "param3":3}, { }]
            print('adaytimeplan = ', adaytimeplan)
            for aplan in adaytimeplan:       # {"ptid":"01142", "param1":"32.5", "param2":"10", "param3":3}
                if len(aplan.keys()) == 0: continue
                print('aplan = ', aplan)
                ptid = aplan['ptid']
                print('==================ptid', ptid)
                param1 = aplan.get('param1', None)  # param1 is a string
                if param1 != None: param1 = str(param1)
                param2 = aplan.get('param2', None)
                if param2 != None: param2 = str(param2)
                param3 = aplan.get('param3', None)
                if param3 != None: param3 = str(param3)

                # insert
                query = 'INSERT INTO ' + TB_PT_WEEKLY_PERSONAL + \
                    ' (userid, dt, dayofweek, onermpercent, pttime, ptid, param1, param2, param3, useridcoach) \
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) '
                print("query  = ", query)
                print(playerid, dtstr, dayofweek, onermpercent, daytime, ptid, param1, param2, param3, userid)
                cur.execute(query, (playerid, dtstr, dayofweek, onermpercent, daytime, ptid, param1, param2, param3, userid,))
                conn.commit()


data = {"userid":"박코치", "name":"홍길동",
    "dtbegin":'2021-03-22', "dtend":"2021-04-05", 
    'weeklyplan':{
        "월요일":{"onermpercent":60,"조조":[{"ptid":"02001", "param1":32.5, "param2":10, "param3":3}, { }], "오전":[ ], "오후":[ ], "야간": [ ]}, 
        "화요일":{"onermpercent":70,"조조":[ ], "오전":[ ], "오후":[ ], "야간": [ ]}, 
        "수요일":{"onermpercent":70,"조조":[ ], "오전":[ ], "오후":[ ], "야간": [ ]}, 
        "목요일":{"조조":[ ], "오전":[ ], "오후":[ ], "야간": [ ]}, 
        "금요일":{"조조":[ ], "오전":[ ], "오후":[ ], "야간": [ ]}, 
        "토요일":{"조조":[ ], "오전":[ ], "오후":[ ], "야간": [ ]}}}

data = {"userid":"박코치", "name":"홍길동",
    "dtbegin":'2021-05-03', "dtend":"2021-05-08", 
    'weeklyplan':{
        "월요일":{"onermpercent":"70",
            "조조":[{"ptid":"00002", "param1":'32.5', "param2":'10', "param3":'3'}, 
                {"ptid":"00001", "param2":10, "param3":'3'}], 
            "오전":[{"ptid":"00001", "param2":10, "param3":'3'},], 
            "오후":[ ], }, 
        "목요일":{"onermpercent":"80",            
            "조조":[{"ptid":"02001", "param1":40.5, "param2":5, "param3":3}, { }], 
            "오후":[ ], "야간": [ ]}, 
        "금요일":{"onermpercent":"70",            
            "오전":[{"ptid":"00001", "param1":33.5, "param2":10, "param3":3}, { }],
            "오후":[{"ptid":"03003", "param1":33.5, "param2":10, "param3":3}, { }],            
            }, 
        "토요일":{"onermpercent":"70",            
            "오전":[{"ptid":"00001", "param1":33.5, "param2":10, "param3":3}, { }]},}}

print("\n PtPlanPersonalWeekly_post 1 ================================> ")
print('  data = ', data)
#print(weekly_post(data))
res = requests.post(URL+'/personal-weekly', json=data, headers=headers)
print('>>>>>>> /personal-weekly post 선수 1명 선택된 1주 트레이닝 계획을 저장:', res.text)
'''

#exit(0)

##################################################################################################

#####################################################################
URL = URLBase + '/nutrition/get-body-composition'
''' 

params = {"userid":"김태권", }
print("\n NutriGetBodyCompo 3 ================================> ")
print('   ====== params = ', params)
res = requests.get(URL, params=params)
print('>>>>>>> {} get 신체조성  : {}'.format(URL, res.text))

'''


URL = URLBase[:-3]

'''
params = {"userid":"김태권", }
print("\n Hello test ================================> ")
print('   ====== params = ', params)
res = requests.get(URL, params=None)
print('>>>>>>> {} get Hello  : {}'.format(URL, res.text))

URL = URLBase

params = {"userid":"김태권", }
print("\n Hello API test ================================> ")
print('   ====== params = ', params)
res = requests.get(URL, params=None)
print('>>>>>>> {} get Hello API  : {}'.format(URL, res.text))
'''

import os
######################################
# image file upload
URL = URLBase + '/nutrition/ingestion-detail-image'
filename = 'E:\\works\\ETRI\\photo\\breakfast.jpg'
filename = '2021-12-03.png'
'''
up = {'image':(filename, open(filename, 'rb'), "multipart/form-data")}

data = {'userid':'김태권', 'date':'2021-11-30', 'time':'07:00', 'details':''}
print(' ingestion-detail-image POST  ====== URL={}, file={}, data={} '.format(URL, filename, data))

res = requests.post(URL, files=up, data=data)
#res = requests.post(URL, json=data, headers=headers)
print('>>>>>>> {} post 섭취상세내용 : {}'.format(URL, res.text))


with open(filename, 'rb') as img:
  name_img= os.path.basename(filename)
  files= {'image': (name_img,img,'multipart/form-data',{'Expires': '0'}) }
  with requests.Session() as s:
    r = s.post(URL, files=files)
    print(r.status_code)
    
'''   
    
    
# multipart_form_data = {
#     'file2': ('custom_file_name.zip', open('myfile.zip', 'rb')),
#     'action': ('', 'store'),
#     'path': ('', '/path1')
# }

# response = requests.post('https://httpbin.org/post', files=multipart_form_data)

#pip install requests_toolbelt
# from requests_toolbelt.multipart.encoder import MultipartEncoder

# multipart_data = MultipartEncoder(
#     fields={
#             # a file upload field
#             'file': ('breakfast.jpg', open('breakfast.jpg', 'rb'), 'text/plain'),
#             # plain text fields
#             'field0': 'value0', 
#             'field1': 'value1',
#            }
#     )

# response = requests.post(URL, data=multipart_data,
#                   headers={'Content-Type': multipart_data.content_type})

exit(0)
