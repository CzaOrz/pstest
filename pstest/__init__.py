# coding: utf-8
import re
import time
import socket
import loggus

from typing import Tuple

"""
> GET / HTTP/1.1
> Host: www.baidu.com
> User-Agent: curl/7.55.1
> Accept: */*
"""

regex = re.compile("(?:(https?)://)?([^/]*)(.*)")
size = 1024 * 1024


def parseUrl(url: str) -> Tuple[str, str, int, str]:
    parser = regex.search(url)
    if not parser:
        raise Exception(f"Parser {url} Failure!")
    protocol, host, path = parser.groups()
    port = 443 if protocol == "https" else 80
    if not host:
        raise Exception(f"Parser {url} Failure, Empty Host!")
    if ":" in host:
        host, port = host.split(":", 1)
    port = int(port)
    hostIP = socket.gethostbyname(host)
    path = path or "/"
    return host, hostIP, port, path


def request(address: Tuple[str, int], requestMsg: bytes, timeout: int = None) -> Tuple[int, bytes, float, float, float]:
    # sock = socket.create_connection(address, timeout)
    sock = socket.socket()
    sock.settimeout(timeout) if timeout else None

    start = time.monotonic()
    sock.connect(address)

    connCreateTime = time.monotonic() - start

    start = time.monotonic()
    sock.send(requestMsg)
    sendMsgTime = time.monotonic() - start

    start = time.monotonic()
    response = sock.recv(size)
    recvMsgTime = time.monotonic() - start
    sock.close()
    del sock

    statusIndex = response.find(b" ") + 1
    status = int(response[statusIndex:statusIndex + 3])

    bodyIndex = response.find(b"\r\n\r\n") + 4
    body = response[bodyIndex:]

    return status, body, connCreateTime, sendMsgTime, recvMsgTime


def parseRequestInfo(method: str, url: str, headers: dict = None, body: str = None) -> Tuple[str, int, bytes]:
    method = method.upper()
    host, hostIP, port, path = parseUrl(url)
    requestMsg = f"{method} {path} HTTP/1.1\r\n"
    headersBases = {
        "Host": host,
        "User-Agent": "PyStressTest/0.0.1",
        "Accept": "*/*",
        "Content-Length": 0,
    }
    headersBases.update(headers or {})
    body = (body or "").encode("utf-8")
    headersBases.update({"Content-Length": len(body)})
    for key, value in headersBases.items():
        requestMsg += f"{key}: {value}\r\n"
    requestMsg += "\r\n"
    requestMsg = requestMsg.encode("utf-8") + body

    return hostIP, port, requestMsg


# def test():
#     import json
#     method = "POST"
#     url = "http://fxcse.avlyun.com/v2/search/pro"
#     headers = {"Content-Type": "application/json"}
#     body = json.dumps(
#         {"appId": "26de60ca3b194f71f550815882105423", "timeStamp": 1596437077, "apiVersion": "2.0", "uuid": "",
#          "scanScene": "0", "secret": "5600ce7a0c2aa9df1c2d19f1f72e41ba", "searchInfo": [
#             {"apkMd5": "FFE9548E5725EFD13AB5E50E2E68E78F", "packageName": "xpt.com.qmkd", "programName": "全民看点",
#              "keyHash": "004410b3c22a9dc4", "mfMd5": "EA007289208D93B465C55F66710D84FE", "index": "1"}]})
#     hostIP, port, requestMsg = parseRequestInfo(method, url, headers, body)
#     for _ in range(5):
#         print(request((hostIP, port), requestMsg))
count = 0
connCreateTimeMax = 0
sendMsgTimeMax = 0
recvMsgTimeMax = 0


def ttt():
    import json
    import threading
    hostIP, port, requestMsg = parseRequestInfo("POST", "http://10.251.63.35:8400/callback",
                                                {"Content-Type": "application/json"}, json.dumps({"name": "cc"}))

    # print(request((hostIP, port), requestMsg))

    def tttt():
        global count, connCreateTimeMax, sendMsgTimeMax, recvMsgTimeMax
        while True:
            # import requests
            # print(requests.post("http://10.251.63.35:8400/callback", json={"name": "cc"}).content)
            status, body, connCreateTime, sendMsgTime, recvMsgTime = request((hostIP, port), requestMsg, 4)
            count += 1
            connCreateTimeMax = max(connCreateTimeMax, connCreateTime)
            sendMsgTimeMax = max(sendMsgTimeMax, sendMsgTime)
            recvMsgTimeMax = max(recvMsgTimeMax, recvMsgTime)
            loggus.WithFields({
                "status": status,
                "connCreateTime": connCreateTimeMax,
                "sendMsgTime": sendMsgTimeMax,
                "recvMsgTime": recvMsgTimeMax,
            }).info("ok")

    num = 200
    ts = [threading.Thread(target=tttt) for _ in range(num)]
    [t.start() for t in ts]
    [t.join() for t in ts]


if __name__ == '__main__':
    ttt()
    # import json
    # hostIP, port, requestMsg = parseRequestInfo("POST", "http://10.251.63.35:8400/callback",
    #                                             {"Content-Type": "application/json"}, json.dumps({"name": "cc"}))
    # while True:
    #     # import requests
    #     # print(requests.post("http://10.251.63.35:8400/callback", json={"name": "cc"}).content)
    #     status, body, connCreateTime, sendMsgTime, recvMsgTime = request((hostIP, port), requestMsg, 4)
    #     count += 1
    #     connCreateTimeMax = max(connCreateTimeMax, connCreateTime)
    #     sendMsgTimeMax = max(sendMsgTimeMax, sendMsgTime)
    #     recvMsgTimeMax = max(recvMsgTimeMax, recvMsgTime)
    #     loggus.WithFields({
    #         "status": status,
    #         "connCreateTime": connCreateTimeMax,
    #         "sendMsgTime": sendMsgTimeMax,
    #         "recvMsgTime": recvMsgTimeMax,
    #     }).info("ok")

# if __name__ == '__main__':
#     print(socket.gethostbyname("www.baidu.com"))
#     print(socket.gethostbyname_ex("www.baidu.com"))
#     print(socket.gethostbyname("fxcse.avlyun.com"))
#     print(socket.gethostbyname_ex("fxcse.avlyun.com"))
#     print(socket.gethostbyname("14.215.177.38"))
#     print(socket.gethostbyname_ex("14.215.177.38"))
#
#     for url in ["www.baidu.com", "http://www.baidu.com/", "https://www.baidu.com/callback?args=1",
#                 "http://localhost:8080/callback"]:
#         # print(regex.search(url).groups(), parseUrl(url))
#         parseRequestInfo("GET", url)
#
#     test()
