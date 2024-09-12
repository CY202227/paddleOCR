import os
import cv2
import time
import yaml
import uuid
import json
from datetime import timedelta
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from paddleocr import PaddleOCR,draw_ocr
from werkzeug import run_simple
from gevent import pywsgi
#from gevent.pywsgi import WSGIServer

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(hours=1)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

def allowed_file(fname):
    return '.' in fname and fname.rsplit('.', 1)[1].lower() in ['png', 'jpg', 'jpeg']

def allowed_pdf(fname):
    return '.' in fname and fname.rsplit('.', 1)[1].lower() in ['pdf']


@app.route("/")
def index():
    return render_template('index.html')
    
@app.route('/ocr', methods=['POST', 'GET'])
def detect():
    file = request.files['file']
    ocr = PaddleOCR(use_angle_cls=True, lang="ch")
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1]
        random_name = '{}.{}'.format(uuid.uuid4().hex, ext)
        savepath = os.path.join('caches', secure_filename(random_name))
        file.save(savepath)
        # time-1
        t1 = time.time()
        img = cv2.imread(savepath)
        img_result = ocr.ocr(img)
        # time-2
        t2 = time.time()
        for idx in range(len(img_result)):
            res = img_result[idx]
            for line in res:
                print(line)

        '''
        识别结果将分别返回
        '''
        results = []
        #for i in range(len(img_result)):
        #results.append(img_result[0])
        from PIL import Image, ImageDraw, ImageFont

        result = img_result[0]
        image = Image.open(savepath).convert('RGB')
        boxes = [line[0] for line in result]
        txts = [line[1][0] for line in result]
        scores = [line[1][1] for line in result]
        im_show = draw_ocr(image, boxes, txts, scores, font_path='/path/to/PaddleOCR/doc/fonts/simfang.ttf')
        im_show = Image.fromarray(im_show)

        return jsonify({
            'Status': 'success',
            'Position': boxes,
            'Results': txts,
            'Score': scores,
            'Time': '{:.4f}s'.format(t2-t1),
            'Img': im_show.show()
        })
    return jsonify({'Status': 'faild'})


@app.route('/pdf', methods=['POST', 'GET'])
def detectPdf():
    file = request.files['file']
    PAGE_NUM = 10
    ocr = PaddleOCR(use_angle_cls=True, lang="ch", page_num=PAGE_NUM)
    if file and allowed_pdf(file.filename):
        ext = file.filename.rsplit('.', 1)[1]
        random_name = '{}.{}'.format(uuid.uuid4().hex, ext)
        savepath = os.path.join('caches', secure_filename(random_name))
        file.save(savepath)
        # time-1
        t1 = time.time()
        result = ocr.ocr(savepath, cls=True)
        for idx in range(len(result)):
            res = result[idx]
            if res == None:  # 识别到空页就跳过，防止程序报错 / Skip when empty result detected to avoid TypeError:NoneType
                print(f"[DEBUG] Empty page {idx + 1} detected, skip it.")
                continue
            #for line in res:
                #print(line)
        #time-2
        t2 = time.time()
        import fitz
        from PIL import Image
        import numpy as np
        imgs = []
        with fitz.open(savepath) as pdf:
            for pg in range(0, pdf.page_count):
                page = pdf[pg]
                mat = fitz.Matrix(2, 2)
                pm = page.get_pixmap(matrix=mat, alpha=False)
                # if width or height > 2000 pixels, don't enlarge the image
                if pm.width > 2000 or pm.height > 2000:
                    pm = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)

                img = Image.frombytes("RGB", [pm.width, pm.height], pm.samples)
                img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                imgs.append(img)
        for idx in range(len(result)):
            res = result[idx]
            image = imgs[idx]
            boxes = [line[0] for line in res]
            txts = [line[1][0] for line in res]
            scores = [line[1][1] for line in res]
            im_show = draw_ocr(image, boxes, txts, scores, font_path='doc/fonts/simfang.ttf')
            im_show = Image.fromarray(im_show)
            #im_show.save('result_page_{}.jpg'.format(idx))

        return jsonify({
            'Status': 'success',
            'Position': boxes,
            'Results': txts,
            'Score': scores,
            'Time': '{:.4f}s'.format(t2 - t1),
            'Img': im_show.show()
        })
    return jsonify({'Status': 'faild'})

@app.route('/ocrplus', methods=['POST', 'GET'])
def detectocrp():
    ocr = PaddleOCR(use_angle_cls=True, lang="en")
    file = request.files['file']
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1]
        random_name = '{}.{}'.format(uuid.uuid4().hex, ext)
        savepath = os.path.join('caches', secure_filename(random_name))
        file.save(savepath)
        # time-1
        t1 = time.time()
        slice = {'horizontal_stride': 300, 'vertical_stride': 500, 'merge_x_thres': 50, 'merge_y_thres': 35}
        results = ocr.ocr(savepath, cls=True)
        from PIL import Image, ImageDraw, ImageFont
        #time-2
        t2 = time.time()
        image = Image.open(file).convert("RGB")
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("./doc/fonts/simfang.ttf", size=20)  # 根据需要调整大小

        # 处理并绘制结果
        for res in results:
            for line in res:
                box = [tuple(point) for point in line[0]]
                # 找出边界框
                box = [(min(point[0] for point in box), min(point[1] for point in box)),
                       (max(point[0] for point in box), max(point[1] for point in box))]
                txt = line[1][0]
                draw.rectangle(box, outline="red", width=2)  # 绘制矩形
                draw.text((box[0][0], box[0][1] - 25), txt, fill="blue", font=font)  # 在矩形上方绘制文本

        return jsonify({
            'Status': 'success',
            'Results': txt,
            'Time': '{:.4f}s'.format(t2-t1),
            'Img': image.show()
        })
    return jsonify({'Status': 'faild'})



if __name__ == '__main__':

    ocr = PaddleOCR(use_angle_cls=True,use_gpu=False)
    server = pywsgi.WSGIServer(('0.0.0.0', 5000), app)
    server.serve_forever()
    #app.run(host='127.0.0.1', port=5000, debug=True, threaded=True, processes=1)
    '''
    app.run()中可以接受两个参数，分别是threaded和processes，用于开启线程支持和进程支持。
    1.threaded : 多线程支持，默认为False，即不开启多线程;
    2.processes：进程数量，默认为1.
    '''