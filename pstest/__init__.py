# coding: utf-8
import re
import time
import socket
import loggus
import argparse

from typing import Tuple

from threading import RLock

__author__ = "https://github.com/CzaOrz"
__version__ = "0.0.1"

regex = re.compile("(?:(https?)://)?([^/]*)(.*)")
size = 1024 * 1024


class Collector:
    samples = 0  # total samples.
    errSamples = 0  # total error samples.
    connCreateTimeMin = 0
    sendMsgTimeMin = 0
    resMsgTimeMin = 0
    connCreateTimeAvg = 0
    sendMsgTimeAvg = 0
    resMsgTimeAvg = 0
    connCreateTimeMax = 0
    sendMsgTimeMax = 0
    resMsgTimeMax = 0
    connCreateTimeTotal = 0
    sendMsgTimeTotal = 0
    resMsgTimeTotal = 0
    lock = RLock()

    def record(self, connCreateTime: float, sendMsgTime: float, resMsgTime: float) -> None:
        with self.lock:
            self.samples += 1
            self.connCreateTimeTotal += connCreateTime
            self.sendMsgTimeTotal += sendMsgTime
            self.resMsgTimeTotal += resMsgTime
            self.connCreateTimeMin = min(connCreateTime, self.connCreateTimeMin)
            self.sendMsgTimeMin = min(sendMsgTime, self.sendMsgTimeMin)
            self.resMsgTimeMin = min(resMsgTime, self.resMsgTimeMin)
            self.connCreateTimeAvg = self.connCreateTimeTotal / self.samples
            self.sendMsgTimeAvg = self.sendMsgTimeAvg / self.samples
            self.resMsgTimeAvg = self.resMsgTimeAvg / self.samples
            self.connCreateTimeMax = max(connCreateTime, self.connCreateTimeMax)
            self.sendMsgTimeMax = max(sendMsgTime, self.sendMsgTimeMax)
            self.resMsgTimeMax = max(resMsgTime, self.resMsgTimeMax)

    def recordWithErr(self, connCreateTime: float, sendMsgTime: float, resMsgTime: float) -> None:
        with self.lock:
            self.errSamples += 1
            self.record(connCreateTime, sendMsgTime, resMsgTime)


collector = Collector()


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


def parseResponse(response: bytes) -> Tuple[int, dict, bytes]:
    statusIndex = response.find(b" ") + 1
    statusIndexEnd = statusIndex + 3
    status = int(response[statusIndex:statusIndexEnd])

    headersIndex = response.find(b"\r\n", statusIndexEnd) + 2
    headersEnd = response.find(b"\r\n\r\n", headersIndex)
    bodyIndex = headersEnd + 4
    headersBytes = response[headersIndex:headersEnd]
    body = response[bodyIndex:]

    headers = {}
    for header in headersBytes.decode("utf-8").split("\r\n"):
        kv = header.split(":")
        if len(kv) == 2:
            headers[kv[0].strip()] = kv[1].strip()
    return status, headers, body


def parseRequestInfo(method: str, url: str, headers: dict = None, body: str = None) -> Tuple[str, int, bytes]:
    method = method.upper()
    host, hostIP, port, path = parseUrl(url)
    requestMsg = f"{method} {path} HTTP/1.1\r\n"
    headersBases = {
        "Host": host,
        "User-Agent": f"PyStressTest/{__version__}",
        "Accept": "*/*",
    }
    if body:
        body = body.encode("utf-8")
        headersBases["Content-Length"] = len(body)
        headersBases["Content-Type"] = "application/x-www-form-urlencoded"
    if headers:
        headersBases.update(headers)
    for key, value in headersBases.items():
        requestMsg += f"{key}: {value}\r\n"
    else:
        requestMsg += "\r\n"
    requestMsg = requestMsg.encode("utf-8")
    if body:
        requestMsg = requestMsg + body

    return hostIP, port, requestMsg


def request(address: Tuple[str, int], requestMsg: bytes, timeout: int = None) -> Tuple[bytes, float, float, float]:
    sock = socket.socket()
    sock.settimeout(timeout) if timeout else None

    start = time.monotonic()
    sock.connect(address)
    connCreateTime = time.monotonic() - start

    start = time.monotonic()
    sock.send(requestMsg)
    sendMsgTime = time.monotonic() - start

    start = time.monotonic()
    response = b""
    # print(sock.recv(0))
    # respo = []
    # import io
    # respo = bytearray(1024)
    # print(sock.recv_into(respo, 1024))
    # print(respo)
    # response = respo
    response = sock.recv(size)
    # sock.setblocking(False)
    # while chunk:
    #     print(chunk)
    #     response += chunk
    #     chunk = sock.recv(size)
    recvMsgTime = time.monotonic() - start

    sock.close()
    return response, connCreateTime, sendMsgTime, recvMsgTime


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


def test():
    hostIP, port, requestMsg = parseRequestInfo("POST", "www.baidu.com",
                                                {"Content-Type": "application/json"})
    status, body, connCreateTime, sendMsgTime, recvMsgTime = request((hostIP, port), requestMsg, 4)
    print(status, body, connCreateTime, sendMsgTime, recvMsgTime)


def execute(args: list = None) -> None:
    parser = argparse.ArgumentParser(
        prog="PyStressTest",
        description="a easy stress test tools.",
    )

    parser.add_argument("-X", help="request method. default is `GET`, if request with data, default `POST`.")
    parser.add_argument("-H", action='append', help="header to server, format like <key:value>", default=[])
    parser.add_argument("-d", action='append', help="http body data.", default=[])
    parser.add_argument("-v", action='store_true', help="make the operation more talkative.")
    parser.add_argument("--stress", action='store_true', help="open stress test.")
    parser.add_argument("--timeout", help="connect timeout.", type=int, default=8)
    parser.add_argument("uri", help="the resource identifier.")

    args = parser.parse_args(args)

    method = args.X.upper() if args.X else "GET"
    headers = {}
    for header in args.H:
        kv = header.split(":", 1)
        if len(kv) == 2:
            headers[kv[0].strip()] = kv[1].strip()
    body = "".join(args.d)
    timeout = args.timeout

    try:
        hostIP, port, requestMsg = parseRequestInfo(method, args.uri, headers, body)
    except Exception as e:
        loggus.WithTraceback().panic(e)
        return

    try:
        response, connCreateTime, sendMsgTime, recvMsgTime = request((hostIP, port), requestMsg, timeout)
        status, headers, body = parseResponse(response)
    except Exception as e:
        loggus.WithTraceback().panic(e)
        return

    loggus.WithFields(headers).info("ResponseHeaders")
    if status < 300:
        loggus.WithField("ResponseBody", body.decode("utf-8"), loggus.INFO_COLOR).info(status)
    elif status < 400:
        loggus.WithField("ResponseBody", body.decode("utf-8"), loggus.WARNING_COLOR).warning(status)
    else:
        loggus.WithField("ResponseBody", body.decode("utf-8"), loggus.ERROR_COLOR).error(status)
    loggus.WithFields({
        "connCreateTime": connCreateTime,
        "sendMsgTime": sendMsgTime,
        "recvMsgTime": recvMsgTime,
    }).info("PerformanceShow")


if __name__ == '__main__':
    execute(["http://fanyi.youdao.com/"])
