# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY
# threading for part 3: packet loss
from concurrent.futures import ThreadPoolExecutor
from threading import Timer


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
        self.timer_buf = {}
        self.listener = True
        print('Before listener thread')
        executor = ThreadPoolExecutor(max_workers=2)
        executor.submit(self.listening)
        print('Listener in thread')

    def send(self, data_bytes: bytes):
        """Note that data_bytes can be larger than one packet."""
        # Your code goes here!  The code below should be changed!
        # length check should be dif bc must make space for header
        print('sequence number: ' + str(self.expected_num))
        header = str(self.expected_num).encode('utf-8')+b'\r\n\r\n'
        if len(data_bytes) + len(header) > 1472:
            payload = data_bytes[:1472-len(header)]
            self.socket.sendto(header+payload, (self.dst_ip, self.dst_port))
            self.expected_num += 1472
            timer = Timer(.25, self.retransmission, [header+payload])
            self.timer_buf[self.expected_num] = timer
            # timer.start()
            self.send(data_bytes[1472-len(header):])
        else:
            self.socket.sendto(header+data_bytes, (self.dst_ip, self.dst_port))
            self.expected_num += len(header)+len(data_bytes)
            timer = Timer(.25, self.retransmission, [header+data_bytes])
            self.timer_buf[self.expected_num] = timer
            # timer.start()

    def listening(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        #data, addr = self.socket.recvfrom()
        #seq_num = get_seq_num(data)
        #self.rec_buf[seq_num] = data
        # self.ack_send(data)
        while self.listener:
            data, addr = self.socket.recvfrom()
            print('raw data: ' + str(data))
            if data and data[0] == 65:
                self.ack_recv(data)
            elif data:
                seq_num = get_seq_num(data)
                self.rec_buf[seq_num] = data
                self.ack_send(data)

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
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        self.listener = False

    def ack_recv(self, data: bytes):
        print('ACK received')
        ack_num = get_ack_num(data)
        # self.timer_buf[ack_num].cancel()
        self.timer_buf.pop(ack_num)

    def ack_send(self, data: bytes):
        ack_num = str(get_seq_num(data)+len(data))
        header = b'A'+ack_num.encode('utf-8')+b'\r\n\r\n'
        self.socket.sendto(header, (self.dst_ip, self.dst_port))
        print('ACK ' + ack_num + ' sent')

    def retransmission(self, data: bytes):
        self.socket.sendto(data, (self.dst_ip, self.dst_port))
        timer = Timer(.25, self.retransmission, [data])
        self.timer_buf[get_seq_num(data)+len(data)] = timer
        timer.start()


def get_seq_num(data: bytes) -> int:
    num = data.decode('utf-8')
    return int(num[:num.find('\r\n\r\n')])


def get_ack_num(data: bytes) -> int:
    num = data.decode('utf-8')
    return int(num[1:num.find('\r\n\r\n')])


def get_payload(data: bytes) -> bytes:
    data = data.decode('utf-8')
    return data[data.find('\r\n\r\n')+len('\r\n\r\n'):].encode('utf-8')
