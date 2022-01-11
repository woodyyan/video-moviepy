import json
import logging
import subprocess
import time

import requests
from moviepy.editor import *
from moviepy.editor import VideoFileClip
from picture import Picture
# 日志配置
from qcloud_vod.model import VodUploadRequest
from qcloud_vod.vod_upload_client import VodUploadClient
from text import Text

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger()
logger.setLevel(level=logging.INFO)

cmd_download = "curl -o %s  '%s' -H 'Connection: keep-alive' -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'  " \
               "-H 'Accept: */*' -H 'Referer: %s' -H 'Accept-Language: zh-CN,zh;q=0.9,en-US;q=0.8,en-HK;q=0.7,en;q=0.6' -H 'Range: bytes=0-' --compressed --insecure"


def main_handler(event, context):
    logger.info("start main handler")
    request_id = context.get('request_id')

    if "body" not in event.keys():
        return {"code": 410, "errorMsg": "event is not come from api gateway"}

    req_body = event['body']
    callback_url = ""
    try:
        req_param = json.loads(req_body)
        logger.info("输入参数: " + json.dumps(req_param))
        video_url = req_param['Data']['Input']['URL']
        audio = req_param['Data']['Input']['Audio']
        callback_url = req_param['Data']['Input']['CallbackURL']
        width = req_param['Data']['Input']['Resolution']['Width']
        height = req_param['Data']['Input']['Resolution']['Height']
        framerate = req_param['Data']['Input']['Framerate']
        bitrate = req_param['Data']['Input']['Bitrate']
        texts_json = req_param['Data']['Input']['Texts']
        texts = []
        for text in texts_json:
            content = text['Content']
            x = text['X']
            y = text['Y']
            size = text['Size']
            texts.append(Text(content, x, y, size))
        pictures_json = req_param['Data']['Input']['Pictures']
        pictures = []
        for picture in pictures_json:
            url = picture['URL']
            x = picture['X']
            y = picture['Y']
            width = picture['Width']
            pictures.append(Picture(url, x, y, width))
        vod_region = req_param['Data']['Output']['Vod']['Region']
        sub_app_id = req_param['Data']['Output']['Vod']['SubAppId']

        if not callback_url:
            logger.warning("Callback url是空的，请检查。")
    except Exception as err:
        message = "bad request: %s, please check." % (str(err))
        logger.error(message)
        resp = {
            'ErrorCode': 'InvalidParameter',
            'ErrorMessage': message,
            'RequestID': request_id
        }
        callback_body = {
            "Result": "Failure",
            "ErrorCode": "InvalidParameter",
            "ErrorMessage": "Invalid parameter: " + str(err),
            "RequestId": request_id
        }
        callback(callback_url, callback_body)
        return json.dumps(resp)

    try:
        logger.info('开始下载视频：' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        local_file = download(video_url)
        logger.info('视频下载完成：' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

        logger.info('开始转换分辨率：' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        clip = VideoFileClip(local_file)
        clip.set_fps(framerate)
        clip.resize(newsize=(width, height))
        logger.info('转换分辨率完成：' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

        logger.info('开始渲染视频：' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        output_video = '/tmp/output.mp4'
        clip.write_videofile(output_video, codec='mpeg4', verbose=False, audio=audio)
        logger.info('渲染视频完成：' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

        logger.info('开始上传视频：' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        uploaded_video_url = upload_vod(vod_region, sub_app_id, output_video)
        logger.info('上传视频完成：' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

        callback_body = {
            "Result": "Success",
            "Data": {
                "OutputUrl": uploaded_video_url
            },
            "RequestId": request_id
        }
    except Exception as err:
        logging.error(err)
        callback_body = {
            "Result": "Failure",
            "ErrorCode": "InternalError",
            "ErrorMessage": "internal error: " + str(err),
            "RequestId": request_id
        }
        pass

    # 回调逻辑
    callback(callback_url, callback_body)

    # 清理工作目录
    clear_files('/tmp/')

    return callback_body


# 回调逻辑。
def callback(url, data):
    if not url:
        logger.info("Callback url is empty, no need to callback.")
        return

    response = requests.post(url, json=data)
    logger.info("Callback response:", response.text.encode('utf8'))


# 视频上传VOD，sdk自动选择普通上传还是分片上传
def upload_vod(vod_region, sub_app_id, media_file_path):
    secret_id = os.environ.get("TENCENTCLOUD_SECRETID")
    secret_key = os.environ.get("TENCENTCLOUD_SECRETKEY")
    token = os.environ.get("TENCENTCLOUD_SESSIONTOKEN")
    if not vod_region:
        vod_region = os.environ.get('TENCENTCLOUD_REGION')

    client = VodUploadClient(secret_id, secret_key, token)
    request = VodUploadRequest()
    request.SubAppId = sub_app_id
    request.MediaFilePath = media_file_path
    response = client.upload(vod_region, request)
    logger.info("Upload Success. FileId: %s. MediaUrl: %s, RequestId: %s" % (response.FileId, response.MediaUrl,
                                                                             response.RequestId))
    return response.MediaUrl


def download(url):
    filename = os.path.basename(url).split('?')[0]
    (_filename, ext) = os.path.splitext(filename)
    download_file = os.path.join("/tmp", '%s_%s%s' %
                                 (_filename, int(round(time.time() * 1000)), ext))

    command = cmd_download % (download_file, url, url)
    logger.info("download media command: %s" % command)

    # 从url下载视频文件
    ret = subprocess.run(command, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, shell=True, check=True)
    if ret.returncode == 0:
        logger.info("下载[%s]完成, 详情: %s" % (url, ret.stdout))
    else:
        logger.info("下载[%s]失败, 错误: %s" % (url, ret.stderr))
        raise KeyError("下载[%s]失败, 错误: %s" % (url, ret.stderr))

    if os.path.exists(download_file):
        logger.info("下载[%s]成功, 本地文件路径：[%s]" % (url, download_file))
    else:
        logger.info("下载[%s]失败, 本地文件不存在。" % url)
        raise KeyError("下载[%s]失败, 本地文件不存在。" % url)

    return download_file


def clear_files(src):
    try:
        logger.info("clear work dir...")
        if os.path.isfile(src):
            os.remove(src)
        elif os.path.isdir(src):
            for item in os.listdir(src):
                itemsrc = os.path.join(src, item)
                clear_files(itemsrc)
    except Exception as err:
        logging.exception(err)
        pass


if __name__ == '__main__':
    event = {
        'body': '''{
                        "Action": "SpliceVideo",
                        "Data": {
                            "Input": {
                                "URL": "http://1500009267.vod2.myqcloud.com/6c9c6980vodcq1500009267/9615e7b2387702294123506819/7wSZx0KFAj8A.mp4",
                                            "Audio": true,
                                "CallbackURL": "https://enk885gn0j1qox.m.pipedream.net",
                                "Resolution": {
                                    "Width": 720,
                                    "Height": 1280
                                },
                                "Framerate": 15,
                                "Bitrate": 500,
                                "Texts": [
                                    {
                                        "Content": "xxxx",
                                        "X": 1,
                                        "Y": 2,
                                        "Size": 3
                                    },
                                    {
                                        "Content": "xxxx",
                                        "X": 1,
                                        "Y": 2,
                                        "Size": 3
                                    }
                                ],
                                "Pictures": [
                                    {
                                        "URL": "xxxx",
                                        "X": 1,
                                        "Y": 2,
                                        "Width": 3
                                    }
                                ]
                            },
                            "Output": {
                                "Vod": {
                                    "Region": "ap-beijing",
                                    "SubAppId": 1500009267
                                }
                            }
                        }
                    }'''
    }
    context = {
        "request_id": "123"
    }



    print('')
