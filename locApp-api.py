# -- coding: utf-8 --
"""
ETRI Localization
2022. 1 H4Tech
    locApp-api
    하나의 client 만 지원한다. 

    Postgresql DB API REST 인터페이스
    주의: 모든 숫자 값은 JSON 문자열로 변환하여 전달한다.
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
import glob

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

# 측위자원 upload file path
FILEPATH_LOCDATA_PATH = "e:/LOCDATA/COLLECTION"
FILEPATH_MAPDATA_PATH = "e:/LOCDATA/MAPDATA"

data_directory = FILEPATH_LOCDATA_PATH

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
TB_COLLECTION_STATUS_TRAJ = 'tb_collection_status_traj'	#수집상황 이동궤적
TB_COLLECTION_POSTPROC = 'tb_collection_postproc'	#수집데이터 후처리
	
TB_TRAINING_DATASET = 'tb_training_dataset'	#학습데이터셋
TB_TRAINING = 'tb_training'	#학습수행 기록 테이블
TB_LOC_MODEL = 'tb_loc_model'	#영상측위 학습 모델 관리


#########################################################################################

def datadirectory_read(config):
    global data_directory
    
    data_directory = config['system']['datadirectory']
    print('data_directory :', data_directory)


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
    config.read('locApp-api_config.ini', encoding='utf-8') 

    # 설정파일의 색션 확인
    # config.sections())
    datadirectory_read(config)
    dbconfig_read(config)
    #kafkaconfig_read(config)
    
config_read()
host = db_ip
port = db_port
print('data_directory :' + data_directory)
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
        try:
            # logger.info('request = {}'.format(request.json))
            # print('request ==> {} {}'.format(request, request.json))
            #scenario_name = request.json.get('building_id')
            #site_id = request.json.get('site_id')
                
            parser = reqparse.RequestParser()
            parser.add_argument('scenario_name', required=True, type=str, help='scenario_name')
            parser.add_argument('site_id', required=True, type=str, help='site_id')
            parser.add_argument('building_id', required=True, type=str, help='building_id')
            parser.add_argument('floor', required=True, type=str, help='floor')
            parser.add_argument('route_wp', required=True, type=str, help='route_wp')
            parser.add_argument('dt_start', required=True, type=str, help='dt_start')
            parser.add_argument('gt', required=True, type=str, help='gt')
            parser.add_argument('user', required=True, type=str, help='user')
            parser.add_argument('phonemodel', required=True, type=str, help='phonemodel')
            
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
            #if route_wp.strip() == '': route_wp = None
            logger.info(f"route_wp = {route_wp}")

            dt_start = args.get('dt_start')
            logger.info(f"dt_start = {dt_start}")        
            
            gt = args.get('gt')
            logger.info(f"gt = {gt}")
            
            user = args.get('user')
            #if user.strip() == '': user = None
            logger.info(f"route_wp = {user}")
            
            phonemodel = args.get('phonemodel')
            #if phonemodel.strip() == '': phonemodel = None
            logger.info(f"phonemodel = {phonemodel}")

            cur = connectDBIfClosed()
            query = 'SELECT idx, scenario_name, site_id, building_id, floor, route_wp, dt_start, \
                dt_end, gt, user_name, phonemodel FROM '\
                + TB_COLLECTION + ' WHERE scenario_name=%s and site_id=%s and building_id=%s and \
                    floor=%s and route_wp=%s and gt=%s and user_name=%s and phonemodel=%s'
            print('query = ', query)
            # None 값과 비교하면 안됨. (None과 비교하는 방법은: user_name is null)
            cur.execute(query, (scenario_name, site_id, building_id, floor, route_wp, gt, user, phonemodel))
            r = cur.fetchone()
            idx = None

            print('records =========>', r)
            # 끝내지 않은(dt_end == null) 동일 조건의 레코드가 있으면 이것으로 갱신
            new_collection = False
            dt_end = r[7] if r != None else None
            if r == None or dt_end != None: new_collection = True
            
            if not new_collection:
                idx = str(r[0])

                # 시간업데이트
                query = 'UPDATE ' + TB_COLLECTION + ' SET dt_start=%s WHERE idx=%s '
                cur.execute(query, (dt_start, idx))
                conn.commit()
            else:
                query = 'INSERT INTO ' + TB_COLLECTION + \
                    '(scenario_name, site_id, building_id, floor, route_wp, dt_start, gt, user_name, phonemodel) '\
                        + ' VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING idx '
                cur.execute(query, (scenario_name, site_id, building_id, floor, route_wp, dt_start, gt, user, phonemodel))
                conn.commit()
                idx = cur.fetchone()[0] # new idx
                
            data = {'result':'Y', 'idx':str(idx)}
            res = json.dumps(data, ensure_ascii=False).encode('utf8')
            print("response data = ", data)
            #logger.info(f"response data = {data}")
            return Response(res, content_type='application/json; charset=utf-8')
        
        except Exception as e:
            logger.error(f'ERROR in {self.__class__.__name__} {sys._getframe().f_code.co_name}: {e}')
            return makeErrorResponseMsgResponse(str(e)) 
  

    def options (self):
        return {'Allow' : 'POST' }, 200, \
        { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*',\
        'Access-Control-Allow-Methods' : 'POST' }


######################################################################################
## 수집app API
class CollappCollectionStatus(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('idx', required=True, type=str, help='idx')
        parser.add_argument('action', required=True, type=str, help='action')
        parser.add_argument('dt', required=True, type=str, help='dt')
        parser.add_argument('cur_pos', required=False, type=str, help='cur_pos')
        parser.add_argument('mark_wp', required=True, type=str, help='mark_wp')
        
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        
        idx = args.get('idx')
        logger.info(f'idx = {idx}')
        
        action = args.get('action').strip().lower()
        logger.info("action = " + action)
        
        dt_str = args.get('dt')
        logger.info("dt = " + dt_str)
        
        #cur_pos = args.get('cur_pos')
        cur_pos = request.json.get('cur_pos')
        logger.info(f"cur_pos = {cur_pos}")
        
        mark_wp = args.get('mark_wp')
        logger.info(f"mark_wp = {mark_wp}")
        
        cur = connectDBIfClosed()
        query = 'SELECT * FROM ' + TB_COLLECTION + ' WHERE idx=%s'
        print('query = ', query)
        cur.execute(query, (idx,))
        r = cur.fetchone()
        if r == None: return makeErrorResponseMsgResponse('no record')
        print('records =========>', r)
        
        # 레코드 시작하면 dt_start 를 레코드 시점으로 업데이트
        if 'record' in action:
            query = 'UPDATE ' + TB_COLLECTION + ' SET dt_start=%s WHERE idx=%s '
            cur.execute(query, (dt_str, idx))
            conn.commit()   
        elif 'stop' in action:         
            query = 'UPDATE ' + TB_COLLECTION + ' SET dt_end=%s WHERE idx=%s '
            cur.execute(query, (dt_str, idx))
            conn.commit()           
        
        cur = connectDBIfClosed()
        query = 'SELECT * FROM ' + TB_COLLECTION_STATUS + ' WHERE idx=%s'
        print('query = ', query)
        cur.execute(query, (idx,))
        r = cur.fetchone()
        
        pos_lon = None
        pos_lat = None
        pos_floor = None
        dt_start = None
        dt_end = None

        # dt 는 status에 무조건 갱신
        if r != None:
            # dt_start = datetime2str(r[1]) if r[1] != None else dt_start
            # dt_end = datetime2str(r[2]) if r[2] != None else dt_end
            pos_lon = str(r[2])
            pos_lat = str(r[3])
            pos_floor = r[4]        
        
        if cur_pos != None:
            pos_lon = cur_pos.get('lon')
            pos_lat = cur_pos.get('lat')
            pos_floor = cur_pos.get('floor')
            
        if 'record' in action:
            dt_start = dt_str
        elif 'stop' in action:
            dt_end = dt_str
        else:
            print('')
            
            
        if r != None:
            # 업데이트
            query = 'UPDATE ' + TB_COLLECTION_STATUS + \
                ' SET dt=%s, pos_x_lon=%s, pos_y_lat=%s, pos_z_floor=%s, mark=%s WHERE idx=%s '
            cur.execute(query, (dt_str, pos_lon, pos_lat, pos_floor, mark_wp, idx))
            conn.commit()
        else:
            query = 'INSERT INTO ' + TB_COLLECTION_STATUS + \
                ' (idx, dt, pos_x_lon, pos_y_lat, pos_z_floor, mark) '\
                    + ' VALUES (%s,%s,%s,%s,%s,%s,%s) '
            cur.execute(query, (idx, dt, pos_lon, pos_lat, pos_floor, mark_wp,))
            conn.commit()
            
        # trajectory
        query = 'INSERT INTO ' + TB_COLLECTION_STATUS_TRAJ + \
            ' (idx_collection, dt, pos_x_lon, pos_y_lat, pos_z_floor, mark) '\
                + ' VALUES (%s,%s,%s,%s,%s,%s) '
        cur.execute(query, (idx, dt_str, pos_lon, pos_lat, pos_floor, mark_wp,))
        conn.commit()
                    
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



def dtstr2planestr(dtstr):
    # 2021-12-23T15:26:24.21342 -> 20211223_15262421342
    # 2021-12-23 15:26:24.21342 -> 20211223_15262421342
    str = dtstr.replace(':', '').replace('-', '').replace('.', '').replace(' ', '_').replace('T', '_')
    return str



class CollappUploadDataset(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        # parser = reqparse.RequestParser()
        # args = parser.parse_args()
        # logger.info('args ==== {}'.format(args))
      
        args = dict(request.form)
        logger.info('args ===> {}'.format(args))
        idx = args.get('idx')
        dt_end = args.get('dt_end')

        # TODO: idx 가 없는 경우 고려해야 하나?
        #   만일 offline 상태로 수집해야 한다면? idx를 받아 오지 못한다.
        #       이런경우에는 upload 시 DB에 collection 레코드를 생성하도록 해야한다.
        #       idx == '-1'인경우이다.
        if idx == None: return makeErrorResponseMsgResponse('no idx')
        if idx == None: return makeErrorResponseMsgResponse('no dt_end')
        cur = connectDBIfClosed()
        query = 'SELECT * FROM ' + TB_COLLECTION + ' WHERE idx=%s'
        print('query = ', query)
        cur.execute(query, (idx,))
        r = cur.fetchone()
        if r == None: return makeErrorResponseMsgResponse(f'no collection for idx:{idx}')
        scenario_name = r[1]
        site_id = r[2]
        building_id = r[3]
        floor = r[4]
        dt_start = r[6]
        if dt_start == None: return makeErrorResponseMsgResponse(f'no start time')
        
        dtstr = dtstr2planestr(datetime2str(dt_start))

        datapath = site_id
        datapath = os.path.join(datapath, building_id)
        datapath = os.path.join(datapath, scenario_name)
        datapath = os.path.join(datapath, dtstr)
        
        path = os.path.join(data_directory, datapath)

        logger.info(f"dataset upload path = {path}")

        # 기존 폴더가 존재할 수 있다. 반복 업로드 가능
        os.makedirs(path, exist_ok=True)

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
                strFilePath = os.path.join(path, filename)
                f.save(strFilePath)
                #폴더 없는 경우 생성
                logger.info('filename : ' + filename)
                logger.info('strFilePath : ' + strFilePath)            
            
        if(metadatafile != None):
            f = metadatafile
            filename = secure_filename(f.filename)        
            strFilePath = os.path.join(path, filename)
            f.save(strFilePath)
            #폴더 없는 경우 생성
            logger.info('metadatafile filename : ' + filename)
            logger.info('metadatafile strFilePath : ' + strFilePath)    
               

        # dt_end, datapath 업데이트, datapath는 상대 위치
        query = 'UPDATE ' + TB_COLLECTION + ' SET dt_end=%s, datapath=%s WHERE idx=%s '
        cur.execute(query, (dt_end, datapath, idx))
        conn.commit()
            
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



######################################################################################
## MapData API2

class MapdataGetSiteList(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        # parser = reqparse.RequestParser()
    
        cur = connectDBIfClosed()
        query = 'SELECT site_id, site_name, address, description  FROM '\
            + TB_SITE 
        print('query = ', query)
        cur.execute(query, )
        records = cur.fetchall()

        print('records =========>', records)
        sitelist = []
        for r in records:
            sitelist.append({'id':r[0], 'name':r[1], 'address':r[2], 'description':r[3]})
            
        data = {'result':'Y', 'sitelist':sitelist}
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



class MapdataGetBuildingList(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('site_id', required=True, type=str, help='site_id')

        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        
        site_id = args.get('site_id')
        logger.info(f"site_id = {site_id}")

        cur = connectDBIfClosed()
        query = 'SELECT building_id, building_name, num_basement, num_floors  FROM '\
            + TB_BUILDING + ' WHERE site_id=%s ' 
        print('query = ', query)
        cur.execute(query, (site_id,))
        records = cur.fetchall()

        print('records =========>', records)
        buildinglist = []
        for r in records:
            buildinglist.append({'id':r[0], 'name':r[1], 'num_basement':r[2], 'num_floors':r[3]})
            
        data = {'result':'Y', 'buildinglist':buildinglist}
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


def extractFloor(f, building_id, num_basement, num_floor):

    # 지하층
    for i in range(1, num_basement+1):
        floor = f'B{i}'
        fname = f'{building_id}_{floor}.png'
        if fname.lower() == f.strip().lower():
            return floor
    
    # 지상층 4층이 없는 경우를 위해서 +1 층까지 검색한다.
    for i in range(1, num_floor+1):
        floor = f'{i}F'
        fname = f'{building_id}_{floor}.png'
        if fname.lower() == f.strip().lower():
            return floor
        
    return None


class MapdataGetFloorList(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('site_id', required=True, type=str, help='site_id')
        parser.add_argument('building_id', required=True, type=str, help='building_id')

        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        
        site_id = args.get('site_id')
        logger.info(f"site_id = {site_id}")
        
        building_id = args.get('building_id')
        logger.info(f"building_id = {building_id}")

        cur = connectDBIfClosed()
        query = 'SELECT building_id, building_name, num_basement, num_floors  FROM '\
            + TB_BUILDING + ' WHERE site_id=%s and building_id=%s' 
        print('query = ', query)
        cur.execute(query, (site_id, building_id,))
        r = cur.fetchone()
        print('records =========>', r)
        
        # 파일목록에서 찾아야 한다.
        floorlist = []
        if r != None:
            num_basement = r[2]
            num_floor = r[3]
            path = os.path.join(FILEPATH_MAPDATA_PATH, site_id)
            path = os.path.join(path, building_id)
            filelist = os.listdir(path)
            for f in filelist:
                print(f)
                floor = extractFloor(f, building_id, num_basement, num_floor)
                if floor != None:
                    floorlist.append(floor)

            
        data = {'result':'Y', 'floorlist':floorlist}
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


    
    
class MapdataGetRouteList(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('site_id', required=True, type=str, help='site_id')
        parser.add_argument('building_id', required=True, type=str, help='building_id')

        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        
        site_id = args.get('site_id')
        logger.info(f"site_id = {site_id}")
        
        building_id = args.get('building_id')
        logger.info(f"building_id = {building_id}")

        cur = connectDBIfClosed()
        query = 'SELECT building_id, building_name, num_basement, num_floors  FROM '\
            + TB_BUILDING + ' WHERE site_id=%s and building_id=%s' 
        print('query = ', query)
        cur.execute(query, (site_id, building_id,))
        r = cur.fetchone()
        print('records =========>', r)
        
        # 파일목록에서 찾아야 한다.
        routelist = []
        if r != None:
            num_basement = r[2]
            num_floor = r[3]
            path = os.path.join(FILEPATH_MAPDATA_PATH, site_id)
            path = os.path.join(path, 'route')
            filelist = os.listdir(path)
            conditions = path + '/*.shp'
            shpfiles = glob.glob(conditions)
            shpfilenames = []
            for shp in shpfiles:
                shpfilenames.append(os.path.basename(shp))
            
            for f in shpfilenames:
                print(f)
                if building_id in f:
                    route_name = f[:-4]
                    routelist.append(route_name)

            
        data = {'result':'Y', 'routelist':routelist}
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



    
app = Flask('LOCALIZATION APP DB API REST Interface', static_url_path='')
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
## 측위자원수집App API
#측위자원 수집app 수집시작하기  - POST
api.add_resource(CollappStartCollection, '/api/collapp/start-collection')
#측위자원 수집app 수집 상태  - POST
api.add_resource(CollappCollectionStatus, '/api/collapp/collection-status')
#측위자원 수집app 수집파일 업로드  - POST
api.add_resource(CollappUploadDataset, '/api/collapp/upload-dataset')

######################################################################################
## 측위자원수집App mapdata API
# site 목록  - POST
api.add_resource(MapdataGetSiteList, '/api/mapdata/get-site-list')
# building 목록  - POST
api.add_resource(MapdataGetBuildingList, '/api/mapdata/get-building-list')
# building 목록  - POST
api.add_resource(MapdataGetFloorList, '/api/mapdata/get-floor-list')
# route(WP) 목록  - POST
api.add_resource(MapdataGetRouteList, '/api/mapdata/get-route-list')


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
    
    #print(f'====>{app.url_map}')

    app.run(host='0.0.0.0', port=8094, debug=True, threaded=False)

