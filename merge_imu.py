'''
    Merge all IMU data
    2022. 1. H4Tech
        LocCollect 앱에서 수집한 ARCore and IMU data : pose.csv, acce.csv, gyro.csv, pres.csv, magn.csv 
        data를 동일한 간격을 데이터로 통합하여 생성
        22/3/2 most recent value interpolation 으로 추가 변경함
'''

import time, os, sys
import configparser
from time import strftime
import operator
from stat import ST_CTIME
import csv
import argparse



import logging, sys, io

##################################################################################
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

#logging.basicConfig(stream=sys.stderr, level=logging.ERROR)

program_name = __file__[:-3]
logger = logging.getLogger(program_name)
logger.setLevel(logging.INFO)
stream_hander = logging.StreamHandler()
logger.addHandler(stream_hander)

logging_filename = program_name + '.log'
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
##################################################################################

csv_files = ['pose.csv', 'acce.csv', 'gyro.csv', 'magn.csv', 'pres.csv']
#csv_files = ['magn.csv', 'pres.csv']
csv_out_header = ['time', 'tx', 'ty', 'tz', 'qx', 'qy', 'qz', 'qw', 'acc_x', 'acc_y', 'acc_z', 
                  'gy_x', 'gy_y', 'gy_z', 'mg_x', 'mg_y', 'mg_z', 'pres']
csv_out_header_str = ''.join([item+', ' for item in csv_out_header])[:-2]


import datetime

timeFmt = "%Y%m%d %H%M%S.%f"   # '20211217 151404.356'

def str2datetime(strDt):
    dt = datetime.datetime.strptime(strDt, timeFmt)
    return dt
    
'''
>>> n = datetime.datetime.now()
>>> n
datetime.datetime(2022, 1, 8, 17, 53, 19, 997059)
>>> n.timestamp()
1641631999.997059
'''
def datetime2timestamp(dt):
    return dt.timestamp()
    

startTimestamp = 0
freq = 100  #Hz
source_dir = './'
header = False

# 데이터의 처음과 마지막 시각을 timestamp로 리턴
def get_time_range(csvfname):
    data = []
    filepath = os.path.join(source_dir, csvfname)
    try:
        logger.info("data file = " + filepath)
        file = open(filepath, 'r', encoding='utf-8')    # file : 파일객체
        reader = csv.reader(file)  # csv.reader(): for loop을 돌면서 line by line read
        count  = 0
        begintime = -1
        endtime = -1
        for line in reader :
            try:
                count += 1
                if header and count == 1: continue
                line[0] = line[0].strip()
                if line[0] == '': continue
                # 숫자 값이 아니면 통과
                if not line[0][:8].isnumeric(): continue
                
                if begintime == -1:
                    begintime = str2datetime(line[0]).timestamp()
                    continue
                endtime = str2datetime(line[0]).timestamp()
                # line[0] = 0
                # line[3] = DMS2DEG(float(line[3]))
                # line[4] = DMS2DEG(float(line[4]))
            
                # data.append( line )
            except Exception as e:
                logger.error('error in file {}, line#={} ({})'.format(fname, count, str(e)))
                continue 
        file.close()
        return begintime, endtime

    except Exception as e:
        logger.error('error in file {} ({})'.format(csvfname, str(e)))
        return 0.0, 0.0

# 모든 csv 파일의 공통시간의 범위 찾기
def find_optimal_time_range():

    time_begin = -1.0
    time_end = sys.maxsize
    
    for fname in csv_files:
        b, e = get_time_range(fname)
        if b > time_begin: time_begin = b 
        if e < time_end: time_end = e
    
    return time_begin, time_end

# 모든 csv 파일의 인터폴레이션
def interpolation_time_range(time_begin, time_end, interval):
    
    for fname in csv_files:
        b, e = get_time_range(fname)
        if b > time_begin: time_begin = b 
        if e < time_end: time_end = e
    
    return time_begin, time_end

# csv data를 로드하여 xs[]와 ys[[], [], [] ...] 생성
def load_csv_data(csvfname):
    filepath = os.path.join(source_dir, csvfname)

    try:
        logger.info("\n\nload_csv_data data file =====> " + filepath)
        file = open(filepath, 'r', encoding='utf-8')    # file : 파일객체
        reader = csv.reader(file)  # csv.reader(): for loop을 돌면서 line by line read
        count  = 0
        xs = []
        ys = []
        for line in reader :
            #print('line == ', line)
            try:
                count += 1
                if header and count == 1: continue
                line[0] = line[0].strip()
                if line[0] == '': continue
                # 숫자 값이 아니면 통과
                if not line[0][:8].isnumeric(): continue
                
                xs.append(str2datetime(line[0]).timestamp())
                if len(xs) == 1:
                    for i in range(1, len(line)):
                        ys.append([float(line[i])])
                else:
                    for i in range(1, len(line)):
                        ys[i-1].append(float(line[i]))
            
                # data.append( line )
            except Exception as e:
                logger.error('\nerror in file {}, line#={} ({}), '.format(csvfname, count, str(e)))
                continue
        logger.info(f"\n\nload_csv_data data count {count} ")
            
        file.close()
        return xs, ys

    except Exception as e:
        logger.error('\n\nerror in file {} ({})\n\n'.format(csvfname, str(e)))
        return None, None
    
    
