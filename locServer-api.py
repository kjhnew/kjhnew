# -- coding: utf-8 --
"""
ETRI Localization
2022. 1 H4Tech
    locServer-api
    하나의 client 만 지원한다. 

    Postgresql DB API REST 인터페이스
    주의: 모든 숫자 값은 JSON 문자열로 변환하여 전달한다.
          onermpercent 값은 없으면 디폴트 100으로 저장
"""


from flask_restful import Resource, reqparse, Api
from flask import request
from flask import Flask
from flask import Response
from flask_cors import CORS
import json
import psycopg2
import configparser

#import cv2
import numpy as np
import base64
import pickle
from PIL import Image

import time
#import csv
import datetime
from datetime import timedelta, date
from dateutil.parser import *
import logging, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

#logging.basicConfig(stream=sys.stderr, level=logging.ERROR)

logger = logging.getLogger("strong-api")
logger.setLevel(logging.INFO)
stream_hander = logging.StreamHandler()
logger.addHandler(stream_hander)

logging_filename = 'strong-api.log'
print("Logging filename = ", logging_filename)

fh = logging.FileHandler(logging_filename)
fh.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
    
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter) 
ch.setFormatter(formatter) 

logger.addHandler(fh)
logger.addHandler(ch)

##########################################

# static 이미지 파일 경로
FILEPATH_STATIC_IMAGE = 'static/img/'
FILEPATH_UPLOAD_INGESTION_IMAGE = 'static/img/ingestphotoupload'

##########################################
# Postgresql API

db_ip = '192.168.219.204'
db_port = '5432'
db_user = 'postgres'
db_pw = 'h42020)('
db_name = 'etri_loc_v1'


TB_SITE = 'tb_site'	#사이트(지역)
TB_BUILDING = 'tb_building'	
TB_COLLECTION = 'tb_collection'	#수집
TB_COLLECTION_STATUS = 'tb_collection_status'	#수집상황
TB_COLLECTION_POSTPROC = 'tb_collection_postproc'	#수집데이터 후처리
	
TB_TRAINING_DATASET = 'tb_training_dataset'	#학습데이터셋
TB_TRAINING = 'tb_training'	#학습수행 기록 테이블
TB_LOC_MODEL = 'tb_loc_model'	#영상측위 학습 모델 관리


#########################################################################################

def dbconfig_read(config):
    global db_ip, db_port, db_name, db_pw
    
    db_ip = config['DB']['ip']
    db_port = config['DB']['port']
    db_name = config['DB']['dbname']
    db_pw = config['DB']['pw']
    
def kafkaconfig_read(config):
    global kafka_url
    
    kafka_url = config['kafka']['kafka_url']
    kafka_topic = config['kafka']['kafka_topic']
    
def config_read():
    
    # 설정파일 읽기
    config = configparser.ConfigParser()    
    config.read('locWeb-api_config.ini', encoding='utf-8') 

    # 설정파일의 색션 확인
    # config.sections())
    dbconfig_read(config)
    #kafkaconfig_read(config)
    
config_read()
host = db_ip
port = db_port
print('db ip:port = {}:{}'.format(db_ip, db_port))
#print('kafka broker = ', kafka_url)

############################################################################################################
# H4T Database server - WAN
def connectDB():
    conn = psycopg2.connect(host=db_ip, dbname=db_name, user=db_user, \
        password=db_pw, port=db_port)
    print(conn)
    return conn

# local
#conn = psycopg2.connect(host='192.168.219.204', dbname='prj_strong_ksoc', user='postgres', password='h42020)(', port='5432')

conn = connectDB()
cur = conn.cursor() # 성능문제 고려해야 할 듯

