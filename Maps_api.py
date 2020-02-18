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
        self.top = ''

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
        dy = 375 - pos[1]
        dx = pos[0] - 300
        lx = self.lon + dx * coord_to_geo_x * math.pow(2, 15 - self.zoom)
        ly = self.lat + dy * coord_to_geo_y * math.cos(math.radians(self.lat)) * math.pow(2, 15 - self.zoom)
        return lx, ly


# Создание карты с соответствующими параметрами.
def load_map(mp):
    map_request = f"http://static-maps.yandex.ru/1.x/?ll={mp.ll()}&z={mp.zoom}&l={mp.type}&pt={mp.point}"
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


def find_corporation(coord):
    global to_find
    search_api_server = "https://search-maps.yandex.ru/v1/"
    api_key = "dda3ddba-c9ea-4ead-9010-f43fbc15c6e3"

    address_ll = coord

    search_params = {
        "apikey": api_key,
        "lang": "ru_RU",
        'text': 'аптека',
        'll': address_ll,
        'spn': '0.005,0.005',
        "type": "biz",
        'rspn': 1
    }
    response = requests.get(search_api_server, params=search_params)
    # Преобразуем ответ в json-объект
    json_response = response.json()
    try:
        # Получаем первую найденную организацию.
        organization = json_response["features"][0]
        # Название организации.
        org_name = organization["properties"]["CompanyMetaData"]["name"]
        # Адрес организации.
        org_address = organization["properties"]["CompanyMetaData"]["address"]

        # Получаем координаты ответа.
        point = organization["geometry"]["coordinates"]

        org_point = "{0},{1}".format(point[0], point[1])
        start_find(org_point, 2)
    except IndexError:
        to_find = 'Организации рядом не найдено'


# Создание холста с текстом.
def render_text(text):
    font = pygame.font.Font(None, 30)
    return font.render(text, 1, (100, 0, 100))


clock = pygame.time.Clock()


def start_find(address, key=1):
    global mp, to_find, index, to_find_2
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
        mp.top = toponym
        # Долгота и Широта :
        if key == 1:
            mp.lon, mp.lat = [float(x) for x in toponym_coodrinates.split(" ")]
        mp.point = f'{",".join(toponym_coodrinates.split(" "))},pm2rdm'
        to_find = toponym['metaDataProperty']['GeocoderMetaData']['text']
        if index:
            to_find_2 = mp.top['metaDataProperty']['GeocoderMetaData']['Address']
            if 'postal_code' in to_find_2:
                to_find_2 = str(mp.top['metaDataProperty']['GeocoderMetaData'][
                                    'Address']['postal_code'])
            else:
                to_find_2 = 'нет почтового индекса'


to_find = to_find_2 = ''


def main():
    global mp, to_find, index, to_find_2
    index = False
    text = ''
    # Инициализируем pygame
    pygame.init()
    running = True
    screen = pygame.display.set_mode((600, 600))
    ind_txt = 'index OFF'
    # Заводим объект, в котором будем хранить все параметры отрисовки карты.
    mp = MapParams()
    while running:
        font = pygame.font.Font(None, 40)
        input_box = pygame.Rect(170, 10, 140, 32)
        color = pygame.Color('blue')

        input_box2 = pygame.Rect(170, 50, 140, 32)
        post_index = pygame.Rect(400, 50, 110, 32)
        map = pygame.Rect(0, 150, 600, 450)
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
            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box2.collidepoint(event.pos):
                    to_find = to_find_2 = mp.point = ''
                if post_index.collidepoint(event.pos):
                    index = not index
                    ind_txt = 'index ON' if index else 'index OFF'
                    if index:
                        to_find_2 = mp.top['metaDataProperty']['GeocoderMetaData']['Address']
                        if 'postal_code' in to_find_2:
                            to_find_2 = str(mp.top['metaDataProperty']['GeocoderMetaData'][
                                                'Address']['postal_code'])
                        else:
                            to_find_2 = 'нет почтового индекса'
                    else:
                        to_find_2 = ''
                if event.button == 1:
                    if map.collidepoint(event.pos):
                        coordinates = mp.screen_to_geo(event.pos)
                        coordinates = str(coordinates[0]) + ',' + str(coordinates[1])
                        start_find(coordinates, key=2)
                if event.button == 3:
                    if map.collidepoint(event.pos):
                        coordinates = mp.screen_to_geo(event.pos)
                        coordinates = str(coordinates[0]) + ',' + str(coordinates[1])
                        find_corporation(coordinates)

        screen.fill((0, 0, 0))
        font = pygame.font.Font(None, 25)
        t = font.render('Введите метку', 1, (255, 255, 100))
        screen.blit(t, (10, 10))
        t = font.render(f'Адрес: {to_find}', 1, (255, 255, 100))
        screen.blit(t, (10, 85))
        t = font.render(f'Почтовый индекс: {to_find_2}', 1, (255, 255, 100))
        screen.blit(t, (10, 105))
        # Render the current text.
        txt_surface = font.render(text, True, color)
        # Resize the box if the text is too long.
        width = max(200, txt_surface.get_width() + 10)
        input_box.w = width
        # Blit the text.
        screen.blit(txt_surface, (input_box.x + 5, input_box.y + 3))
        # Blit the input_box rect.
        pygame.draw.rect(screen, color, input_box, 2)
        text2 = font.render('Сброс метки', 1, (255, 255, 100))
        screen.blit(text2, (175, 55))
        pygame.draw.rect(screen, color, input_box2, 2)
        text2 = font.render(ind_txt, 1, (255, 255, 100))
        screen.blit(text2, (405, 55))
        pygame.draw.rect(screen, color, post_index, 2)
        # Загружаем карту, используя текущие параметры.
        map_file = load_map(mp)
        # Рисуем картинку, загружаемую из только что созданного файла.
        screen.blit(pygame.image.load(map_file), (0, 150))
        # Переключаем экран и ждем закрытия окна.
        pygame.display.flip()
        clock.tick(100)
    pygame.quit()
    # Удаляем за собой файл с изображением.
    os.remove(map_file)


if __name__ == "__main__":
    main()