# t0 <= ta <= t1
def interpolate(tx, t0, t1, y0, y1):
    return (y1-y0) * (tx-t0)/(t1 - t0)


# t0 <= ta <= t1
def extrapolate(tx, t0, t1, y0, y1):
    return (y1-y0) * (tx-t0)/(t1 - t0)

# 가장 최근 값을 사용
def mostRecentValueInterpolate(xs, ys, startTime_sec, endTime_sec, interval_ms):
    assert startTime_sec >= xs[0]
    
    times_arr = np.arange(startTime_sec, endTime_sec, interval_ms/1000.0)
    xi = 0
    ys_out = [] # 결과 y값
    for t in times_arr:
        for i in range(xi, len(xs)):
            if xs[i] > t: break
        
        xi = i - 1
        ys_out.append(ys[xi])
    

    newarr = np.array(ys_out)

    print(f'....... mostRecentValueInterpolate result = \n{newarr}')
    #input('\n\nwait ... key ')
    return newarr



from scipy.interpolate import interp1d
import numpy as np

def linearInterpolate(xs, ys, startTime_sec, endTime_sec, interval_ms):
    interp_func = interp1d(xs, ys)

    newarr = interp_func(np.arange( startTime_sec, endTime_sec, interval_ms/1000.0))

    print(f'....... linearInterpolate result = \n{newarr}')
    #input('\n\nwait ... key ')
    return newarr
    
    
from scipy.interpolate import UnivariateSpline
def splineInterpolate(xs, ys, startTime_sec, endTime_sec, interval_ms):

    interp_func = UnivariateSpline(xs, ys)

    newarr = interp_func(np.arange(2.1, 3, 0.1))

    print(newarr)

    

# 시작 시각 부터 일정간격으로 데이터 근사값 생성
def sync_data(csvfname, startTime_sec, endTime_sec, interval_ms):
    logger.info(f'.....interval_ms = {interval_ms}')
    filepath = os.path.join(source_dir, csvfname)
    
    xs, ys = load_csv_data(filepath)
    xs_np = np.array(xs)
    arr = []
    for y in ys:
        ys_np = np.array(y)
        #arr.append(linearInterpolate(xs_np, ys_np, startTime_sec, endTime_sec, interval_ms).tolist())
        arr.append(mostRecentValueInterpolate(xs_np, ys_np, startTime_sec, endTime_sec, interval_ms).tolist())
        
    return arr
    
    

if __name__ == "__main__":
    
    program_name = __file__[:-3]
    
    parser = argparse.ArgumentParser(
        description="Merge pose and IMU data"
    )

    parser.add_argument(
        "--freq", type=int, default=100,
        help="Data Frequency (default: 100)"
    )
    # 소스 파일이 있는 동일한 디렉토리에 결과파일 생성
    parser.add_argument(
        "--source_dir", default="./",
        help="source & target directory (default: ./)"
    )
    parser.add_argument("--verbose", "-v", action="count")
    parser.add_argument(
        "--out_header", default='yes',
        help="CSV Header in output file (default: yes)"
    )
    parser.add_argument(
        "--out_filename", default='data_all.csv',
        help="CSV output file name (default: data_all.csv)"
    )
    args = parser.parse_args()
    freq = args.freq
    source_dir = args.source_dir

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
        
    
    time_begin, time_end = find_optimal_time_range()
    print(f'\n\ntime_begin = {time_begin},  time_end = {time_end}\n\n')
    
    xs = np.arange(time_begin, time_end, 1/freq)
    arr_all = [xs.tolist()]
    print(f'arr_all({len(arr_all[0])}) ==================>')

    for fname in csv_files:
        arr = sync_data(fname, time_begin, time_end, 1*1000/freq)
        arr_all += arr
    print(f'arr_all({len(arr_all[0])}) ==================>')
        
    print(f'xs({len(xs)}) ==================>', xs)
        
    print("header ====> ", csv_out_header_str)
    arr_all_T = np.array(arr_all).T.tolist()
    np.savetxt("new_file1.csv", np.array(arr_all).T, delimiter=',', header=csv_out_header_str)
    
    with open("new_file2.csv","w+") as my_csv:
        csvWriter = csv.writer(my_csv, delimiter=',', lineterminator='\n')
        if args.out_header == 'yes': csvWriter.writerow(csv_out_header)
        csvWriter.writerows(arr_all_T)
        
    f = open("new_file3.csv","w+")
    wr = csv.writer(f, quoting=csv.QUOTE_NONE, delimiter=',', lineterminator='\n')
    if args.out_header == 'yes': wr.writerow(csv_out_header)

    # for i in arr_all_T:
    #     #wr.writerow(['{:3.4e}'.format(x) for x in i])
    #     wr.writerow(['{:.3f}'.format(x) for x in i])        
        
    x = arr_all_T
    for r in arr_all_T:
        wr.writerow(['{:.3f}'.format(r[i]) if i==0 else '{:.5f}'.format(r[i]) for i in range(len(r))])        

