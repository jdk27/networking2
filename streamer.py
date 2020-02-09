# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY
# threading for part 3: packet loss
from concurrent.futures import ThreadPoolExecutor
from threading import Timer
import threading
import time


class Streamer:
    def __init__(self, dst_ip, dst_port,
                 src_ip=INADDR_ANY, src_port=0):
        """Default values listen on all network interfaces, chooses a random source port,
           and does not introduce any simulated packet loss."""
        self.socket = LossyUDP()
        self.socket.bind((src_ip, src_port))
        self.dst_ip = dst_ip
        self.dst_port = dst_port
        self.expected_num = 0
        self.rec_buf = {}
        self.timer = None
        self.timer_ack = -1
        self.ack_buf = []
        self.listener = True
        self.timeout = .25
        self.unacked = {}
        self.other_fin = False
        self.own_fin = False
        executor = ThreadPoolExecutor(max_workers=3)
        self.listening_future = executor.submit(self.listening)
        self.acking_future = executor.submit(self.acking)

    def listening(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        while self.listener:
            # print('we are listening')
            data, addr = self.socket.recvfrom()
            # print('raw data: ' + str(data))
            if data and data[0] == 65:
                # print('received ack: ' + str(data))
                self.ack_recv(data)
            elif data and data[0] == 70:
                self.other_fin = True
                # print('received fin packet: ' + str(data))
            elif data:
                # print('received application data: ' + str(data))
                seq_num = get_seq_num(data)
                checksum = get_checksum(data)
                if seq_num != -1 and checksum:
                    checksum = checksum.decode('utf-8')
                    calculated_checksum = self.calculate_checksum(
                        get_payload(data))
                    if checksum == calculated_checksum:
                        self.rec_buf[seq_num] = data
                        self.ack_buf.append(data)

    def acking(self):
        while self.listener:
            while self.ack_buf:
                self.ack_send(self.ack_buf[0])
                self.ack_buf.pop(0)

    def send(self, data_bytes: bytes):
        """Note that data_bytes can be larger than one packet."""
        # Your code goes here!  The code below should be changed!
        # length check should be dif bc must make space for header
        seq_num = str(self.expected_num).encode('utf-8')

        if len(data_bytes) + len(seq_num) + 6 + len(b'\r\n\r\n') > 1472:
            payload = data_bytes[:1472-len(seq_num)-6-len(b'\r\n\r\n')]
            checksum = self.calculate_checksum(payload).encode('utf-8')
            header = seq_num+b'C'+checksum+b'\r\n\r\n'
            self.socket.sendto(header+payload, (self.dst_ip, self.dst_port))
            self.expected_num += len(header+payload)
            self.unacked[self.expected_num] = header+payload
            if len(self.unacked) == 1:
                self.timer = Timer(
                    self.timeout, self.retransmission, [header+payload])
                self.timer.start()
                self.timer_ack = self.expected_num
            self.send(data_bytes[1472-len(header):])
        else:
            checksum = self.calculate_checksum(data_bytes).encode('utf-8')
            header = seq_num+b'C'+checksum+b'\r\n\r\n'
            self.socket.sendto(header+data_bytes, (self.dst_ip, self.dst_port))
            self.expected_num += len(header+data_bytes)
            self.unacked[self.expected_num] = header+data_bytes
            if len(self.unacked) == 1:
                self.timer = Timer(
                    self.timeout, self.retransmission, [header+data_bytes])
                self.timer.start()
                self.timer_ack = self.expected_num

    def recv(self) -> bytes:
        # if not expected data, return nothing
        if self.expected_num not in self.rec_buf:
            return b''

        # if expected data, check buffer for contiguous segments and return total contiguous payload
        application_data = self.rec_buf[self.expected_num]
        self.rec_buf.pop(self.expected_num)
        self.expected_num += len(application_data)
        application_data = get_payload(application_data)
        while self.expected_num in self.rec_buf:
            data = self.rec_buf[self.expected_num]
            self.rec_buf.pop(self.expected_num)
            self.expected_num += len(data)
            application_data += get_payload(data)
        return application_data

    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions 
           your code goes here, especially after you add ACKs and retransmissions."""
        while len(self.unacked) != 0:
            time.sleep(5)
            print('Still listening for ACKs: ' + str(self.acking_future.done()))
            print('Still listening for anything: ' + str(self.listening_future.done()))
            pass
        # self.socket.stoprecv()
        print('*****How much we got left ****', threading.active_count())
        self.send_fin()
        self.own_fin = True
        while not self.other_fin:
            time.sleep(5)
            self.send_fin()
            pass
        print('-----There should be nothing-----', threading.active_count())
        while(threading.active_count() > 4):
            time.sleep(5)
            print('waiting here', threading.enumerate())
        self.socket.stoprecv()
        self.listener = False
        pass

    def send_fin(self):
        fin = b'F\r\n\r\n'
        self.socket.sendto(fin, (self.dst_ip, self.dst_port))

    def ack_recv(self, data: bytes):
        ack_num = get_ack_num(data)
        #print('unacked before: ' + str(self.unacked))
        #print('timer before: ' + str(self.timer))
        #print('self.timer_ack before: ' + str(self.timer_ack))
        if ack_num and ack_num in self.unacked:
            self.unacked.pop(ack_num)
        if ack_num and ack_num == self.timer_ack:
            self.timer.cancel()
            if self.unacked:
                new_timer_ack = sorted(self.unacked.keys())[0]
                self.timer_ack = new_timer_ack
                self.timer = Timer(
                    self.timeout, self.retransmission, [self.unacked[new_timer_ack]])
                self.timer.start()
            else:
                self.timer = None
                self.timer_ack = -1
        #print('timer after: ' + str(self.timer))
        #print('self.timer_ack before: ' + str(self.timer_ack))
        # print('unacked after: ' + str(len(self.unacked)) + '\n')

    def ack_send(self, data: bytes):
        ack_num = str(get_seq_num(data)+len(data))
        header = b'A'+ack_num.encode('utf-8')+b'\r\n\r\n'
        self.socket.sendto(header, (self.dst_ip, self.dst_port))

    def retransmission(self, data: bytes):
        # self.socket.sendto(data, (self.dst_ip, self.dst_port))
        # self.timer = Timer(self.timeout, self.retransmission, [data])
        # self.timer.start()
        if not (self.other_fin and self.own_fin):
            self.socket.sendto(data, (self.dst_ip, self.dst_port))
            self.timer = Timer(self.timeout, self.retransmission, [data])
            self.timer.start()

    def calculate_checksum(self, msg) -> str:
        try:
            msg = msg.decode('utf-8')
            s = 0       # Binary Sum
            # loop taking 2 characters at a time
            for i in range(0, len(msg), 2):
                if (i+1) < len(msg):
                    a = ord(msg[i])
                    b = ord(msg[i+1])
                    s = s + (a+(b << 8))
                elif (i+1) == len(msg):
                    s += ord(msg[i])
                else:
                    raise "Something Wrong here"
            # One's Complement
            s = s + (s >> 16)
            s = ~s & 0xffff
            return str(s)
        except:
            return ''


def get_seq_num(data: bytes) -> int:
    try:
        num = data.decode('utf-8')
        num = int(num[:num.find('C')])
        return num
    except:
        return -1


def get_ack_num(data: bytes) -> int:
    try:
        num = data.decode('utf-8')
        num = int(num[1:num.find('\r\n\r\n')])
        return num
    except:
        return 0


def get_payload(data: bytes) -> bytes:
    try:
        data = data.decode('utf-8')
        return data[data.find('\r\n\r\n')+len('\r\n\r\n'):].encode('utf-8')
    except:
        return 0


def get_checksum(data: bytes) -> str:
    try:
        data = data.decode('utf-8')
        data = data[data.find('C')+1:data.find('\r\n\r\n')].encode('utf-8')
        return data
    except:
        return ''
