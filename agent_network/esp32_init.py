import network
from socket import *


def init(ssid, password):
    wlan = network.WLAN(network.STA_IF)  # create station interface
    wlan.active(True)  # activate the interface
    wlan.scan()  # scan for access points
    wlan.isconnected()  # check if the station is connected to an AP
    wlan.connect(ssid, password)  # connect to an AP
    wlan.config('mac')  # get the interface's MAC address
    wlan.ifconfig()  # get the interface's IP/netmask/gw/DNS addresses
    print("wifi connect success")

    # 1. 创建udp套接字
    # udp_socket = socket(AF_INET, SOCK_DGRAM)
    #
    # # 2. 准备接收方的地址
    # dest_addr = ('192.168.31.137', 8080)
    #
    # # 3. 从键盘获取数据
    # send_data = "hello world"
    #
    # # 4. 发送数据到指定的电脑上
    # udp_socket.sendto(send_data.encode('utf-8'), dest_addr)
    #
    # # 5. 关闭套接字
    # udp_socket.close()


# init("Xiaomi_LB", "libing2015")