def connectDBIfClosed():
    global conn
    global cur
    if conn == None or conn.closed == 1:
        logger.warning('DB Connection closed.') 

        try:
            conn = connectDB()
            #print('reconnected DB....')  
            logger.info('reconnected DB....1') 
        except Exception as e:
            logger.error('DB connection 1 ' + e)
            return None
        
    try:
        cur = conn.cursor() # 성능문제 고려해야 할 듯
    except Exception as e:
        try:
            conn = connectDB()
            #print('reconnected DB....')  
            logger.info('reconnected DB....2') 
            cur = conn.cursor() # 성능문제 고려해야 할 듯
        except Exception as e:
            logger.error('DB connection 2 ' + e)
            return None     

    return cur
############################################################################################################
# util
def getFileInfo(fpath):
    fname = os.path.basename(fpath)
    info = fpath.stat()
    sz = info.st_size
    if sz >= 1000000:
        sz = sz / 1000000.
        sz = f'{sz:,.1f}MB'
    elif sz >= 100:
        sz = sz / 1000.
        sz = f'{sz:,.1f}KB'
    else:
        sz = f'{sz:}B'
    
    return {'name': fname, 'size':sz}



############################################################################################################
def im2json(im):
    """Convert a Numpy array to JSON string"""
    imdata = pickle.dumps(im)
    jstr = json.dumps({"image": base64.b64encode(imdata).decode('ascii')})
    return jstr

def json2im(jstr):
    """Convert a JSON string back to a Numpy array"""
    load = json.loads(jstr)
    imdata = base64.b64decode(load['image'])
    im = pickle.loads(imdata)
    return im


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

    if r != None:
        imdata = r[0]

    return imdata



def bytea2data(byteafromdb):

    imdata = None

    if byteafromdb != None:
        bytedata = byteafromdb.tobytes()
        imdata = base64.b64encode(bytedata).decode('ascii')

    return imdata

    

############################################################################################################

## 파일 업로드


from werkzeug.utils import secure_filename
from werkzeug.datastructures import ImmutableMultiDict
import os
from flask import send_file

