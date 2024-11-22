from machine import Pin, I2C, SoftI2C
from OLED_1inch5 import OLED_1inch5
from SHTC3 import SHTC3
from VOC_SGP40 import SGP40
from VOC_Algorithm import VOC_Algorithm
from time import sleep, ticks_ms

# Налаштування адрес та інтерфейсу I2C
OLED_ADDR = 0x3d
SHTC3_ADDR = 0x70
VOC_ADDR = 0x59
OLED_i2c = SoftI2C(sda=Pin(6), scl=Pin(7), freq=1_000_000)
Sensors_i2c = I2C(id=0, sda=Pin(8), scl=Pin(9), freq=100_000)

# Ініціалізація дисплея, датчиків та алгоритму VOC
OLED = OLED_1inch5(OLED_ADDR, OLED_i2c)
sthc3 = SHTC3(Sensors_i2c, SHTC3_ADDR)
sthc3.wakeup()
sgp = SGP40(Sensors_i2c, VOC_ADDR)
VOC = VOC_Algorithm()

# Налаштування кнопки для ввімкнення/вимкнення дисплея
button = Pin(3, Pin.IN, Pin.PULL_UP)
display_on = True
last_button_press_time = ticks_ms()  # Для дебаунсингу кнопки

# Створення змінних для графіків
show_temperature_graph = False
show_humidity_graph = False
show_air_quality_graph = False

# Буфери для зберігання графіків температури та вологості
temperature_history = []
humidity_history = []

# Функція для перемикання графіків
def toggle_display(pin):
    global display_on, last_button_press_time, show_temperature_graph, show_humidity_graph, show_air_quality_graph
    # Дебаунсинг кнопки: чекаємо, поки кнопка не буде натиснута 500 мс
    if ticks_ms() - last_button_press_time > 500:
        if not display_on:  # Якщо дисплей вимкнений, не змінюємо графіки
            return
        # Перемикаємо графіки
        if show_temperature_graph:
            show_temperature_graph = False
            show_humidity_graph = True
        elif show_humidity_graph:
            show_humidity_graph = False
            show_air_quality_graph = True
        elif show_air_quality_graph:
            show_air_quality_graph = False
        else:
            show_temperature_graph = True
        last_button_press_time = ticks_ms()

button.irq(trigger=Pin.IRQ_FALLING, handler=toggle_display)

# Функція для малювання графіка температури
def draw_temperature_graph():
    OLED.fill(0)  # Очищуємо екран
    OLED.text("Temperature", 1, 0, 1)
    # Малюємо графік температури з буфера
    for i in range(1, len(temperature_history)):
        x1 = (i - 1) * 10 + 20
        y1 = 63 - int(temperature_history[i - 1] * 2)  # Масштабуємо значення температури
        x2 = i * 10 + 20
        y2 = 63 - int(temperature_history[i] * 2)
        OLED.line(x1, y1, x2, y2, 1)
    OLED.text("{:.1f} C".format(temperature_history[-1]), 1, 55, 1)
    OLED.show()

# Функція для малювання графіка вологості
def draw_humidity_graph():
    OLED.fill(0)  # Очищуємо екран
    OLED.text("Humidity", 1, 0, 1)
    # Малюємо графік вологості з буфера
    for i in range(1, len(humidity_history)):
        x1 = (i - 1) * 10 + 20
        y1 = 63 - int(humidity_history[i - 1] * 0.63)  # Масштабуємо значення вологості
        x2 = i * 10 + 20
        y2 = 63 - int(humidity_history[i] * 0.63)
        OLED.line(x1, y1, x2, y2, 1)
    OLED.text("{:.1f} %".format(humidity_history[-1]), 1, 55, 1)
    OLED.show()

# Функція для малювання графіка якості повітря
def draw_air_quality_graph(voc_index):
    OLED.fill(0)  # Очищуємо екран
    OLED.text("Air Quality", 1, 0, 1)
    # Малюємо графік якості повітря
    air_quality_height = int(voc_index / 10)  # Масштабуємо індекс VOC
    if air_quality_height > 63:  # Якщо значення занадто велике
        air_quality_height = 63
    OLED.fill_rect(20, 10, 10, air_quality_height, 1)  # Малюємо стовпець для якості повітря
    OLED.text("VOC Index: {}".format(voc_index), 1, 55, 1)
    OLED.show()

# Основний цикл програми
while True:
    if display_on:
        # Зчитування температури та вологості
        temp, humidity = sthc3.measurement(0, 0, 0)
        
        # Оновлення буферів для графіків
        temperature_history.append(temp)
        humidity_history.append(humidity)
        
        # Обмежуємо кількість точок на графіку до 10
        if len(temperature_history) > 10:
            temperature_history.pop(0)
        if len(humidity_history) > 10:
            humidity_history.pop(0)
        
        # Отримання значення газу, скоригованого за температурою та вологістю
        raw = sgp.measureRaw(temp, humidity)
        
        # Обчислення індексу VOC
        voc_index = VOC.VocAlgorithm_process(raw)
        
        # Виведення графіків, якщо вони увімкнені
        if show_temperature_graph:
            draw_temperature_graph()
        elif show_humidity_graph:
            draw_humidity_graph()
        elif show_air_quality_graph:
            draw_air_quality_graph(voc_index)
        else:
            # Якщо жоден графік не вибрано, відображаємо основні дані
            OLED.fill(0)
            OLED.text("Temp: {:.1f}C".format(temp), 1, 0, 1)
            OLED.text("Humidity: {:.1f}%".format(humidity), 1, 10, 1)
            OLED.text("VOC Index: {}".format(voc_index), 1, 20, 1)
            OLED.show()
        
        sleep(0.5)
    else:
        OLED.fill(0)  # Очистити дисплей при вимкненому режимі
        OLED.show()
        sleep(0.5)
