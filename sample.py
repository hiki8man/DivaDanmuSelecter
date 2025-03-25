# -*- coding: utf-8 -*-
import asyncio
import http.cookies
from typing import *
from aioconsole import ainput
import aiohttp
import blivedm
import blivedm.models.web as web_models
from pathlib import Path
import tomllib,psutil,pymem
import sys,time,logging
import json
import aiofiles
import keyboard

with open("config.toml","rb") as f:
    config = tomllib.load(f)

SongSearchTitle = config["SongSearchTitle"]
SongSelectTitle = config["SongSelectTitle"]

def cleartxt(clearall = True):
    with open("SongSearch.txt", "w", encoding="UTF-8") as f:
        f.write(SongSearchTitle)
    if clearall:
        with open("SongSelect.txt", "w", encoding="UTF-8") as f:
            f.write(SongSelectTitle)

def custom_excepthook(exc_type, exc_value, traceback_obj):

    # 记录异常到日志文件
    logging.error("程序崩溃", exc_info=(exc_type, exc_value, traceback_obj))

    
    # 控制台输出
    sys.__excepthook__(exc_type, exc_value, traceback_obj)
    print("\n程序遇到异常，将在 5 秒后退出...")
    time.sleep(5)
    sys.exit(1)

sys.excepthook = custom_excepthook

SelectIDList = []
IDlock = asyncio.Lock()
SElock = asyncio.Lock()
changesonglock = asyncio.Lock()
class IDManager:
    ID_dict = {}
    Name_dict = {}
    
    def __init__(self):
        with open(r"Data\HanziKanjiDict.txt","r",encoding="UTF-8") as f:
            Hanzi_list = []
            Kanji_list = []
            for text in f.readlines():
                text_sp = text.split()
                Hanzi_list.append(text_sp[0])
                Kanji_list.append(text_sp[1])
        Hanzi_Kanji_dict = dict(zip(Hanzi_list,Kanji_list))
        self.Hanzi_Kanji = str.maketrans(Hanzi_Kanji_dict)
    
    def CheckID(self,_id):
        if _id in IDManager.ID_dict.keys():
            return True
        else:
            return False
    
    def SearchName(self,_Name:str):
        funcs = [self.__Search_Str,self.__Search_Hanzi2Kanji,self.__Search_AnotherName]
        for func in funcs:
            ans = func(_Name)
            if ans:
                return ans
        return []
    
    def __Search_Str(self,_Name:str):
        return self.__SearchName(_Name)
    
    def __Search_Hanzi2Kanji(self,_Name:str):
        new_Name = _Name.translate(self.Hanzi_Kanji)
        return self.__SearchName(new_Name)
    
    def __Search_AnotherName(self,_Name:str):
        ans = []
        with open(r"Data\AnotherSongName.json","r",encoding="UTF-8") as f:
            AnotherNameDict = json.load(f)
        for SongName in AnotherNameDict.keys():
            if _Name.lower() in SongName.lower():
                ans += self.__SearchName(AnotherNameDict[SongName])
        return ans
    
    def __SearchName(self,_Name):
        ans = []
        for SongName in IDManager.Name_dict.keys():
            if _Name.lower() in SongName.lower():
                ans.append(f"{SongName}：{IDManager.Name_dict[SongName]}\n")
        return ans
            
    def __GetDIVAFolder(self):
        try:
            pid = pymem.Pymem('DivaMegaMix.exe').process_id
            process = psutil.Process(pid)
            Mega_Folder = Path(process.exe()).parent
        except pymem.exception.ProcessNotFound:
            raise OSError("游戏进程不存在")
        return Mega_Folder
    
    def Read_M39ID(self):
        self.ReadPVDB(Path(r"Data\pv_db.txt"))
        DLC_CPK = self.__GetDIVAFolder().joinpath("diva_dlc00_region.cpk")
        if DLC_CPK.exists():
            self.ReadPVDB(Path(r"Data\mdata_pv_db.txt"))
    
    def GetModList(self):
        #利用游戏读取DML文件路径从而定位MOD文件夹位置
        #如果没有配置文件则默认认为没有安装DML
        #DML有 priority 定义MOD读取顺序
        #如果没有则是按照文件名顺序读取
        #暂时只处理mod_pv_db
        _path = self.__GetDIVAFolder()
        toml_path = _path.joinpath("config.toml")
        if not toml_path.exists():
            raise OSError("无法找到游戏目录下DML的配置文件")
        with open(toml_path,"rb") as f:
            dmlconfig = tomllib.load(f)
        if not "mods" in dmlconfig:
            raise KeyError("配置文件中没有指定mods文件夹路径")
        mods_path = _path.joinpath(dmlconfig["mods"])
        if "priority" in dmlconfig:
            mods_file_list = [mods_path.joinpath(item) for item in dmlconfig["priority"]]
        else:
            mods_file_list = [item for item in mods_path.iterdir() if item.is_dir()]
        mods_list = [item.joinpath(r"rom\mod_pv_db.txt") for item in mods_file_list if item.joinpath(r"rom\mod_pv_db.txt").exists()]
        for Mod in mods_list:
            self.ReadPVDB(Mod)

    def ReadPVDB(self,_file):
        with open(_file,"r",encoding="UTF-8") as f:
            text_list = f.readlines()
        New_ID_dict = self.__GetInfo(text_list)
        self.__Updata(New_ID_dict)
    
    def __Updata(self,New_ID_dict):
        IDManager.ID_dict = New_ID_dict | IDManager.ID_dict
        New_Name_dict = {}
        for key, value in IDManager.ID_dict.items():
            New_Name_dict.setdefault(value, []).append(key)
        IDManager.Name_dict = New_Name_dict
    
    def __GetInfo(self,text_list):
        id_list = []
        name_list = []
        for info in text_list:
            info_id = info.split(".song_name=")[0][3:]
            if info_id.isdigit() and id_list.count(int(info_id)) == 0 :
                id_list.append(int(info_id))
                name_list.append(info.split(".song_name=")[1].replace("\n",""))
        return dict(zip(id_list,name_list))

