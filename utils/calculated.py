'''
Klamist，2024-2-29 21:39:33
自用版，E键交互，F是秘技。
若要换回F交互E秘技，修改__init__部分开头的字母
'''

from win32 import win32api,win32gui
import time
import cv2 as cv
import numpy as np
from .config import read_picture,model_dir
from .log import log
from cnocr import CnOcr
import os
import ctypes
from pynput import mouse, keyboard
from pynput.keyboard import Key,KeyCode
from .screenhoot import Screenhoot
class Calculated:
    def __init__(self):
        # 战技、使用按键分别是什么
        self.use_key = "e"
        self.skill_key = "f"
        if self.use_key == "e":
            self.use_pic = "interaction-e.png"
        elif self.use_key == "f":
            self.use_pic = "interaction.jpg"
        # 获取窗口句柄
        self.hwnd = win32gui.FindWindow("UnityWndClass","崩坏：星穹铁道")
        # 边框
        self.left_border = int(8)
        self.up_border = int(31)
        # 缩放比例
        ctypes.windll.user32.SetProcessDPIAware()
        self.scale = ctypes.windll.user32.GetDpiForSystem() / 96.0
        # OCR识别
        self.reader = CnOcr(det_model_name="ch_PP-OCRv3_det", rec_model_name="densenet_lite_136-fc",det_root=os.path.join(model_dir, "cnocr"), rec_root=os.path.join(model_dir, "cnstr"))
        # 键鼠控制
        self.Mouse = mouse.Controller()
        self.Keyboard = keyboard.Controller()
        # 截图控制
        self.screenshot = Screenhoot()
        # 列表比较
        self.compare_lists = lambda a, b: all(x <= y for x, y in zip(a, b))
        # 图片logs是否记录
        self.img_log_value = False
        # 战斗检测时间
        self.fight_time = 900

    def get_hwnd(self):
        self.hwnd = win32gui.FindWindow("UnityWndClass","崩坏：星穹铁道")

    def active_window(self):
        win32gui.SetForegroundWindow(self.hwnd)

    def set_windowsize(self):
        """
        说明:
            设置边框参数让截图区域正确
        """
        rect = win32gui.GetWindowRect(self.hwnd)
        w = rect[2]-rect[0]
        h = rect[3]-rect[1]
        self.left_border = (w-1920) // 2
        self.up_border = h-1080-self.left_border
        log.info(f"游戏分辨率:{w}x{h}x{self.scale}")

    def get_WindowRect(self,hwnd):
        """
        说明:
            返回准确的窗口信息
        参数:
            hwnd: 窗口句柄
        """
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        left, top, right, bottom = left+self.left_border,top+self.up_border,right-self.left_border,bottom-self.left_border
        return (left, top, right, bottom)

    def char_exp_record(self,who_shot:int,who_walk:int,mater=0):
        # 打开角色面板，打开经验值，截图
        self.key_press(str(who_shot),0.1)
        time.sleep(0.4)
        self.key_press("c",0.1)
        time.sleep(1.0)
        self.img_click("char_update.png",(1600,950,1750,1030),5)
        time.sleep(0.5)
        char_time = time.strftime("%Y-%m-%d-%H-%M-%S",time.localtime())
        left, top, right, bottom = self.get_WindowRect(self.hwnd)
        screenshot = self.screenshot.grab(left,top)
        cv.imwrite(f"./logs/{char_time}.jpg",screenshot,[cv.IMWRITE_JPEG_QUALITY, 25])
        log.info(f"已记录角色经验")
        time.sleep(0.2)
        self.key_press(Key.esc,0.1)
        time.sleep(0.4)
        self.key_press(Key.esc,0.1)
        time.sleep(0.4)
        self.check_main_interface()
        self.key_press(str(who_walk),0.1)
        time.sleep(0.2)
        # 记录材料面板
        if(mater==0):
            return
        time.sleep(0.3)
        self.key_press("b",0.1)
        time.sleep(2.5)
        if(self.img_click("material.png",(900,50,950,100),1,0.6)):
            time.sleep(1.0)
        char_time = time.strftime("%Y-%m-%d-%H-%M-%S",time.localtime())
        left, top, right, bottom = self.get_WindowRect(self.hwnd)
        screenshot = self.screenshot.grab(left,top)
        cv.imwrite(f"./logs/{char_time}.jpg",screenshot,[cv.IMWRITE_JPEG_QUALITY, 25])
        log.info(f"已记录背包材料")
        self.key_press(Key.esc,0.1)
        time.sleep(0.5)
        self.check_main_interface()

    def take_screenshot(self,points=(0,0,0,0)):
        """
        说明:
            返回BGR图像
        参数:
            points: 图像截取范围
        """
        left, top, right, bottom = self.get_WindowRect(self.hwnd)
        screenshot = self.screenshot.grab(left,top)
        if points != (0,0,0,0):
            return screenshot[points[1]:points[3],points[0]:points[2]]
        return screenshot

    def save_screenshot(self,name:str):
        """
        说明:
            保存截图名字为name至log/image
        参数"
            name: 文件名字
        """
        if self.img_log_value:
            left, top, right, bottom = self.get_WindowRect(self.hwnd)
            screenshot = self.screenshot.grab(left,top)
            cv.imwrite(f"./logs/image/{name}.jpg",screenshot,[cv.IMWRITE_JPEG_QUALITY, 25])

    def img_match(self,img,templeimg):
        """
        说明:
            返回最佳匹配系数与最佳匹配位置
        参数:
            img:原始图像
            templeimg:模板图像
        """
        res = cv.matchTemplate(img,templeimg,cv.TM_CCOEFF_NORMED)
        min_val,max_val,min_loc,max_loc = cv.minMaxLoc(res)
        return max_val,max_loc

    def img_click(self,templepath,points=(0,0,0,0),overtime=5.0,rates=0.90):
        """
        说明:
            识别到图片并点击,否则不点击
        参数:
            templepath:模板图像路径
            points:截图区域
            overtime:识别时间
            rates:对比度要求
        """
        templeimg = read_picture(templepath)
        img = self.take_screenshot(points)
        val,loc = self.img_match(img,templeimg)
        start_time = time.time()
        while val < rates and time.time() - start_time < overtime:
            img = self.take_screenshot(points)
            val,loc = self.img_match(img,templeimg)
            time.sleep(0.05)
        # log.info(f"图片点击-{val}")
        if val >= rates:
            w = templeimg.shape[1]
            h = templeimg.shape[0]
            left, top, right, bottom = self.get_WindowRect(self.hwnd)
            x = left + points[0] + loc[0] + int(w/2)
            y = top + points[1]+loc[1] + int(h/2)
            self.Mouse.position = (x,y)
            time.sleep(0.1)
            self.Mouse.press(mouse.Button.left)
            time.sleep(0.2)
            self.Mouse.release(mouse.Button.left)
            time.sleep(0.2)
            return True
        else:
            # log.info("识别超时")
            return False

    def img_check(self,templepath,points=(0,0,0,0),overtime=5.0,rates=0.90):
        """
        说明:
            识别图片返回布尔值
        参数:
            templepath:模板图像路径
            points:截图区域
            overtime:识别时间
            rates:对比度要求
        """
        templeimg = read_picture(templepath)
        img = self.take_screenshot(points)
        val,loc = self.img_match(img,templeimg)
        start_time = time.time()
        while val < rates and time.time() - start_time < overtime:
            img = self.take_screenshot(points)
            val,loc = self.img_match(img,templeimg)
            time.sleep(0.05)
        # log.info(f"图片检测-{val}")
        if val >= rates:
            return True
        else:
            return False

    def dungeon_img_click(self,templepath,points=(0,0,0,0),overtime=5.0,rates=0.90):
        """
        说明:
            识别副本图片，并点击该副本
        参数:
            templepath:模板图像路径
            points:截图区域
            overtime:识别时间
            rates:对比度要求
        """
        templeimg = read_picture(templepath)
        img = self.take_screenshot(points)
        val,loc = self.img_match(img,templeimg)
        start_time = time.time()
        while val < rates and time.time() - start_time < overtime:
            img = self.take_screenshot(points)
            val,loc = self.img_match(img,templeimg)
            time.sleep(0.05)
        # log.info(f"图片点击-{val}")
        if val >= rates:
            h = templeimg.shape[0]
            print((0,loc[1],1920,loc[1]+h))
            self.img_click("dungeon_transfer.jpg",points=(0,loc[1],1920,loc[1]+h))
        else:
            log.info("识别超时")

    def ocr_match(self,img,text:str,mode=1):
        """
        说明:
            返回匹配位置与匹配系数
        参数:
            img:图像
            text:匹配文本
            mode:匹配模式
        """
        result = self.reader.ocr(img)
        nums = len(text)
        ocr_num = 0
        # print(result)
        for res in result:
            loc = res['position']
            content = str(res['text']).replace(" ", "")
            rate = res['score']
            # 完全匹配
            if mode == 1:
                if text == content:
                    x = int((loc[0][0]+loc[1][0]+loc[2][0]+loc[3][0])/4)
                    y = int((loc[0][1]+loc[1][1]+loc[2][1]+loc[3][1])/4)
                    return (x,y),rate
            # 部分匹配/误差字数为1
            if mode == 2:
                for t in text:
                    if t in content[ocr_num:]:
                        ocr_num = ocr_num + 1
                if ocr_num >= nums - 1:
                    x = int((loc[0][0]+loc[1][0]+loc[2][0]+loc[3][0])/4)
                    y = int((loc[0][1]+loc[1][1]+loc[2][1]+loc[3][1])/4)
                    return (x,y),rate
        return (0,0),0

    def ocr_click(self,text:str,points=(0,0,0,0),overtime=5.0,rates=0.1,mode=1):
        """
        说明:
            识别到文本点击，否则不点击
        参数:
            text:需要检测的文本内容
            points:截图区域
            overtime:识别时间
            rates:对比度要求
            mode:匹配模式
        """
        img = self.take_screenshot(points)
        pos,rate = self.ocr_match(img,text,mode)
        start_time = time.time()
        while rate < rates and time.time() - start_time < overtime:
            img = self.take_screenshot(points)
            pos,rate = self.ocr_match(img,text,mode)
            time.sleep(0.05)
        if rate >= rates:
            # log.info(f"OCR点击-{rate}")
            left, top, right, bottom = self.get_WindowRect(self.hwnd)
            x = left + points[0] + pos[0]
            y = top + points[1] + pos[1]
            self.Mouse.position = (x,y)
            time.sleep(0.1)
            self.Mouse.press(mouse.Button.left)
            time.sleep(0.2)
            self.Mouse.release(mouse.Button.left)
            time.sleep(0.2)
            return True
        else:
            log.warning(f"OCR点击失败-{rate}")
            return False

    def ocr_check(self,text:str,points=(0,0,0,0),overtime=5.0,rates=0.1,mode=1):
        """
        说明:
            识别文本返回布尔值
        参数:
            text:需要检测的文本内容
            points:截图区域
            overtime:识别时间
            rates:对比度要求
            mode:匹配模式
        """
        img = self.take_screenshot(points)
        pos,rate = self.ocr_match(img,text,mode)
        start_time = time.time()
        while rate < rates and time.time() - start_time < overtime:
            img = self.take_screenshot(points)
            pos,rate = self.ocr_match(img,text,mode)
            time.sleep(0.05)
        if rate >= rates:
            return True
        else:
            return False

    def mouse_pos(self,points):
        """
        说明:
            返回实际鼠标坐标
        参数:
            points:相对游戏坐标
        """
        left, top, right, bottom = self.get_WindowRect(self.hwnd)
        x = left + points[0]
        y = top + points[1]
        return (x,y)

    def mouse_click(self):
        """
        说明:
            鼠标点击
        """
        self.Mouse.press(mouse.Button.left)
        time.sleep(0.3)
        self.Mouse.release(mouse.Button.left)

    def key_press(self,key,times=1.0):
        self.Keyboard.press(key)
        start_time = time.perf_counter()
        while time.perf_counter() - start_time < times:
            pass
        self.Keyboard.release(key)

    def move(self,key:str = ["w","a","s","d"],times=1.0):
        """
        说明:
            移动
        参数:
            key:方位按键
            times:执行时间
        """
        log.info(f"执行{key}---{times}")
        self.Keyboard.press(key)
        start_time = time.perf_counter()
        while time.perf_counter() - start_time < times:
            pass
        self.Keyboard.release(key)

    def mouse_move(self,value:int):
        time.sleep(0.2)
        log.info(f"视角转向{value}")
        win32api.mouse_event(1,int(value*self.scale),0)
        time.sleep(0.4)

    def has_red(self, points=(0,0,0,0)):
        """
        说明:
            判断游戏指定位置是否有红色
        参数:
            points: 图像截取范围
        """
        img = self.take_screenshot(points)
        hsv_img = cv.cvtColor(img, cv.COLOR_BGR2HSV)

        lower_red = np.array([0, 100, 100])
        upper_red = np.array([10, 255, 255])
        lower_red2 = np.array([170, 100, 100])
        upper_red2 = np.array([180, 255, 255])

        mask1 = cv.inRange(hsv_img, lower_red, upper_red)
        mask2 = cv.inRange(hsv_img, lower_red2, upper_red2)
        mask = cv.bitwise_or(mask1, mask2)
        # 统计掩膜中的像素数目
        pixel_count = cv.countNonZero(mask)
        return pixel_count > 50

    def has_purple(self, points=(0,0,0,0)):
        """
        说明:
            判断游戏指定位置是否有紫色
        参数:
            points: 图像截取范围
        """
        img = self.take_screenshot(points)
        hsv_img = cv.cvtColor(img, cv.COLOR_BGR2HSV)
        lower = np.array([125, 43, 46])
        upper = np.array([175, 255, 255])
        mask = cv.inRange(hsv_img,lower,upper)
        # 统计掩膜中的像素数目
        pixel_count = cv.countNonZero(mask)
        return pixel_count > 700

    def get_whiteimg(self,img):
        """
        说明:
            对白色做提取处理,返回RGB图像
        参数:
            img:提供的原始图片
        """
        hsv_img = cv.cvtColor(img, cv.COLOR_BGR2HSV)
        # 设置白色提取范围
        lower_white = np.array([0,0,70])
        upper_white = np.array([180,43,255])

        mask = cv.inRange(hsv_img,lower_white,upper_white)
        # 维度扩充并归一化
        mask = cv.merge([mask,mask,mask])
        return mask

    def get_pix_hsv(self,points=(0,0)):
        """
        说明:
            返回hsv像素值
        参数:
            points:相对游戏坐标
        """
        img = self.take_screenshot()
        hsv = cv.cvtColor(img, cv.COLOR_RGB2HSV)
        x = points[0]
        y = points[1]
        h = hsv[y,x,0]
        s = hsv[y,x,1]
        v = hsv[y,x,2]
        return [h,s,v]

    def fighting(self,mode=1):
        if mode == 1:   # 打怪
            log.info("打怪")
            self.Mouse.click(mouse.Button.left)
            time.sleep(1)
            self.wait_fight_end()
            return True
        else:   # 打障碍物
            log.info("打罐子")
            self.Mouse.click(mouse.Button.left)
            time.sleep(0.8)
            return True

    def wait_main_interface(self):
        start_time = time.time()    # 开始计算等待时间
        while True:
            if self.img_check("liaotian.png",(20,900,80,970),0.3):
                break
            if self.img_click("fighting_lost.jpg",(700,140,1200,400),0.1):
                log.info("战斗失败")
                break
            time.sleep(0.3)
            if time.time() - start_time > self.fight_time:
                return False
        time.sleep(1.0)   # 等待人物模型出现
        return True

    def check_main_interface(self):
        log.info("强制在主界面")
        if self.img_check("liaotian.png",(20,900,80,970),7):
            time.sleep(1.0)   # 等待人物模型出现
        else:
            while not self.img_check("liaotian.png",(20,900,80,970),1):
                self.Keyboard.press(Key.esc)
                time.sleep(0.05)
                self.Keyboard.release(Key.esc)
                time.sleep(1)
        return True

    def wait_fight_end(self):
        """
        说明:
            等待战斗结束
        """
        start_time = time.time()
        while self.img_check("liaotian.png",(20,900,80,970),1):
            if self.img_check("z.png",(750,0,850,100),1) or self.has_red((50,68,230,245)):
                time.sleep(1)
            else:
                break
            if time.time() - start_time > 7:
                break
        if not self.img_check("liaotian.png",(20,900,80,970),0.5):
            log.info("等待战斗结束")
            self.wait_main_interface()

    def interaction(self,mode:str = ["w","a","s","d"]):
        """
        说明:
            等待传送结束
        """
        log.info("执行交互")
        time.sleep(0.5)   # 截图识别延时性修复
        start_time = time.time()    # 开始计算等待时间
        while not self.img_check(self.use_pic,(1050,580,1250,660),1):
            self.Keyboard.press(mode)
            time.sleep(0.1)
            self.Keyboard.release(mode)
            # 超时中断
            if time.time() - start_time > 20:
                return False
        time.sleep(0.5)
        self.Keyboard.press(self.use_key)
        time.sleep(0.05)
        self.Keyboard.release(self.use_key)
        time.sleep(2)   # 缓冲
        self.wait_main_interaction()

    def wait_main_interaction(self):
        """
        说明:
            交互检测主页面
        """
        start_time = time.time()    # 开始计算等待时间
        while True:
            if self.img_check("one.jpg",(1860,300,1900,350),0.3):
                break
            # 遥梦之眼交互
            if self.img_check("map_4-1_point_6.png",(1352,646,1480,700),overtime=0.3):
                if self.img_check("map_4-1_point_7.png",(540,840,810,1080),overtime=2.5):
                    self.img_click("map_4-1_point_8.png",(1298,727,1352,789),overtime=0.5)
                else:
                    self.img_click("map_4-1_point_6.png",(1352,646,1480,700),overtime=0.5)
            # 界域定锚退出
            if self.img_click("exit.jpg",(1820,20,1900,100),overtime=0.3):
                break
            time.sleep(0.3)
            if time.time() - start_time > 30:
                return False
        time.sleep(1)   # 等待人物模型出现
        return True

    def open_map(self):
        """
        说明:
            打开地图
        """
        log.info("进入地图")
        while not self.img_check("map_navigation.jpg",(40,40,100,100),0.8):
            self.Keyboard.press("m")
            time.sleep(0.05)
            self.Keyboard.release("m")
            # 稚子的梦返回地图界面
            self.Mouse.position = self.mouse_pos((250,900))
            time.sleep(1.0)
            self.img_click("return.jpg",overtime=0.8,rates=0.85)

    def release_mouse_keyboard(self):
        """
        说明:
            释放键鼠操作
        """
        self.Mouse.release(mouse.Button.left)
        self.Mouse.release(mouse.Button.right)
        for key in ["w","a","s","d","f","e","r",Key.esc,Key.shift_l]:
            self.Keyboard.release(key)
        return True

    def turn_video_record(self):
        self.Keyboard.press(KeyCode.from_vk(103))
        time.sleep(0.05)
        self.Keyboard.release(KeyCode.from_vk(103))

    def close_game(self,mode):
        """
        说明:
            关闭模式
        """
        # 关闭游戏
        self.turn_video_record()
        if mode >= 1:
            self.Keyboard.press(Key.esc)
            time.sleep(0.05)
            self.Keyboard.release(Key.esc)
            self.img_click("exit1.png")
            self.img_click("sure.jpg")
            self.img_click("exit2.png",overtime=60)
            self.img_click("sure2.png",overtime=10)
        else:
            return False
        time.sleep(10)
        # 关机
        if mode == 2:
            os.system('shutdown /s /t 30')
        # 注销
        if mode == 3:
            os.system('shutdown /l')
        # 关闭程序
        self.Keyboard.press(Key.f10)
        time.sleep(0.05)
        self.Keyboard.release(Key.f10)
        return True

    def change_team(self,teamid:int,id:int):
        """
        说明:
            切换队伍
        """
        if teamid > 0 and teamid <= 9:
            log.info("切换队伍")
            self.Keyboard.press('t')
            time.sleep(0.5)
            self.Keyboard.release('t')
            time.sleep(1)   # 缓冲
            teamid = '0' + str(teamid)
            # 向后滚动
            if not self.ocr_check(text=teamid,points=(550,0,1800,130),overtime=1):
                self.Mouse.position = self.mouse_pos((1300,60))
                for j in range(8):
                    time.sleep(0.05)
                    self.Mouse.scroll(0,-200)
            # 向前滚动
            if not self.ocr_check(text=teamid,points=(550,0,1800,130),overtime=1):
                self.Mouse.position = self.mouse_pos((1300,60))
                for j in range(8):
                    time.sleep(0.05)
                    self.Mouse.scroll(0,200)
            self.ocr_click(text=teamid,points=(550,0,1800,130),overtime=2)
            self.ocr_click(text=teamid,points=(550,0,1800,130),overtime=2)
            self.img_click("team_sure.png",points=(1500,950,1920,1080),overtime=2)
            time.sleep(2)   # 缓冲
            self.Keyboard.press(Key.esc)
            time.sleep(0.05)
            self.Keyboard.release(Key.esc)
            self.check_main_interface()
        if id >= 1 and id <= 4:
            log.info("切换角色")
            id = str(id)
            self.Keyboard.press(id)
            time.sleep(0.05)
            self.Keyboard.release(id)
            if self.img_click("sure.jpg",overtime=0.5):
                self.img_click("exit3.jpg",overtime=0.5)
                self.check_main_interface()
                self.Keyboard.press(id)
                time.sleep(0.05)
                self.Keyboard.release(id)

    def login(self):
        """
        说明:
            登录功能
        """
        log.info("登录界面")
        for i in range(3):
            while not self.img_check("liaotian.png",(20,900,80,970),1):
                self.Mouse.position = self.mouse_pos((950,900))
                self.Mouse.click(mouse.Button.left)
                time.sleep(1.5)

    def use_skill(self,food:bool = True,skill_time=1):
        """
        说明:
            使用秘技
        """
        log.info("使用秘技")
        if self.has_purple((1650,850,1800,880)):
            if food:
                self.Keyboard.press(self.skill_key)
                time.sleep(0.1)
                self.Keyboard.release(self.skill_key)
                if self.img_click("sure.jpg",overtime=0.5):
                    self.img_click("exit3.jpg",overtime=0.5)
                    self.img_check("liaotian.png",(20,900,80,970),1)
                    self.Keyboard.press(self.skill_key)
                    time.sleep(0.1)
                    self.Keyboard.release(self.skill_key)
                    time.sleep(skill_time)
                    return True
                else:
                    self.img_click("exit3.jpg",overtime=0.5)
                    if self.img_check("liaotian.png",(20,900,80,970),1):
                        return False
        else:
            self.Keyboard.press(self.skill_key)
            time.sleep(0.1)
            self.Keyboard.release(self.skill_key)
            time.sleep(skill_time)
        return food

    def run_change(self,mode:int = 1):
        """
        说明:
            疾跑切换模式
        """
        starttime = time.time()
        maxtime = 100
        while not self.img_check("exit1.png",overtime=1.5) and time.time() - starttime < maxtime:
            self.Keyboard.press(Key.esc)
            time.sleep(0.05)
            self.Keyboard.release(Key.esc)
        self.img_click("setting1.jpg",overtime=2)
        self.img_click("setting2.jpg",overtime=2)
        time.sleep(1)
        for i in range(8):
            self.Mouse.position = self.mouse_pos((1300,360))
            for j in range(3):
                self.Mouse.scroll(0,-200)
        time.sleep(1)
        self.Mouse.position = self.mouse_pos((1300,360))
        self.Mouse.press(mouse.Button.left)
        time.sleep(0.5)
        self.Mouse.release(mouse.Button.left)
        if mode == 0:
            self.ocr_click(text='通过按钮切换',points=(1400,410,1600,550),overtime=3,mode=2)
        if mode == 1:
            self.ocr_click(text='长按进入疾跑状态',points=(1400,410,1600,550),overtime=3,mode=2)
        while not self.img_check("liaotian.png",(20,900,80,970),overtime=1.5) and time.time() - starttime < maxtime:
            self.Keyboard.press(Key.esc)
            time.sleep(0.05)
            self.Keyboard.release(Key.esc)

    def rotate_img(self,img,angle):
        """
        说明:
            返回旋转后的图片
        """
        h, w, _ = img.shape
        center = (w // 2, h // 2)
        # 构建旋转变换矩阵
        matrix = cv.getRotationMatrix2D(center, angle, 1.0)
        # 应用旋转变换并得到结果图像
        result = cv.warpAffine(img, matrix, (w,h))
        return result

    def get_loc_angle(self):
        """
        说明:
            返回当前蓝色箭头位置角度
        """
        self.Keyboard.press('w')
        time.sleep(0.05)
        self.Keyboard.release('w')
        time.sleep(0.55)
        arrow = read_picture("arrow.png")
        img = self.take_screenshot((120,131,160,171))
        hsv = cv.cvtColor(img, cv.COLOR_BGR2HSV)  # 转HSV
        # 设置蓝色提取范围
        lower = np.array([91, 120, 60])
        upper = np.array([98, 255, 255])
        mask = cv.inRange(hsv, lower, upper)  # 创建掩膜
        arrow_now = cv.bitwise_and(img,img, mask=mask)
        # cv.imwrite("arrow.png",arrow_now)  # 记录当前截图
        best_val = 0.00
        angle = 0
        for i in range(360):
            rotate_arrow = self.rotate_img(arrow,i)
            res = cv.matchTemplate(arrow_now,rotate_arrow,cv.TM_CCOEFF_NORMED)
            _,max_val,_,loc = cv.minMaxLoc(res)
            # log.info(f"{i}角度，系数{max_val}")
            if best_val < max_val:
                angle = i
                best_val = max_val
        return angle

    def correct_loc_angle(self,angle):
        """
        说明:
            校准蓝色箭头位置角度
        """
        self.wait_main_interaction()
        angle_now = self.get_loc_angle()
        rotate_angle = angle_now - angle
        if rotate_angle > 180:
            rotate_angle -= 360
        elif rotate_angle < -180:
            rotate_angle += 360
        self.mouse_move(6150*rotate_angle/360)
        log.info(f"转向{angle}")

    def map_pos(self,mappath:str):
        """
        说明:
            返回识别到地图坐标
        """
        # 老方法
        # CenterBlue = [255,220,0]
        # CenterBlue1 = [200,170,10]
        # CenterBlue2 = [250,210,60]
        # CircleBlue = [220,200,120]
        # # 获取小地图
        # img = self.take_screenshot((80,90,200,210))
        # w = img.shape[1]
        # h = img.shape[0]
        # # 去除中心蓝色
        # img = cv.bitwise_and(img,img)
        # mask_img = img[45:75,45:75]
        # mask_img[abs(np.sum(mask_img-CenterBlue,axis=-1)) < 50] = [55,55,55]
        # mask_img[abs(np.sum(mask_img-CenterBlue1,axis=-1)) < 30] = [55,55,55]
        # mask_img[abs(np.sum(mask_img-CenterBlue2,axis=-1)) < 20] = [55,55,55]
        # # 去除蓝色圆点
        # for i in range(h):
        #     for j in range(w):
        #         color = img[i,j]
        #         if abs(color[0]-CircleBlue[0]) < 10 and abs(color[1]-CircleBlue[1]) < 10 and abs(color[2]-CircleBlue[2]) < 10:
        #             img[i,j] = [55,55,55]
        # mapimg = read_picture(mappath)
        # res = cv.matchTemplate(mapimg,img,cv.TM_CCOEFF_NORMED)
        # min_val,max_val,min_loc,loc = cv.minMaxLoc(res)
        # realx = loc[0]+60
        # realy = loc[1]+60
        # cv.circle(mapimg,(realx,realy),2,(0,0,255),-1)
        # cv.imshow("result",mapimg)
        # cv.waitKey(5)
        # 获取小地图
        img = self.take_screenshot((80,90,200,210))
        bigmap = cv.imread(mappath)
        bigmapedge = cv.Canny(bigmap, 15, 50)
        # 缩放匹配
        scale_list = [0.95,1.00, 1.05, 1.10, 1.15, 1.20, 1.25,1.30]
        best_scale = 1.00
        best_val = 0.00
        for scale in scale_list:
            local = cv.resize(img, None, fx=scale, fy=scale, interpolation=cv.INTER_CUBIC)
            # Canny边缘处理
            local = cv.GaussianBlur(local, (5, 5), 0)
            edge = cv.Canny(local, 15, 50)
            res = cv.matchTemplate(bigmapedge,edge,cv.TM_CCOEFF_NORMED)
            _,max_val,_,loc = cv.minMaxLoc(res)
            if best_val < max_val:
                best_scale = scale
                best_val = max_val
        local = cv.resize(img, None, fx=best_scale, fy=best_scale, interpolation=cv.INTER_CUBIC)
        local = cv.GaussianBlur(local, (5, 5), 0)
        edge = cv.Canny(local, 15, 50)
        res = cv.matchTemplate(bigmapedge,edge,cv.TM_CCOEFF_NORMED)
        _,max_val,_,loc = cv.minMaxLoc(res)
        w = local.shape[0]
        h = local.shape[1]
        realx = loc[0] + w//2
        realy = loc[1] + h//2
        # cv.circle(bigmap,(realx,realy),2,(0,0,255),-1)
        # cv.imshow("result",bigmap)
        # cv.waitKey(5)
        return (realx,realy)
