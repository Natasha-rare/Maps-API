import pygame
import requests
import sys
import os

import math


# Подобранные констатны для поведения карты.
LAT_STEP = 0.008  # Шаги при движении карты по широте и долготе
LON_STEP = 0.02
coord_to_geo_x = 0.0000428  # Пропорции пиксельных и географических координат.
coord_to_geo_y = 0.0000428
move = 0.01
map_view = ['map', 'sat', 'sat,skl']


# Параметры отображения карты:
# координаты, масштаб, найденные объекты и т.д.

class MapParams(object):
    # Параметры по умолчанию.
    def __init__(self):
        self.lat = 55.729738  # Координаты центра карты на старте.
        self.lon = 37.664777
        self.zoom = 15  # Масштаб карты на старте.
        self.type = map_view[0]  # Тип карты на старте.
        self.point = ''

    # Преобразование координат в параметр ll
    def ll(self):
        return "{0},{1}".format(self.lon, self.lat)

    # Обновление параметров карты по нажатой клавише.
    def update(self, event):
        if event.key == pygame.K_PAGEUP:  # + масштаб
            if self.zoom < 17:
                self.zoom += 1
        elif event.key == pygame.K_PAGEDOWN:  # - масштаб
            if self.zoom > 0:
                self.zoom -= 1
        # Двигаем карту
        elif event.key == pygame.K_UP:
            self.lat += move
        elif event.key == pygame.K_DOWN:
            self.lat -= move
        elif event.key == pygame.K_RIGHT:
            self.lon += move
        elif event.key == pygame.K_LEFT:
            self.lon -= move
        elif event.key == pygame.K_F1:
            if self.type == map_view[-1]:
                self.type = map_view[0]
            else:
                self.type = map_view[map_view.index(self.type) + 1]

    # Преобразование экранных координат в географические.
    def screen_to_geo(self, pos):
        dy = 225 - pos[1]
        dx = pos[0] - 300
        lx = self.lon + dx * coord_to_geo_x * math.pow(2, 15 - self.zoom)
        ly = self.lat + dy * coord_to_geo_y * math.cos(math.radians(self.lat)) * math.pow(2, 15 - self.zoom)
        return lx, ly


# Создание карты с соответствующими параметрами.
def load_map(mp):
    if mp.point != '':
        map_request = f"http://static-maps.yandex.ru/1.x/?ll={mp.ll()}&z={mp.zoom}&l={mp.type}&pt={mp.ll()},{mp.point}"
    else:
        map_request = f"http://static-maps.yandex.ru/1.x/?ll={mp.ll()}&z={mp.zoom}&l={mp.type}"
    response = requests.get(map_request)
    if not response:
        print("Ошибка выполнения запроса:")
        print(map_request)
        print("Http статус:", response.status_code, "(", response.reason, ")")
        sys.exit(1)

    # Запишем полученное изображение в файл.
    map_file = "map.png"
    try:
        with open(map_file, "wb") as file:
            file.write(response.content)
    except IOError as ex:
        print("Ошибка записи временного файла:", ex)
        sys.exit(2)
    return map_file


# Создание холста с текстом.
def render_text(text):
    font = pygame.font.Font(None, 30)
    return font.render(text, 1, (100, 0, 100))


clock = pygame.time.Clock()


def start_find(address):
    global mp
    geocoder_api_server = "http://geocode-maps.yandex.ru/1.x/"

    geocoder_params = {
        "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
        "geocode": address,
        "format": "json"}

    response = requests.get(geocoder_api_server, params=geocoder_params)
    if response:
        # Преобразуем ответ в json-объект
        json_response = response.json()
        # Получаем первый топоним из ответа геокодера.
        toponym = json_response["response"]["GeoObjectCollection"][
            "featureMember"][0]["GeoObject"]
        toponym_coodrinates = toponym["Point"]["pos"]
        # Долгота и Широта :
        mp.lon, mp.lat = [float(x) for x in toponym_coodrinates.split(" ")]
        mp.point = 'pm2rdm'


def main():
    global mp
    text = ''
    # Инициализируем pygame
    pygame.init()
    running = True
    screen = pygame.display.set_mode((600, 500))

    # Заводим объект, в котором будем хранить все параметры отрисовки карты.
    mp = MapParams()
    while running:
        font = pygame.font.Font(None, 40)
        input_box = pygame.Rect(170, 10, 140, 32)
        color = pygame.Color('blue')
        for event in pygame.event.get():
            if event.type == pygame.QUIT:  # Выход из программы
                running = False
            if event.type == pygame.KEYUP:  # Обрабатываем различные нажатые клавиши.
                mp.update(event)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    start_find(text)
                    text = ''
                elif event.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                elif event.key not in [pygame.K_LEFT,
                                       pygame.K_RIGHT, pygame.K_DOWN,
                                       pygame.K_UP, pygame.K_PAGEDOWN,
                                       pygame.K_PAGEUP]:
                    text += event.unicode

        screen.fill((0, 0, 0))
        font = pygame.font.Font(None, 30)
        t = font.render('Введите адрес', 1, (255, 255, 100))
        screen.blit(t, (10, 10))

        # Render the current text.
        txt_surface = font.render(text, True, color)
        # Resize the box if the text is too long.
        width = max(200, txt_surface.get_width() + 10)
        input_box.w = width
        # Blit the text.
        screen.blit(txt_surface, (input_box.x + 5, input_box.y + 3))
        # Blit the input_box rect.
        pygame.draw.rect(screen, color, input_box, 2)
        # Загружаем карту, используя текущие параметры.
        map_file = load_map(mp)
        # Рисуем картинку, загружаемую из только что созданного файла.
        screen.blit(pygame.image.load(map_file), (0, 50))
        # Переключаем экран и ждем закрытия окна.
        pygame.display.flip()
        clock.tick(100)
    pygame.quit()
    # Удаляем за собой файл с изображением.
    os.remove(map_file)


if __name__ == "__main__":
    main()