class SongSelect:
    
    def __init__(self):
        self.pm = pymem.Pymem('DivaMegaMix.exe')
        self.LastSelectPVIDMem = self.pm.base_address + int("0x12B6350" , 16)
        self.LastSelectSortMem = self.pm.base_address + int("0x12B6354" , 16)
        self.LastSelectDiffMem = self.pm.base_address + int("0x12B635C" , 16)
        self.EdenOffsetMem     = int("0x105F460" , 16)
        self.ChangeSongSelect  = self.pm.base_address + int("0xCC61098" , 16)
        self.StartChange       = self.pm.base_address + int("0xCC610A0" , 16)
        self.__EdenCheck()
        
    def __EdenCheck(self):
        if self.pm.read_int(self.LastSelectPVIDMem) == 0:
            self.LastSelectPVIDMem += self.EdenOffsetMem
            self.LastSelectSortMem += self.EdenOffsetMem
            self.LastSelectDiffMem += self.EdenOffsetMem
    
    async def ChangeSong(self,_ID):
        async with changesonglock:
            if IDManager().CheckID(int(_ID)):
                self.pm.write_int(self.ChangeSongSelect, 6)
                self.pm.write_int(self.StartChange, 2)
                await asyncio.sleep(0.032)
                self.pm.write_int(self.LastSelectPVIDMem, int(_ID))
                #跳转难度
                #锁定到难度分类
                self.pm.write_int(self.LastSelectSortMem, 1)
                #锁定到ALL分类
                self.pm.write_int(self.LastSelectDiffMem, 19)
                self.pm.write_int(self.ChangeSongSelect, 5)
                self.pm.write_int(self.StartChange, 2)
                return True
            else:
                print("该ID不存在！")
                return False

async def AddIDList(ID: int):
    global SelectIDList
    if SongIDManager.CheckID(ID):
        SelectIDList.append(ID)
        await WriteSongIDList()
    else:
        print("该ID不存在！")

async def WriteSongIDList():
    global SongIDManager
    global SelectIDList
    async with IDlock:
        try:
            async with aiofiles.open("SongSelect.txt", "w", encoding="UTF-8") as f:
                await f.writelines([SongSelectTitle]+[f"{SongIDManager.ID_dict[SongID]}" for SongID in SelectIDList])
        except Exception as e:
            print(f"文件写入失败: {e}")

async def WriteSearchList(SearchName):
    global SongIDManager
    async with SElock:
        try:
            async with aiofiles.open("SongSearch.txt", "w", encoding="UTF-8") as f:
                await f.writelines([SongSearchTitle] + SongIDManager.SearchName(SearchName))
        except Exception as e:
            print(f"文件写入失败: {e}")

# 传输热键
command_queue = asyncio.Queue()

