import socket
import random
import time

def start_server():
    host = '0.0.0.0'
    port = 9999

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(1)
        print(f"설비 온도 측정 서버가 시작되었습니다. 포트 {port}에서 대기 중...")

        while True:
            client_socket, client_address = server_socket.accept()
            print(f"클라이언트가 연결되었습니다: {client_address}")

            try:
                while True:
                    # 49.0 ~ 51.0 소수점 랜덤 온도 생성
                    temperature = random.uniform(49.0, 51.0)
                    # 소수점 둘째 자리까지 문자열 포맷팅
                    data = f"{temperature:.2f}\n"
                    
                    # 데이터 전송
                    client_socket.sendall(data.encode('utf-8'))
                    print(f"전송 데이터: {data.strip()} 도")
                    
                    # 1초 대기
                    time.sleep(1)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                print(f"클라이언트 {client_address} 와의 연결이 끊어졌습니다.")
            finally:
                client_socket.close()

    except Exception as e:
        print(f"서버 에러 발생: {e}")
    finally:
        server_socket.close()

if __name__ == "__main__":
    start_server()