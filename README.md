# DivaDanmuSelecter
基于Pymem和blivedm库实现的歌姬计划MEGA39+弹幕点歌姬

## 已知缺陷
没有设定定位到指定难度，这会导致如果玩家选择EXEX难度时跳向没有exex难度的歌会自动返回到第一首  
歌曲列表使用的是读取pvdb的方式，如果玩家使用了什么奇怪的mod删除了原版歌曲可能会跳转到并不存在的歌而崩游戏

## 原理
M39+游戏有一个地址会保存最后一次退出时选择的歌曲ID，本程序利用了这一点修改地址切换状态到PV鉴赏模式后更改ID值后再切回选歌界面从而实现了游戏内切歌  
我不会写代码，只会简单的调包，所以这个项目的代码看着会很混乱，我也暂时不打算优化了  

## 搜索功能能不能单独提取出来
能，但是Brogamer已经在开发集成在游戏内GUI搜索的插件了，我觉得我没必要再做一个  
可以等等Brogamer做完他的MOD  

## 特别感谢
nas,samyuu - M39+ DEBUG MOD  
srounet - pymem  
xfgryujk - blivedm  
boppreh  - keyboard  