# 命令行菜单交互
async def command_line_menu():
    global SelectIDList,SongIDManager
    SelectID = -1
    async def usercommand(usercommand:list,SelectID):
        SelectManager = SongSelect()
        match usercommand:
            case ["nx"]:
                if len(SelectIDList) == 0:
                    SelectID = -1
                else:
                    SelectID = SelectIDList[0]
                    SelectIDList.pop(0)
                    await SelectManager.ChangeSong(SelectID)
                    await WriteSongIDList()
            case ["re"]:
                if SelectID != -1:
                    print(f"重新跳转歌曲：{SongIDManager.ID_dict[SelectID]}")
                    await SelectManager.ChangeSong(SelectID)
            case ["skip"]:
                if len(SelectIDList) == 0:
                    SelectID = -1
                elif SelectID == -1:
                    print("当前无正在游玩的歌曲，直接跳至下一首")
                    SelectID = SelectIDList[0]
                    SelectIDList.pop(0)
                else:
                    print(f"跳过当前歌曲 {SongIDManager.ID_dict[SelectID]}")
                    SelectIDList.pop(0)
                    SelectID = SelectIDList[0] if len(SelectIDList) > 0 else -1
                await WriteSongIDList()
            case ["id",SongID] if SongID.isdigit():
                if await SelectManager.ChangeSong(SongID):
                    SelectID = int(SongID)
            case ["se",SongName]:
                print(f"搜索结果：\n{''.join(SongIDManager.SearchName(SongName))}")
            case ["clear"]:
                SelectIDList.clear()
                SelectID = -1
                cleartxt()
                print("已清空所有歌曲列表")
            case [command] if command == "help" or command == "-h":
                print("\n指令列表：\nnx：跳转到下一首歌\nre：重新跳转当前歌曲\nskip：跳过当前选择歌曲\nid：在 id 后面打好空格后输入pvid跳转对应歌曲\nse：按歌名搜索歌曲\nclear：清空所有列表\n")
            case _:
                print("无效输入！")
                
        return SelectID
    
    while True:
        if SelectID == -1:
            print("当前点歌列表为空！")
        else:
            print(f"当前歌曲：{SongIDManager.ID_dict[SelectID]}，如果没有跳转请切换到正确难度后回到主菜单，然后输入 re 重新跳转")
        '''
        #2025.03.24 由于ainput在win平台无法取消，考虑修改成完全使用热键
        input_task = asyncio.create_task(ainput())
        queue_task = asyncio.create_task(command_queue.get())
        # 使用 wait 处理首个完成的任务
        done, pending = await asyncio.wait(
            [input_task, queue_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        # 获取实际输入的命令
        if input_task in done:
            command = await input_task
            command = command.decode()
        else:
            command = await queue_task
            input_task.cancel()  # 取消未完成的输入任务
        '''
        command = await command_queue.get()
        if command == "Console":
            command = await ainput("请输入指令（再次输入指令仍需要按下热键激活）：\n")
        commandlist = command.split(maxsplit=1) if command != "" else ["",""]
        commandlist[0] = commandlist[0].lower()
        SelectID = await usercommand(commandlist,SelectID)

if config["LiveRoomID"] > 0:
    ROOMID:int = config["LiveRoomID"]
else:
    ROOMID:str = input("输入房间号\n")
    if not ROOMID.isdigit():
        print("Error")
        exit()


# 这里填一个已登录账号的cookie的SESSDATA字段的值。不填也可以连接，但是收到弹幕的用户名会打码，UID会变成0
SESSDATA = ''

session: Optional[aiohttp.ClientSession] = None

def init_session():
    cookies = http.cookies.SimpleCookie()
    cookies['SESSDATA'] = SESSDATA
    cookies['SESSDATA']['domain'] = 'bilibili.com'

    global session
    session = aiohttp.ClientSession()
    session.cookie_jar.update_cookies(cookies)

async def run_single_client():
    room_id = int(ROOMID)
    client = blivedm.BLiveClient(room_id, session=session)
    handler = MyHandler()
    client.set_handler(handler)
    client.start()

class MyHandler(blivedm.BaseHandler):

    def _on_danmaku(self, client: blivedm.BLiveClient, message: web_models.DanmakuMessage):
        match message.msg.split(maxsplit=1):
            case [command,ID] if command.lower() == "id" and ID.isdigit():
                print(f"弹幕添加ID {ID}")
                asyncio.create_task(AddIDList(int(ID)))
                cleartxt(False)
            case [command,Name] if command.lower() == "se":
                print(f"弹幕搜索歌名 {Name}")
                asyncio.create_task(WriteSearchList(Name))

SongIDManager = IDManager()
SongIDManager.Read_M39ID()
SongIDManager.GetModList()
cleartxt()

def setup_hotkey(main_loop):
    """接收主事件循环作为参数"""
    def create_handler(cmd):
        def handler():
            # 安全地将协程提交到主事件循环
            asyncio.run_coroutine_threadsafe(
                command_queue.put(cmd),
                main_loop
            )
        return handler

    keyboard.add_hotkey(config["NextSong"], create_handler("nx"))
    keyboard.add_hotkey(config["RetrySong"], create_handler("re"))
    keyboard.add_hotkey(config["SkipSong"], create_handler("skip"))
    keyboard.add_hotkey(config["ClearList"], create_handler("clear"))
    #输入指令热键
    keyboard.add_hotkey(config["Console"], create_handler("Console"))

async def main():
    init_session()
    main_loop = asyncio.get_running_loop()  # 获取当前事件循环
    setup_hotkey(main_loop)  # 传递主事件循环
    await asyncio.gather(
        run_single_client(),
        command_line_menu()
    )
asyncio.run(main())
