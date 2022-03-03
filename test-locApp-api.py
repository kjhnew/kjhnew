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

URLBase = 'http://localhost:8094/api'
#URLBase = 'http://192.168.219.204:8094/api'
#URLBase = 'http://124.61.24.153:48094/api'
URLBase = 'http://192.168.219.114:8094/api'

print(f"URLBase ==========> {URLBase}")

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
URL = URLBase + '/collapp'
# 측위자원수집app
'''
data = {"site_id": "ETRI", "building_id": "3004", "floor": "1F", 'scenario_name':'sc11', "route_wp": "3004_1F_WP_1",\
    'dt_start':'2022-02-03 11:14:53.2', 'gt':'B', 'user':'myname', 'phonemodel':'samsung SM-N986N'}			
print("\ndata = ", data)
apiurl = URL+'/start-collection'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 수집 시작({apiurl}) == > {res.text}')
'''

'''
dt = datetime2str(datetime.datetime.now())
data = {"site_id": "ETRI", "building_id": "3004", "floor": "1F", 'scenario_name':'sc11', "route_wp": "3004_1F_WP_1",\
    'dt_start':dt, 'gt':'B', 'user':'myname', 'phonemodel':'samsung SM-N986N'}			
print("\ndata = ", data)
apiurl = URL+'/start-collection'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 수집 시작({apiurl}) == > {res.text}')

retdict = json.loads(res.text)
print(f'\nreturn idx ===> \n' + retdict['idx'])
idx = retdict.get('idx')

#test only data
x_lon = 127.36793118691
y_lat = 36.3800722718335
x_inc = -0.00001
y_inc = 0.00001

dt = datetime2str(datetime.datetime.now())
cur_pos = {'lon':str(x_lon), 'lat':str(y_lat), 'floor':'1F'}
data = {"idx": idx, 'action':'pos', 'dt':dt, 'cur_pos':cur_pos, 'mark_wp':'-1'}			
print("\ndata = ", data)
apiurl = URL+'/collection-status'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 측위자원수집앱 진행 상황({apiurl}) == > {res.text}')
# retdict = json.loads(res.text)
# print(f'\ndetails ===> \n' + retdict['details'])

time.sleep(2)

dt = datetime2str(datetime.datetime.now())
x_lon += x_inc
y_lat += y_inc

# record 시작
cur_pos = {'lon':str(x_lon), 'lat':str(y_lat), 'floor':'1F'}
data = {"idx": idx, 'action':'record', 'dt':dt, 'cur_pos':cur_pos, 'mark_wp':'0'}			
print("\ndata = ", data)
apiurl = URL+'/collection-status'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 측위자원수집앱 진행 상황({apiurl}) == > {res.text}')
# retdict = json.loads(res.text)
# print(f'\ndetails ===> \n' + retdict['details'])

for i in range(5):
    x_lon += x_inc
    y_lat += y_inc
    dt = datetime2str(datetime.datetime.now())
    cur_pos = {'lon':str(x_lon), 'lat':str(y_lat), 'floor':'1F'}
    data = {"idx": idx, 'action':'pos', 'dt':dt, 'cur_pos':cur_pos, 'mark_wp':'1'}			
    print("\ndata = ", data)
    apiurl = URL+'/collection-status'
    res = requests.post(apiurl, json=data, headers=headers)
    print(f'\n>>>>>>> POST 측위자원수집앱 진행 상황({apiurl}) == > {res.text}')    
    time.sleep(1)
    

for i in range(5):
    x_lon += x_inc
    y_lat += y_inc
    dt = datetime2str(datetime.datetime.now())
    cur_pos = {'lon':str(x_lon), 'lat':str(y_lat), 'floor':'1F'}
    data = {"idx": idx, 'action':'pos', 'dt':dt, 'cur_pos':cur_pos, 'mark_wp':'2'}			
    print("\ndata = ", data)
    apiurl = URL+'/collection-status'
    res = requests.post(apiurl, json=data, headers=headers)
    print(f'\n>>>>>>> POST 측위자원수집앱 진행 상황({apiurl}) == > {res.text}')    
    time.sleep(1)
    

dt = datetime2str(datetime.datetime.now())
x_lon += x_inc
y_lat += y_inc
# 수집 종료
cur_pos = {'lon':str(x_lon), 'lat':str(y_lat), 'floor':'1F'}
data = {"idx": idx, 'action':'stop', 'dt':dt, 'cur_pos':cur_pos, 'mark_wp':'3'}			
print("\ndata = ", data)
apiurl = URL+'/collection-status'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 측위자원수집앱 진행 상황({apiurl}) == > {res.text}')

'''

###########################################################################
# /api
URL = URLBase + '/mapdata'
# 

data = {'site_id':'KAIST'}			
print("\ndata = ", data)
apiurl = URL+'/get-building-list'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST no building {apiurl}) == > {res.text}')

data = {}			
print("\ndata = ", data)
apiurl = URL+'/get-site-list'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST {apiurl}) == > {res.text}')

