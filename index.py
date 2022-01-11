import json
import logging

import requests
from moviepy.editor import *
from picture import Picture
# 日志配置
from text import Text

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger()
logger.setLevel(level=logging.INFO)


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


# 回调逻辑。
def callback(url, data):
    if not url:
        logger.info("Callback url is empty, no need to callback.")
        return

    response = requests.post(url, json=data)
    logger.info("Callback response:", response.text.encode('utf8'))


if __name__ == '__main__':
    clip = VideoFileClip("/Users/yansongbai/Downloads/new.mp4").subclip(50, 60)
    video = CompositeVideoClip([clip])
    video.write_videofile("myHolidays_edited.mp4")
    print('')