class NutriIngestionDetailImage(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        # parser = reqparse.RequestParser()
        # args = parser.parse_args()
        # logger.info('args ==== {}'.format(args))
      
        args = dict(request.form)
        logger.info('args ===> {}'.format(args))
        scenarioid = args.get('scenarioid')
        if scenarioid != None:
            print(f"scenarioid = {scenarioid}")
        time_ = args.get('time')
        item = args.get('item')
        details = args.get('details', '')

        print(request.files.to_dict())
        #f = request.files.get('photo')
        filelist = request.files.getlist('files[]')
        print(f' filelist====>{filelist}')
        metadatafile = request.files.get('metadata')
        print(f' metadatafile====>{metadatafile}')

        filename = ''
        strFilePath = ''
        for f in filelist:
            if(f != None):
                filename = secure_filename(f.filename)        
                strFilePath = os.path.join(FILEPATH_UPLOAD_INGESTION_IMAGE, filename)
                f.save(strFilePath)
                #폴더 없는 경우 생성
                logger.info('filename : ' + filename)
                logger.info('strFilePath : ' + strFilePath)            
            
        if(metadatafile != None):
            f = metadatafile
            filename = secure_filename(f.filename)        
            strFilePath = os.path.join(FILEPATH_UPLOAD_INGESTION_IMAGE, filename)
            f.save(strFilePath)
            #폴더 없는 경우 생성
            logger.info('metadatafile filename : ' + filename)
            logger.info('metadatafile strFilePath : ' + strFilePath)    
               
            
        data = {'result':'Y'}
        res = json.dumps(data, ensure_ascii=False).encode('utf8')
        print("response data = ", data)
        return Response(res, content_type='application/json; charset=utf-8')
        
        # except Exception as e:
        #     logger.error(self.__class__.__name__ + ' Get : ' + str(e))
        #     return makeErrorResponseMsgResponse(str(e))




    def options (self):
        return {'Allow' : 'GET, POST' }, 200, \
        { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*',\
        'Access-Control-Allow-Methods' : 'GET, POST' }



class DownloadFiles(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        # parser = reqparse.RequestParser()
        # args = parser.parse_args()
        # logger.info('args ==== {}'.format(args))
        
        return makeErrorResponseMsgResponse("return.........")
      
        args = dict(request.form)
        logger.info('args ===> {}'.format(args))
        scenarioid = args.get('scenarioid')
        if scenarioid != None:
            print(f"scenarioid = {scenarioid}")
        time_ = args.get('time')
        item = args.get('item')
        details = args.get('details', '')

        print(request.files.to_dict())
        #f = request.files.get('photo')
        filelist = request.files.getlist('files[]')
        print(f' filelist====>{filelist}')
        metadatafile = request.files.get('metadata')
        print(f' metadatafile====>{metadatafile}')

        filename = ''
        strFilePath = ''
        for f in filelist:
            if(f != None):
                filename = secure_filename(f.filename)        
                strFilePath = os.path.join(FILEPATH_UPLOAD_INGESTION_IMAGE, filename)
                f.save(strFilePath)
                #폴더 없는 경우 생성
                logger.info('filename : ' + filename)
                logger.info('strFilePath : ' + strFilePath)            
            
        if(metadatafile != None):
            f = metadatafile
            filename = secure_filename(f.filename)        
            strFilePath = os.path.join(FILEPATH_UPLOAD_INGESTION_IMAGE, filename)
            f.save(strFilePath)
            #폴더 없는 경우 생성
            logger.info('metadatafile filename : ' + filename)
            logger.info('metadatafile strFilePath : ' + strFilePath)    
               
            
        data = {'result':'Y'}
        res = json.dumps(data, ensure_ascii=False).encode('utf8')
        print("response data = ", data)
        return Response(res, content_type='application/json; charset=utf-8')
        
        # except Exception as e:
        #     logger.error(self.__class__.__name__ + ' Get : ' + str(e))
        #     return makeErrorResponseMsgResponse(str(e))



    def get(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        print("Downloading................")

        parser = reqparse.RequestParser()
        parser.add_argument('userid', required=False, type=str, help='userid')
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        # userid = str(args['userid'])
        # logger.info("선수id = " + userid)

        files = ['h4tech_logo_new.png', 'pushup.jpg', 'testWP.shp']
        strFilePath1 = os.path.join(FILEPATH_UPLOAD_INGESTION_IMAGE, files[0])
        strFilePath2 = os.path.join(FILEPATH_UPLOAD_INGESTION_IMAGE, files[1])

        file_list = [  
            ('Key_here', (files[0], open(strFilePath1, 'rb'), 'image/png')),
            ('key_here', (files[1], open(strFilePath2, 'rb'), 'image/jpg'))
            ]
        # text/plane, text/csv 
        file_name = os.path.join(FILEPATH_UPLOAD_INGESTION_IMAGE, files[0])
        file_name = "E:/tmp/h4tech_logo_new.png"
        file_name = "e:/tmp/testWP.shp"
        print(f"send file : {file_name}")
        return send_file(file_name,
                     mimetype='application/octet-stream',
                     attachment_filename=files[2],# 다운받아지는 파일 이름. 
                     as_attachment=True)
        # return send_file(file_name,
        #              mimetype='image/png',
        #              attachment_filename=files[0],# 다운받아지는 파일 이름. 
        #              as_attachment=True)    
        # data = {'result':'Y', 'height':str(r[0]), 'weight':str(r[1]), 'bodyfat':'29.1', 'musclemass':'37.8'}
        # res = json.dumps(data, ensure_ascii=False).encode('utf8')
        # print("response data = ", data)
        # return Response(res, content_type='application/json; charset=utf-8')
        
        # except Exception as e:
        #     logger.error(self.__class__.__name__ + ' Get : ' + str(e))
        #     return makeErrorResponseMsgResponse(str(e)) 
  



    def options (self):
        return {'Allow' : 'GET, POST' }, 200, \
        { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*',\
        'Access-Control-Allow-Methods' : 'GET, POST' }




class NutriGetBodyCompo(Resource):
    
    def get_time(elem):
        return elem.get('time')
    
    def get(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('userid', required=True, type=str, help='userid')
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        userid = str(args['userid'])
        logger.info("선수id = " + userid)

        cur = connectDBIfClosed()
        query = 'SELECT height, weight FROM ' + TB_USER + ' WHERE userid=%s '
        print('query = ', query)
        cur.execute(query, (userid,))
        r = cur.fetchone()

        if r==None:
            return makeErrorResponseMsgResponse('no user')
            
        data = {'result':'Y', 'height':str(r[0]), 'weight':str(r[1]), 'bodyfat':'29.1', 'musclemass':'37.8'}
        res = json.dumps(data, ensure_ascii=False).encode('utf8')
        print("response data = ", data)
        return Response(res, content_type='application/json; charset=utf-8')
        
        # except Exception as e:
        #     logger.error(self.__class__.__name__ + ' Get : ' + str(e))
        #     return makeErrorResponseMsgResponse(str(e)) 
  

    def options (self):
        return {'Allow' : 'GET' }, 200, \
        { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*',\
        'Access-Control-Allow-Methods' : 'GET' }


class Hello(Resource):
    

    def get(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
            
        data = {'result':'Y', 'msg':'Hello!'}
        res = json.dumps(data, ensure_ascii=False).encode('utf8')
        print("response data = ", data)
        return Response(res, content_type='application/json; charset=utf-8')
        
        # except Exception as e:
        #     logger.error(self.__class__.__name__ + ' Get : ' + str(e))
        #     return makeErrorResponseMsgResponse(str(e)) 
  

    def options (self):
        return {'Allow' : 'GET' }, 200, \
        { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*',\
        'Access-Control-Allow-Methods' : 'GET' }


class HelloAPI(Resource):
    

    def get(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
            
        data = {'result':'Y', 'msg':'Hello! API!'}
        res = json.dumps(data, ensure_ascii=False).encode('utf8')
        print("response data = ", data)
        return Response(res, content_type='application/json; charset=utf-8')
        
        # except Exception as e:
        #     logger.error(self.__class__.__name__ + ' Get : ' + str(e))
        #     return makeErrorResponseMsgResponse(str(e)) 
  

    def options (self):
        return {'Allow' : 'GET' }, 200, \
        { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*',\
        'Access-Control-Allow-Methods' : 'GET' }



######################################################################################
## 수집app API
class CollappStartCollection(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('scenario_name', required=True, type=str, help='scenario_name')
        parser.add_argument('site_id', required=True, type=str, help='site_id')
        parser.add_argument('building_id', required=True, type=str, help='building_id')
        parser.add_argument('floor', required=True, type=str, help='floor')
        parser.add_argument('route_wp', required=True, type=str, help='route_wp')
        parser.add_argument('dt_start', required=True, type=str, help='dt_start')
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        
        scenario_name = args.get('scenario_name')
        logger.info("scenario_name = " + scenario_name)
        
        site_id = args.get('site_id')
        logger.info("site_id = " + site_id)
        
        building_id = args.get('building_id')
        logger.info("building_id = " + building_id)
        
        floor = args.get('floor')
        logger.info("floor = " + floor)        
        
        route_wp = args.get('route_wp')
        if route_wp.strip() == '': route_wp = None
        logger.info(f"route_wp = {route_wp}")
                       
        dt_start = args.get('dt_start')
        logger.info("dt_start = " + dt_start)        
        
        cur = connectDBIfClosed()
        query = 'SELECT idx, scenario_name, site_id, building_id, floor, route_wp, dt_start, dt_end, gt, user_name, phonemodel FROM '\
            + TB_COLLECTION + ' WHERE scenario_name=%s and site_id=%s and building_id=%s and floor=%s and route_wp=%s and dt_end=%s'
        print('query = ', query)
        cur.execute(query, (scenario_name, site_id, building_id, floor, route_wp, None))
        r = cur.fetchone()
        idx = None

        print('records =========>', r)
        # 끝내지 않은 동일 조건의 레코드가 있으면 이것으로 대체한다.
        if r != None:
            idx = str(r[0])

            # 시간업데이트
            query = 'UPDATE ' + TB_COLLECTION + ' SET dt_start=%s WHERE idx=%s '
            cur.execute(query, (dt_start, idx))
            conn.commit()
        else:
            query = 'INSERT INTO ' + TB_COLLECTION + \
                '(scenario_name, site_id, building_id, floor, route_wp, dt_start, dt_end, gt, user_name, phonemodel) '\
                    + ' VALUES (%s,%s,%s,%s,%s,%s) RETURNING idx '
            cur.execute(query, (scenario_name, site_id, building_id, floor, route_wp, dt_start))
            conn.commit()
            idx = cur.fetchone()[0] # new idx
            
        data = {'result':'Y', 'idx':str(idx)}
        res = json.dumps(data, ensure_ascii=False).encode('utf8')
        print("response data = ", data)
        return Response(res, content_type='application/json; charset=utf-8')
        
        # except Exception as e:
        #     logger.error(self.__class__.__name__ + ' Get : ' + str(e))
        #     return makeErrorResponseMsgResponse(str(e)) 
  

    def options (self):
        return {'Allow' : 'POST' }, 200, \
        { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*',\
        'Access-Control-Allow-Methods' : 'POST' }



    
app = Flask('STRONG for KSOC DB API REST Interface')
app.config['JSON_AS_ASCII'] = False # 한글 깨짐 문제 해결
CORS(app)   # 모든 주소에 대하여 요청 허용
# 1 ‘https://hwangtoemat.github.io’ 에 해당하는 모든 포트, 하위 주소를 허용한다.
#CORS(app, resources={r'*': {'origins': 'https://hwangtoemat.github.io'}})
# 2 ‘https://hwangtoemat.github.io’ 에서 /computer-science의 하위 경로와 포트번호 1121만 허용한다.
#CORS(app, resources={r'/computer-science/*': {'origins': 'https://hwangtoemat.github.io:1121'}})

api = Api(app)

## 기본 API
api.add_resource(Hello, '/')
api.add_resource(HelloAPI, '/api')

######################################################################################
## 측위자원수집관리 API
#측위자원 수집app 수집시작하기  - POST
api.add_resource(CollappStartCollection, '/api/collapp/start-collection')
#측위자원 수집app 수집 상태  - POST
#api.add_resource(CollappStartCollection, '/api/collapp/collection-status')


## 영양정보 사진업로드
api.add_resource(NutriIngestionDetailImage, '/upload')    # 영양섭취 사진
api.add_resource(DownloadFiles, '/down')

# static 이미지 파일 경로
# <flask home>/static/img/

print(f'====>{app.url_map}')


import zipfile
import io
import pathlib

@app.route('/download-zip')
def request_zip():
    base_path = pathlib.Path('./mapdata/ETRI/3002/')
    data = io.BytesIO()
    with zipfile.ZipFile(data, mode='w') as z:
        for f_name in base_path.iterdir():
            z.write(f_name)
    data.seek(0)
    return send_file(
        data,
        mimetype='application/zip',
        as_attachment=True,
        attachment_filename='data.zip'      # zip파일에 mapdata/ETRI/3002/ 경로를 모두 가지고 있다.
    )
    
    
if __name__ == '__main__':

    # H4T Database server - WAN
    #conn = psycopg2.connect(host=host, dbname='prj_strong_ksoc', user='postgres', password='h42020)(', port=port)
    #print(conn)

    # local
    #conn = psycopg2.connect(host='192.168.219.204', dbname='prj_strong_ksoc', user='postgres', password='h42020)(', port='5432')

    #cur = conn.cursor() # 성능문제 고려해야 할 듯
    
    print(f'====>{app.url_map}')

    app.run(host='192.168.0.41', port=8889, debug=True, threaded=False)
    
    print(f'====>{app.url_map}')
