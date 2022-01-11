import json
import logging
import os
import subprocess
import sys
import time

import requests

from qcloud_vod.model import VodUploadRequest
from qcloud_vod.vod_upload_client import VodUploadClient
from moviepy.editor import *

# 日志配置
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


if __name__ == '__main__':
    clip = VideoFileClip("/Users/yansongbai/Downloads/new.mp4").subclip(50, 60)
    video = CompositeVideoClip([clip])
    video.write_videofile("myHolidays_edited.mp4")
    print('')