data = {'site_id':'ETRI'}			
print("\ndata = ", data)
apiurl = URL+'/get-building-list'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST {apiurl}) == > {res.text}')



data = {'site_id':'ETRI', 'building_id':'3002'}			
print("\ndata = ", data)
apiurl = URL+'/get-floor-list'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST {apiurl}) == > {res.text}')


data = {'site_id':'ETRI', 'building_id':'3003'}			
print("\ndata = ", data)
apiurl = URL+'/get-floor-list'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST {apiurl}) == > {res.text}')


data = {'site_id':'ETRI', 'building_id':'3004'}			
print("\ndata = ", data)
apiurl = URL+'/get-floor-list'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST {apiurl}) == > {res.text}')


data = {'site_id':'ETRI', 'building_id':'3004'}			
print("\ndata = ", data)
apiurl = URL+'/get-route-list'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST {apiurl}) == > {res.text}')


data = {'site_id':'ETRI', 'building_id':'3002'}			
print("\ndata = ", data)
apiurl = URL+'/get-route-list'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST {apiurl}) == > {res.text}')

'''


data = {"idx": "250000"}			
print("\ndata = ", data)
apiurl = URL+'/delete-ppdataset'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 없는 후처리 데이터세트 삭제({apiurl}) == > {res.text}')


data = {"idx": "24"}			
print("\ndata = ", data)
apiurl = URL+'/delete-ppdataset'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 후처리 데이터세트 삭제({apiurl}) == > {res.text}')




data = {"idx": "24"}			
print("\ndata = ", data)
apiurl = URL+'/post-processing'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 후처리 수행({apiurl}) == > {res.text}')


data = {"idx": "24"}			
print("\ndata = ", data)
apiurl = URL+'/postproc-status'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 후처리 수행 상황({apiurl}) == > {res.text}')

'''

'''
data = {"site_id": "*"}			
print("\ndata = ", data)
apiurl = URL+'/get-dataset-filter'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 학습데이터셑 필터({apiurl}) == > {res.text}')


data = {"site_id":"*", "building_id":"3004", "floor":"*"}		
print("\ndata = ", data)
apiurl = URL+'/get-dataset-list'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 학습 데이터세트 목록({apiurl}) == > {res.text}')


data = {"site_id":"*", "building_id":"3003", "floor":"*"}		
print("\ndata = ", data)
apiurl = URL+'/get-dataset-list'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 학습 데이터세트 목록 빈 목록({apiurl}) == > {res.text}')


data = {"site_id":"*", "building_id":"*", "floor":"*"}		
print("\ndata = ", data)
apiurl = URL+'/get-dataset-list'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 학습 데이터세트 목록({apiurl}) == > {res.text}')


data = {"site_id":"*", "building_id":"*", "floor":"*"}		
print("\ndata = ", data)
apiurl = URL+'/get-model-list'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 학습모델 목록 ({apiurl}) == > {res.text}')


data = {"site_id":"*", "building_id":"3005", "floor":"*"}		
print("\ndata = ", data)
apiurl = URL+'/get-model-list'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 학습모델 목록 ({apiurl}) == > {res.text}')


data = {"site_id":"*", "building_id":"3005", "floor":"B1"}		
print("\ndata = ", data)
apiurl = URL+'/get-model-list'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 학습모델 목록-데이터없음({apiurl}) == > {res.text}')
'''
'''
data = {"idx": "8"}			
print("\ndata = ", data)
apiurl = URL+'/run'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 학습 수행({apiurl}) == > {res.text}')


data = {"idx": "8"}			
print("\ndata = ", data)
apiurl = URL+'/run-status'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 학습 수행 상황({apiurl}) == > {res.text}')

data = {"idx": "10"}			
print("\ndata = ", data)
apiurl = '/delete-dataset'
res = requests.post(URL+apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 학습데이터 삭제({apiurl}) == > {res.text}')


data = {"model_id": "ETRI-3005-4F-202112131443"}			
print("\ndata = ", data)
apiurl = '/delete-model'
res = requests.post(URL+apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 학습모델 삭제({apiurl}) == > {res.text}')

'''


###########################################################################
# /api
URL = URLBase + '/collectstatus'
# 수집 상태
'''
e'''
exit(0)

data = {"site_id": "*"}			
print("\ndata = ", data)
apiurl = URL+'/get-job'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 진행중인 수집작업 목록({apiurl}) == > {res.text}')


data = {"idx": "12"}			
print("\ndata = ", data)
apiurl = URL+'/get-mapdata'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 수집작업관련 빌딩맵({apiurl}) == > {res.text}')


data = {"idx": "12"}			
print("\ndata = ", data)
apiurl = URL+'/get-status'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 수집작업 상태 가져오기({apiurl}) == > {res.text}')



data = {"idx": "12"}			
print("\ndata = ", data)
apiurl = URL+'/get-status-traj'
res = requests.post(apiurl, json=data, headers=headers)
print(f'\n>>>>>>> POST 수집작업 상태 가져오기({apiurl}) == > {res.text}')










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
'''