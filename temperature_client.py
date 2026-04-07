import sys
import socket
import collections
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import QThread, Signal, Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# 1. 서버로부터 데이터를 비동기로 계속 수신받기 위한 스레드 클래스
class DataReceiverThread(QThread):
    # 온도를 나타내는 float 값을 GUI 스레드로 전달하기 위한 시그널
    temperature_received = Signal(float)
    # 현재 연결 상태를 전달하기 위한 시그널
    connection_status = Signal(str)

    def __init__(self, host='127.0.0.1', port=9999):
        super().__init__()
        self.host = host
        self.port = port
        self.running = True

    def run(self):
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connection_status.emit(f"{self.host}:{self.port} 서버에 연결 중...")
            
            # 서버 접속 시도
            client_socket.connect((self.host, self.port))
            self.connection_status.emit("✅ 서버에 성공적으로 연결됨!")

            buffer = ""
            while self.running:
                data = client_socket.recv(1024)
                if not data:
                    self.connection_status.emit("🚨 서버와 연결이 끊어졌습니다.")
                    break
                
                # 수신받은 바이트 데이터를 문자열로 변환 후 버퍼에 추가
                buffer += data.decode('utf-8')
                
                # 줄바꿈(\n) 단위로 잘라서 데이터 해석
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            # 문자열로 온 온도 데이터를 실수로 파싱 후 시그널 전파
                            temp_value = float(line.strip())
                            self.temperature_received.emit(temp_value)
                        except ValueError:
                            pass
        except Exception as e:
            self.connection_status.emit(f"🚨 연결 오류: {str(e)}")
        finally:
            client_socket.close()

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

# 2. 실시간 그래프와 UI를 구성하는 메인 위젯
class RealTimePlotWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("실시간 공장 설비 온도 모니터링 클라이언트")
        self.resize(800, 600)

        # 데이터 저장소 (최대 60개의 데이터 포인트 저장 = 약 60초간의 기록)
        self.max_points = 60
        self.x_data = collections.deque(maxlen=self.max_points)
        self.y_data = collections.deque(maxlen=self.max_points)
        self.time_counter = 0

        # ---- UI 레이아웃 설정 ----
        layout = QVBoxLayout()
        
        # 상태 표시 라벨 설정
        self.status_label = QLabel("상태: 대기 중")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333; padding: 5px;")
        layout.addWidget(self.status_label)

        # 현재 온도 표시 라벨 설정
        self.temp_label = QLabel("현재 온도: -- ℃")
        self.temp_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #d32f2f; padding: 5px;")
        layout.addWidget(self.temp_label)

        # Matplotlib Figure 및 Canvas 설정
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        self.setLayout(layout)

        # ---- 그래프(Axes) 설정 ----
        self.ax = self.figure.add_subplot(111)
        # 초기 데이터를 빈 리스트로 두고 o 마커와 선으로 렌더링 설정
        self.line, = self.ax.plot([], [], 'b-o', linewidth=2, markersize=5)
        # 온도 값이 49.0 ~ 51.0 이므로 살짝 넓게 y축 고정 (48.0 ~ 52.0)
        self.ax.set_ylim(48.0, 52.0) 
        self.ax.set_xlim(0, self.max_points)
        self.ax.set_title("Real-time Temperature Chart")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Temperature (℃)")
        self.ax.grid(True, linestyle='--', alpha=0.6)

        # ---- 수신 스레드 시작 ----
        self.receiver_thread = DataReceiverThread()
        # 스레드에서 시그널이 오면 update_plot, update_status 함수 실행
        self.receiver_thread.temperature_received.connect(self.update_plot)
        self.receiver_thread.connection_status.connect(self.update_status)
        self.receiver_thread.start()

    # 연결 상태를 화면 상단에 업데이트
    def update_status(self, message):
        self.status_label.setText(f"상태: {message}")

    # 새 데이터가 오면 그래프 갱신
    def update_plot(self, temp):
        # 텍스트 라벨 갱신
        self.temp_label.setText(f"현재 온도: {temp:.2f} ℃")
        
        # X축 시간/데이터 리스트 추가
        self.time_counter += 1
        self.x_data.append(self.time_counter)
        self.y_data.append(temp)
        
        # 선(line) 객체에 최신 데이터 셋업
        self.line.set_xdata(self.x_data)
        self.line.set_ydata(self.y_data)
        
        # 데이터가 max_points(60개)를 넘어가면 그래프가 왼쪽으로 스크롤되도록 x축 리미트 변경
        if self.time_counter > self.max_points:
            self.ax.set_xlim(self.time_counter - self.max_points + 1, self.time_counter + 1)
        else:
            self.ax.set_xlim(0, self.max_points)
            
        # 캔버스 다시 그리기 (화면 갱신)
        self.canvas.draw()

    # 창을 닫을 때 스레드 안전하게 종료
    def closeEvent(self, event):
        if hasattr(self, 'receiver_thread'):
            self.receiver_thread.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RealTimePlotWidget()
    window.show()
    sys.exit(app.exec())
