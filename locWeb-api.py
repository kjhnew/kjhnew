# -- coding: utf-8 --
"""
ETRI Localization
2022. 1 H4Tech
    locweb-api
    하나의 client 만 지원한다. 

    Postgresql DB API REST 인터페이스
    주의: 모든 숫자 값은 JSON 문자열로 변환하여 전달한다.
"""


from inspect import getfile
import site
from typing import Tuple
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
from pathlib import Path


sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

#logging.basicConfig(stream=sys.stderr, level=logging.ERROR)

logger = logging.getLogger("locWeb-api")
logger.setLevel(logging.INFO)
stream_hander = logging.StreamHandler()
logger.addHandler(stream_hander)

logging_filename = 'locWeb-api.log'
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
#host = 'dev.h4tech.co.kr'
#port = '45432'


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


def makeWhereClause(site_id, building_id, floor):
    site_where = ' site_id = %s ' if site_id != '%' else ' site_id LIKE %s '
    building_where = ' building_id = %s ' if building_id != '%' else ' building_id LIKE %s '
    floor_where = ' floor = %s ' if floor != '%' else ' floor LIKE %s '
    return f' WHERE {site_where} and {building_where} and {floor_where} '

########################################################################################################
# Collect 측위자원수집관리
class CollectGetDatasetList(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('site_id', required=False, type=str, help='site_id')
        parser.add_argument('building_id', required=False, type=str, help='building_id')
        parser.add_argument('floor', required=False, type=str, help='floor')
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        site_id = args.get('site_id', '%')
        if site_id == '*': site_id = '%'
        logger.info("site_id = " + site_id)
        
        building_id = args.get('building_id', '%')
        if building_id == '*': building_id = '%'
        logger.info("building_id = " + building_id)
        
        floor = args.get('floor', '%')
        if floor == '*': floor = '%'
        logger.info("floor = " + floor)        
        
        cur = connectDBIfClosed()
        whereclause = makeWhereClause(site_id, building_id, floor)
        print(whereclause)
        query = 'SELECT idx, scenario_name, site_id, building_id, floor, route_wp, dt_start, dt_end, gt, user_name, phonemodel FROM '\
            + TB_COLLECTION + whereclause + ' ORDER BY dt_start DESC '
        print('query = ', query)
        cur.execute(query, (site_id, building_id, floor,))
        records = cur.fetchall()
        print('records =========>', records)

        data_list = []
        # if len(records)==0:
        #     return makeErrorResponseMsgResponse('no data')
        for r in records:
            dt_str = datetime2str(r[6])
            d = {'idx':str(r[0]), 'scenario_name':r[1], 'site_id':r[2], 'building_id':r[3], 'floor':r[4],
                 'route_wp':r[5], 'dt_start':dt_str}
            data_list.append(d)
            
        data = {'result':'Y', 'data_list':data_list}
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


class CollectPPGetDatasetList(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('site_id', required=False, type=str, help='site_id')
        parser.add_argument('building_id', required=False, type=str, help='building_id')
        parser.add_argument('floor', required=False, type=str, help='floor')
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        site_id = args.get('site_id', '%')
        if site_id == '*': site_id = '%'
        logger.info("site_id = " + site_id)
        
        building_id = args.get('building_id', '%')
        if building_id == '*': building_id = '%'
        logger.info("building_id = " + building_id)
        
        floor = args.get('floor', '%')
        if floor == '*': floor = '%'
        logger.info("floor = " + floor)        
        
        cur = connectDBIfClosed()
        whereclause = makeWhereClause(site_id, building_id, floor)
        print(whereclause)
        query = 'SELECT idx, scenario_name, site_id, building_id, floor, route_wp, dt_start, ppdirectory FROM '\
            + TB_COLLECTION + whereclause + ' and ppdirectory IS NOT NULL '+ ' ORDER BY dt_start DESC '
        print('query = ', query)
        cur.execute(query, (site_id, building_id, floor,))
        records = cur.fetchall()
        print('records =========>', records)

        if len(records)==0:
            return makeErrorResponseMsgResponse('no data')
        data_list = []
        for r in records:
            dt_str = datetime2str(r[6])
            d = {'idx':str(r[0]), 'scenario_name':r[1], 'site_id':r[2], 'building_id':r[3], 'floor':r[4],
                 'route_wp':r[5], 'dt_start':dt_str, 'ppdirectory': r[7]}
            data_list.append(d)
            
        data = {'result':'Y', 'data_list':data_list}
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



class CollectGetDatasetFilter(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('site_id', required=True, type=str, help='site_id')
        parser.add_argument('building_id', required=False, type=str, help='building_id')
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        site_id = args.get('site_id', '%')
        if site_id == '*': site_id = '%'
        site_id = '%'   # 우선 all 로 고정
        logger.info("site_id = " + site_id)
        
        # building_id = args.get('building_id', '%')
        # if building_id == '*': building_id = '%'
        # logger.info("building_id = " + building_id)      
        
        cur = connectDBIfClosed()
        whereclause = f' WHERE site_id LIKE %s'
        print(whereclause)
        query = 'SELECT building_id FROM '\
            + TB_COLLECTION + whereclause + ' ORDER BY building_id ASC '
        print('query = ', query)
        cur.execute(query, (site_id,))
        records = cur.fetchall()
        print('records =========>', records)

        building_list = []
        building_set = set([])
        if len(records) > 0:
            for r in records:
                building_list.append(r[0])
            building_set = set(building_list)
            building_list = sorted(list(building_set))

            
        data = {'result':'Y', 'building_list':building_list}
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

ground_truth_name = {'A': 'ARCore', 'B': 'Backpack'}
class CollectGetDatasetDetails(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('idx', required=True, type=str, help='idx')
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        idx = args.get('idx')
        logger.info("idx = " + idx)
           
        
        cur = connectDBIfClosed()
        query = 'SELECT idx, scenario_name, site_id, building_id, floor, route_wp, dt_start, dt_end, gt, user_name, phonemodel FROM '\
            + TB_COLLECTION + ' WHERE idx = %s'
        print('query = ', query)
        cur.execute(query, (idx,))
        r = cur.fetchone()
        print('record =========>', r)

        if r == None:
            return makeErrorResponseMsgResponse('no record')

        dt_str = datetime2str(r[6])
        dt_str_end = datetime2str(r[7])
        gt = ground_truth_name[r[8].strip()]
        details = f'Scenario: {r[1]},\nSite: {r[2]},\nBuilding: {r[3]},\nFloor: {r[4]},\nRoute(waypoints): {r[5]},\n' + \
            f'Start time: {dt_str},\nEnd time: {dt_str_end},\nUser: {r[9]},\nGround Truth: {gt},\nPhone Model: {r[10]},\n'

        # d = {'idx':str(r[0]), 'scenario_name':r[1], 'site_id':r[2], 'building_id':r[3], 'floor':r[4],
        #         'route_wp':r[5], 'dt_start':dt_str, 'dt_end':dt_str_end, 'ppdirectory': r[7]}
        
        finfolist = []
        dataset_path = "."
        for path in Path(dataset_path).iterdir():
            finfo = getFileInfo(path)
            finfolist.append(finfo)
            # info = path.stat()
            # print(info.st_mtime)
    
        data = {'result':'Y', 'details':details, 'file_list':finfolist}
        # data.update(details)
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


class CollectDeleteDataset(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('idx', required=True, type=str, help='idx')
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        idx = args.get('idx')
        logger.info("idx = " + idx)
           
        
        cur = connectDBIfClosed()
        query = 'SELECT ppdirectory FROM '\
            + TB_COLLECTION + ' WHERE idx = %s'
        print('query = ', query)
        cur.execute(query, (idx,))
        r = cur.fetchone()
        if r == None: return makeErrorResponseMsgResponse('no record')
        
        
        query = 'DELETE FROM ' + TB_COLLECTION + ' WHERE idx = %s'
        print('query = ', query)
        cur.execute(query, (idx,))
        conn.commit()
    
        data = {'result':'Y'}
        # data.update(details)
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


class CollectDeletePPDataset(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('idx', required=True, type=str, help='idx')
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        idx = args.get('idx')
        logger.info("idx = " + idx)
           
        
        cur = connectDBIfClosed()
        query = 'SELECT ppdirectory FROM '\
            + TB_COLLECTION + ' WHERE idx = %s'
        print('query = ', query)
        cur.execute(query, (idx,))
        r = cur.fetchone()
        if r == None: return makeErrorResponseMsgResponse('no record')
        
        query = 'UPDATE ' + TB_COLLECTION + ' SET ppdirectory=%s WHERE idx = %s'
        print('query = ', query)
        cur.execute(query, (None, idx,))
        conn.commit()
    
        data = {'result':'Y'}
        # data.update(details)
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



class CollectPostProcessing(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('idx', required=True, type=str, help='idx')
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        idx = args.get('idx')
        logger.info("idx = " + idx)
           
        
        cur = connectDBIfClosed()
        query = 'SELECT ppdirectory FROM '\
            + TB_COLLECTION + ' WHERE idx = %s'
        print('query = ', query)
        cur.execute(query, (idx,))
        r = cur.fetchone()
        if r == None: return makeErrorResponseMsgResponse('no record')
        
        # query = 'UPDATE ' + TB_COLLECTION + ' SET ppdirectory=%s WHERE idx = %s'
        # print('query = ', query)
        # cur.execute(query, (None, idx,))
        # conn.commit()
    
        data = {'result':'Y'}
        # data.update(details)
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



class CollectPostProcStatus(Resource):
    

    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')

        try:
            parser = reqparse.RequestParser()
            parser.add_argument('idx', required=True, type=str, help='idx')
            args = parser.parse_args()
            logger.info('args = {}'.format(args))
            idx = args['idx']
            logger.info("idx = " + idx)
        
            #dummy
            data = {'result':'Y', 'status':'100'}

            #data = {'result':'Y'}
            # data.update(details)
            res = json.dumps(data, ensure_ascii=False).encode('utf8')
            print("response data = ", data)
            return Response(res, content_type='application/json; charset=utf-8')

        except Exception as e:
            logger.error(self.__class__.__name__ + ' Get : ' + str(e))
            return makeErrorResponseMsgResponse(str(e)) 


    def options (self):
        return {'Allow' : 'POST' }, 200, \
        { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*',\
        'Access-Control-Allow-Methods' : 'POST' }



########################################################################################################
# Training  학습 관리


class TrainingGetDatasetFilter(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('site_id', required=True, type=str, help='site_id')
        parser.add_argument('building_id', required=False, type=str, help='building_id')
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        site_id = args.get('site_id', '%')
        if site_id == '*': site_id = '%'
        site_id = '%'   # 우선 all 로 고정
        logger.info("site_id = " + site_id)
        
        # building_id = args.get('building_id', '%')
        # if building_id == '*': building_id = '%'
        # logger.info("building_id = " + building_id)      
        
        cur = connectDBIfClosed()
        whereclause = f' WHERE site_id LIKE %s'
        print(whereclause)
        query = 'SELECT DISTINCT building_id FROM '\
            + TB_TRAINING_DATASET + whereclause + ' ORDER BY building_id ASC '
        print('query = ', query)
        cur.execute(query, (site_id,))
        records = cur.fetchall()
        print('records =========>', records)

        building_list = []
        building_set = set([])
        if len(records) > 0:
            for r in records:
                building_list.append(r[0])
            building_set = set(building_list)
            building_list = sorted(list(building_set))

            
        data = {'result':'Y', 'building_list':building_list}
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


class TrainingGetDatasetList(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('site_id', required=False, type=str, help='site_id')
        parser.add_argument('building_id', required=False, type=str, help='building_id')
        parser.add_argument('floor', required=False, type=str, help='floor')
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        site_id = args.get('site_id', '%')
        if site_id == '*': site_id = '%'
        logger.info("site_id = " + site_id)
        
        building_id = args.get('building_id', '%')
        if building_id == '*': building_id = '%'
        logger.info("building_id = " + building_id)
        
        floor = args.get('floor', '%')
        if floor == '*': floor = '%'
        logger.info("floor = " + floor)        
        
        cur = connectDBIfClosed()
        whereclause = makeWhereClause(site_id, building_id, floor)
        print(whereclause)
        query = 'SELECT idx, site_id, building_id, floor, dt FROM '\
            + TB_TRAINING_DATASET + whereclause + ' ORDER BY dt DESC '
        print('query = ', query)
        cur.execute(query, (site_id, building_id, floor,))
        records = cur.fetchall()
        print('records =========>', records)

        data_list = []
        #if len(records) > 0:
        for r in records:
            dt_str = datetime2str(r[4])
            d = {'idx':str(r[0]), 'site_id':r[1], 'building_id':r[2], 'floor':r[3], 'dt':dt_str}
            data_list.append(d)
            
        data = {'result':'Y', 'data_list':data_list}
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



class TrainingRun(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('idx', required=True, type=str, help='idx')
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        idx = args.get('idx')
        logger.info("idx = " + idx)
           
        
        cur = connectDBIfClosed()
        query = 'SELECT * FROM '\
            + TB_TRAINING_DATASET + ' WHERE idx = %s'
        print('query = ', query)
        cur.execute(query, (idx,))
        r = cur.fetchone()
        if r == None: return makeErrorResponseMsgResponse('no record')
        
        # query = 'UPDATE ' + TB_COLLECTION + ' SET ppdirectory=%s WHERE idx = %s'
        # print('query = ', query)
        # cur.execute(query, (None, idx,))
        # conn.commit()
    
        data = {'result':'Y'}
        # data.update(details)
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


class TrainingRunStatus(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('idx', required=True, type=str, help='idx')
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        idx = args.get('idx')
        logger.info("idx = " + idx)
           
        
        cur = connectDBIfClosed()
        query = 'SELECT dirpath FROM '\
            + TB_TRAINING_DATASET + ' WHERE idx = %s'
        print('query = ', query)
        cur.execute(query, (idx,))
        r = cur.fetchone()
        if r == None: return makeErrorResponseMsgResponse('no record')
        if r[0] == None: return makeErrorResponseMsgResponse('no data')
        
        #dummy
        data = {'result':'Y', 'status':'100'}
        
        # query = 'UPDATE ' + TB_COLLECTION + ' SET ppdirectory=%s WHERE idx = %s'
        # print('query = ', query)
        # cur.execute(query, (None, idx,))
        # conn.commit()
    
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




class TrainingGetModelList(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('site_id', required=False, type=str, help='site_id')
        parser.add_argument('building_id', required=False, type=str, help='building_id')
        parser.add_argument('floor', required=False, type=str, help='floor')
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        site_id = args.get('site_id', '%')
        if site_id == '*': site_id = '%'
        logger.info("site_id = " + site_id)
        
        building_id = args.get('building_id', '%')
        if building_id == '*': building_id = '%'
        logger.info("building_id = " + building_id)
        
        floor = args.get('floor', '%')
        if floor == '*': floor = '%'
        logger.info("floor = " + floor)        
        
        cur = connectDBIfClosed()
        whereclause = makeWhereClause(site_id, building_id, floor)
        print(whereclause)
        query = 'SELECT model_id, site_id, building_id, floor, dt, confidence FROM '\
            + TB_LOC_MODEL + whereclause + ' ORDER BY dt DESC '
        print('query = ', query)
        cur.execute(query, (site_id, building_id, floor,))
        records = cur.fetchall()
        print('records =========>', records)

        data_list = []
        #if len(records) > 0:
        for r in records:
            dt_str = datetime2str(r[4])
            d = {'model_id':r[0], 'site_id':r[1], 'building_id':r[2], 'floor':r[3], 'dt':dt_str, 'confidence':str(r[5])}
            data_list.append(d)
            
        data = {'result':'Y', 'data_list':data_list}
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



class TrainingDeleteDataset(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('idx', required=True, type=str, help='idx')
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        idx = args.get('idx')
        logger.info("idx = " + idx)
           
        
        cur = connectDBIfClosed()
        query = 'SELECT dirpath FROM '\
            + TB_TRAINING_DATASET + ' WHERE idx = %s'
        print('query = ', query)
        cur.execute(query, (idx,))
        r = cur.fetchone()
        if r == None: return makeErrorResponseMsgResponse('no record')
        
        
        query = 'DELETE FROM ' + TB_TRAINING_DATASET + ' WHERE idx = %s'
        print('query = ', query)
        cur.execute(query, (idx,))
        conn.commit()
    
        data = {'result':'Y'}
        # data.update(details)
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




class TrainingDeleteModel(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('model_id', required=True, type=str, help='idx')
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        model_id = args.get('model_id')
        logger.info("model_id = " + model_id)
           
        
        cur = connectDBIfClosed()
        query = 'SELECT dt FROM '\
            + TB_LOC_MODEL + ' WHERE model_id = %s'
        print('query = ', query)
        cur.execute(query, (model_id,))
        r = cur.fetchone()
        if r == None: return makeErrorResponseMsgResponse('no record')
        
        
        query = 'DELETE FROM ' + TB_LOC_MODEL + ' WHERE model_id = %s'
        print('query = ', query)
        cur.execute(query, (model_id,))
        conn.commit()
    
        data = {'result':'Y'}
        # data.update(details)
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


######################################################################################
## 수집진행 상황 API
class CollectStatusGetJob(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('site_id', required=False, type=str, help='site_id')
        # parser.add_argument('building_id', required=False, type=str, help='building_id')
        # parser.add_argument('floor', required=False, type=str, help='floor')
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        site_id = args.get('site_id', '%')
        if site_id == '*': site_id = '%'
        logger.info("site_id = " + site_id)
        
        # building_id = args.get('building_id', '%')
        # if building_id == '*': building_id = '%'
        # logger.info("building_id = " + building_id)
        
        # floor = args.get('floor', '%')
        # if floor == '*': floor = '%'
        # logger.info("floor = " + floor)        
        
        # cur = connectDBIfClosed()
        # whereclause = makeWhereClause(site_id, '%', '%')
        # print(whereclause)
        # query = 'SELECT idx, site_id, building_id, floor, dt FROM '\
        #     + TB_COLLECTION_STATUS + whereclause + ' ORDER BY dt DESC '
        # print('query = ', query)
        # cur.execute(query, (site_id, '%', '%',))
        # records = cur.fetchall()
        # print('records =========>', records)

        # data_list = []
        # #if len(records) > 0:
        # for r in records:
        #     dt_str = datetime2str(r[4])
        #     d = {'idx':str(r[0]), 'site_id':r[1], 'building_id':r[2], 'floor':r[3], 'dt':dt_str}
        #     data_list.append(d)
        
        # dummy
        data_list = [{'id':'12', 'name':'ETRI-3004-1F', 'idlist':['12']}, {'id':'13', 'name':'ETRI-3004-3F', 'idlist':['13']}]
            
        data = {'result':'Y', 'data_list':data_list}
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



class CollectStatusGetMapdata(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('idx', required=True, type=str, help='idx')
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        idx = args.get('idx')
        logger.info("idx = " + idx)
           
        
        cur = connectDBIfClosed()
        query = 'SELECT idx, scenario_name, site_id, building_id, floor, route_wp, dt_start, dt_end, gt, user_name, phonemodel FROM '\
            + TB_COLLECTION + ' WHERE idx=%s ORDER BY dt_start DESC '
            
        print('query = ', query)
        cur.execute(query, (idx,))
        r = cur.fetchone()
        if r == None: return makeErrorResponseMsgResponse('no record')
        
        map_image = '/mapdata/ETRI/3004/3004_1F.PNG'
        # LL, LR, UL, UR
        map_rect = [{'lng':"127.367212394", "lat":"36.3798125202"}, 
                    {'lng':"127.368210944", "lat":"36.3798136260"}, 
                    {'lng':"127.367211561", "lat":"36.3803023208"}, 
                    {'lng':"127.368210118", "lat":"36.3803034266"}]
        route_wp = [{'lng':'127.36793118691 ', 'lat':'36.3800722718335'},
                    {'lng':'127.367547509083', 'lat':'36.3800725974993'},
                    {'lng':'127.367547081407', 'lat':'36.3800101107162'},
                    {'lng':'127.367589699251', 'lat':'36.3800101963372'},
                    {'lng':'127.367589529849', 'lat':'36.3799303871561'}]
    
        data = {'result':'Y', 'map_image':map_image, 'map_rect':map_rect, 'route_wp':route_wp}
        # data.update(details)
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



#test only data
x_lon = 127.36793118691
y_lat = 36.3800722718335
x_inc = -0.00001
y_inc = 0.0000001
class CollectStatusGetStatus(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('idx', required=True, type=str, help='idx')
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        idx = args.get('idx')
        logger.info("idx = " + idx)
           
        
        cur = connectDBIfClosed()
        query = 'SELECT idx, scenario_name, site_id, building_id, floor, route_wp, dt_start, dt_end, gt, user_name, phonemodel FROM '\
            + TB_COLLECTION + ' WHERE idx=%s ORDER BY dt_start DESC '
            
        print('query = ', query)
        cur.execute(query, (idx,))
        r = cur.fetchone()
        if r == None: return makeErrorResponseMsgResponse('no record')
        
        
        cur_pos = [{'lng':"127.367212394", "lat":"36.3798125202"}, 
                    {'lng':"127.368210944", "lat":"36.3798136260"}, 
                    {'lng':"127.367211561", "lat":"36.3803023208"}, 
                    {'lng':"127.368210118", "lat":"36.3803034266"}]
        route_wp = [{'lng':'127.36793118691', 'lat':'36.3800722718335'},
                    {'lng':'127.367547509083', 'lat':'36.3800725974993'},
                    {'lng':'127.367547081407', 'lat':'36.3800101107162'},
                    {'lng':'127.367589699251', 'lat':'36.3800101963372'},
                    {'lng':'127.367589529849', 'lat':'36.3799303871561'}]
    
        global x_lon, y_lat
        x_lon += x_inc
        y_lat += y_inc
        cur_pos = {'lng':str(x_lon), "lat":str(y_lat), 'floor':'1F'}
        mark_wp = "2"
        data = {'result':'Y', 'cur_pos': cur_pos, 'mark_wp':mark_wp}
        # data.update(details)
        res = json.dumps(data, ensure_ascii=False).encode('utf8')
        logger.info(f"response data = {data}")
        return Response(res, content_type='application/json; charset=utf-8')
        
        # except Exception as e:
        #     logger.error(self.__class__.__name__ + ' Get : ' + str(e))
        #     return makeErrorResponseMsgResponse(str(e)) 
  

    def options (self):
        return {'Allow' : 'POST' }, 200, \
        { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*',\
        'Access-Control-Allow-Methods' : 'POST' }


x_lon_t = 127.36793118691
y_lat_t = 36.3800722718335
x_inc_t = -0.00001
y_inc_t = 0.0000001
pos_list = []
class CollectStatusGetStatusTraj(Resource):
    
    
    def post(self):
        logger.info('called : ' + self.__class__.__name__ + ': ' + sys._getframe().f_code.co_name + '()')
        #try:
        
        parser = reqparse.RequestParser()
        parser.add_argument('idx', required=True, type=str, help='idx')
        args = parser.parse_args()
        logger.info('args = {}'.format(args))
        idx = args.get('idx')
        logger.info("idx = " + idx)
           
        
        cur = connectDBIfClosed()
        query = 'SELECT idx, scenario_name, site_id, building_id, floor, route_wp, dt_start, dt_end, gt, user_name, phonemodel FROM '\
            + TB_COLLECTION + ' WHERE idx=%s ORDER BY dt_start DESC '
            
        print('query = ', query)
        cur.execute(query, (idx,))
        r = cur.fetchone()
        if r == None: return makeErrorResponseMsgResponse('no record')
        
        
        cur_pos = [{'lng':"127.367212394", "lat":"36.3798125202"}, 
                    {'lng':"127.368210944", "lat":"36.3798136260"}, 
                    {'lng':"127.367211561", "lat":"36.3803023208"}, 
                    {'lng':"127.368210118", "lat":"36.3803034266"}]
        route_wp = [{'lng':'127.36793118691', 'lat':'36.3800722718335'},
                    {'lng':'127.367547509083', 'lat':'36.3800725974993'},
                    {'lng':'127.367547081407', 'lat':'36.3800101107162'},
                    {'lng':'127.367589699251', 'lat':'36.3800101963372'},
                    {'lng':'127.367589529849', 'lat':'36.3799303871561'}]
    
        global x_lon_t, y_lat_t, pos_list
        x_lon_t += x_inc_t
        y_lat_t += y_inc_t
        cur_pos = {'lng':str(x_lon_t), "lat":str(y_lat_t), 'floor':'1F'}
        pos_list.append(cur_pos)
        mark_wp = "2"
        data = {'result':'Y', 'cur_pos': cur_pos, 'mark_wp':mark_wp, 'pos_count':str(len(pos_list)), 'pos_traj':pos_list}
        # data.update(details)
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





    
app = Flask('LOCALIZATION API REST Interface for WEB', static_url_path='')
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
#측위자원 수집데이터세트 목록 가져오기  - POST
api.add_resource(CollectGetDatasetList, '/api/collect/get-dataset-list')
#측위자원 후처리데이터세트 목록 가져오기  - POST
api.add_resource(CollectPPGetDatasetList, '/api/collect/get-ppdataset-list')
#측위자원 수집데이터세트 필터 정보 가져오기  - POST					
api.add_resource(CollectGetDatasetFilter, '/api/collect/get-dataset-filter')
#측위자원 수집데이터세트 상세 정보 가져오기  - POST									
api.add_resource(CollectGetDatasetDetails, '/api/collect/get-dataset-details')

#측위자원 수집데이터세트 삭제하기  - POST					
api.add_resource(CollectDeleteDataset, '/api/collect/delete-dataset')
#측위자원 후처리데이터세트 삭제하기  - POST					
api.add_resource(CollectDeletePPDataset, '/api/collect/delete-ppdataset')

#측위자원 후처리 수행  - POST					
api.add_resource(CollectPostProcessing, '/api/collect/post-processing')
#측위자원 후처리 상태  - POST					
api.add_resource(CollectPostProcStatus, '/api/collect/postproc-status')

'''
'''
######################################################################################
## 학습관리 API
#측위자원 수집데이터세트 필터 정보 가져오기  - POST					
api.add_resource(TrainingGetDatasetFilter, '/api/training/get-dataset-filter')
#학습 데이터세트 목록 가져오기  - POST
api.add_resource(TrainingGetDatasetList, '/api/training/get-dataset-list')
# 학습 수행하기  - POST
api.add_resource(TrainingRun, '/api/training/run')
# 학습수행 상태  - POST					
api.add_resource(TrainingRunStatus, '/api/training/run-status')

#학습 모델 목록 가져오기  - POST
api.add_resource(TrainingGetModelList, '/api/training/get-model-list')

#측위자원 수집데이터세트 삭제하기  - POST					
api.add_resource(TrainingDeleteDataset, '/api/training/delete-dataset')
#측위자원 후처리데이터세트 삭제하기  - POST					
api.add_resource(TrainingDeleteModel, '/api/training/delete-model')


######################################################################################
## 수집진행 상황 API
#측위자원 수집 진행목록 가져오기  - POST					
api.add_resource(CollectStatusGetJob, '/api/collectstatus/get-job')
#측위자원 수집 지도자료 가져오기  - POST					
api.add_resource(CollectStatusGetMapdata, '/api/collectstatus/get-mapdata')
#측위자원 수집 진행상황 가져오기  - POST					
api.add_resource(CollectStatusGetStatus, '/api/collectstatus/get-status')
#측위자원 수집 진행상황 가져오기  - POST					
api.add_resource(CollectStatusGetStatusTraj, '/api/collectstatus/get-status-traj')

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

