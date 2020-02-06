import re
import os
import mysql.connector
from bs4 import BeautifulSoup

from settings import MYSQL_PASSWORD

mydb = mysql.connector.connect(
    host="127.0.0.1",
    user="root",
    passwd=MYSQL_PASSWORD,
    database="mydatabase",
    auth_plugin="mysql_native_password"
)

mycursor = mydb.cursor()


persons = []
persons_data = []

fio_pattern = r"[А-ЯЁ]* \([А-ЯЁ]*\)|[А-ЯЁ]*"
date_of_birth_pattern = r"\d{4}(?= г.р|)"

died_in_battle_pattern = r"(?<=погиб\s)\d{2}.\d{2}.\d{2,4}|(?<=погибла\s)\d{2}.\d{2}.\d{2,4}"
pass_away_pattern = r"(?<=умер\s)\d{2}.\d{2}.\d{2,4}|(?<=умерла\s)\d{2}.\d{2}.\d{2,4}"
died_of_wounds_pattern = r"(?<=умер\sот\sран\s)\d{2}.\d{2}.\d{2,4}|(?<=умер\sот\sран\s)\d{2}.\d{2}.\d{2,4}"
loss_pattern = r"(?<=пропал\sбез\sвести\s)\d{2}.\d{2}.\d{2,4}|(?<=пропала\sбез\sвести\s)\d{2}.\d{2}.\d{2,4}"
died_in_captivity_pattern = r"(?<=погиб\sв\sплену\s)\d{2}.\d{2}.\d{2,4}|(?<=погибла\sв\sплену\s)\d{2}.\d{2}.\d{2,4}"
released_from_captivity_pattern = r"(?<=попал\sв\sплен\s)\d{2}.\d{2}.\d{2,4}|(?<=попала\sв\sплен\s)\d{2}.\d{2}.\d{2,4}"

residence_pattern = r"проживал\sпосле\sвойны|проживала\sпосле\sвойны"

place_of_conscription_pattern = r"РВК|ГВК|р-н|с\.|г\.(\s|)[А-ЯЁ]"   # подумать

location_pattern = r"р-н|с\.|г\.(\s|)[А-ЯЁ]|не\sустановлено"
military_rank_pattern = r"ст-на|с-т|ряд\.|ст\. л-т|гв\. с-т|с-т|мл\. л-т|ефр"


# Придумать как можно лучше
def make_persons(directory):
    for root, dirs, filenames in os.walk(directory):
        for f in filenames:
            html_file = open(os.path.join(root, f), 'r', encoding='cp1251')
            print(f)
            soup = BeautifulSoup(html_file.read(), 'html.parser')
            tags = soup.p.text
            data = tags.split("\n")

            for line in data:
                if line and line != ' ':
                    line = line.strip()
                    condition = re.match(r"^[А-ЯЁ]{4,}", line)
                    if condition:
                        persons_data.append(line)
                    else:
                        persons_data[-1] = persons_data[-1]+line

    return persons_data


# Т.К. ФИО и ДР почти всегда находятся в 1м элементе списка, то искать их следует там
# Остальные данные могут быть в произвольном элементе списка, поэтому поиск идет по всем элементам, кроме 1го

# Проверяет в элементе, и возвращает список ФИО
def check_fio(pattern, data):
    result = re.findall(pattern, data)
    if result:
        result = list(filter(None, result))
        return result
    return None


# Проверяет в элементе, и возвращает результат
# "дата рождения" находится в 1м элементе списка

def check_one(pattern, data):
    result = re.findall(pattern, data)
    if result:
        return result[0]
    return None


# Проверяет в списке, и возвращает результат
# Среди всех  элементов ищутся даты смерти

def check_list(pattern, data):
    for element in data:
        result = re.findall(pattern, element)
        if result:
            return result[0]
    return None


# Проверяет в списке, и возвращает элемент
# Если находит часть из звания - то возращает весь элемент

def check_data(pattern, data):
    for element in data:
        result = re.findall(pattern, element)
        if result:
            return element.strip()
    return None


# Придумать как сделать проверку
# 1. Проверку между датой и званием не сделать, т.к. может не быть даты и звания
def check_conscription(pattern, data):
    for element in data:
        result = re.findall(pattern, element)
        if result:
            return element.strip()
    return None


def check_residence(pattern, data):
    for element in data:
        result = re.findall(pattern, element)
        if result:
            r = element.rfind("после войны")
            return element[r+11:].strip(), True
    return None, False


# Проверяет в списке, и возвращает дату смерти
# Элемен "место смерти" идет после "даты смерти"
def check_date(pattern_date, pattern_location, data):
    for element in data:
        result = re.findall(pattern_date, element)
        if result:
            try:
                test = re.findall(pattern_location, data[data.index(element)+1])
                if test:
                    return result[0], data[data.index(element)+1].strip(), True
            except IndexError:
                return result[0], None, True
    return None, None, False


def check_released(pattern_date, data):
    for element in data:
        result = re.findall(pattern_date, element)
        if result:
            return result[0], None, True
    return None, None, False


def pars(persons):
    for person in persons:

        name = None
        patronymic = None
        date_of_birth = None
        place_of_conscription = None
        military_rank = None
        date_of_death = None
        location = None
        fate = None

        died_in_battle = False
        loss = False
        pass_away = False
        died_of_wounds = False
        residence = False
        died_in_captivity = False
        released_from_captivity = False

        is_valid = False

        fio = check_fio(fio_pattern, person[0])

        surname = fio[0].capitalize()
        try:
            name = fio[1].capitalize()
        except IndexError:
            name = None
        try:
            patronymic = fio[2].capitalize()
        except IndexError:
            patronymic = None

        date_of_birth = check_one(
            date_of_birth_pattern,
            person[0]
            )

        place_of_conscription = check_conscription(
            place_of_conscription_pattern,
            person[1:3]
            )

        military_rank = check_data(
            military_rank_pattern,
            person[1:]
            )

        date_died_in_battle, place_died_in_battle, died_in_battle = check_date(
            died_in_battle_pattern,
            location_pattern,
            person[1:]
            )

        date_of_loss, place_of_loss, loss = check_date(
            loss_pattern,
            location_pattern,
            person[1:]
            )

        date_of_pass_away, place_of_pass_away, pass_away = check_date(
            pass_away_pattern,
            location_pattern,
            person[1:]
            )

        date_died_of_wounds, place_died_of_wounds, died_of_wounds = check_date(
            died_of_wounds_pattern,
            location_pattern,
            person[1:]
            )

        date_died_in_captivity, place_died_in_captivity, died_in_captivity = check_date(
            died_in_captivity_pattern,
            location_pattern,
            person[1:]
            )

        date_released_from_captivity, place_released_from_captivity, released_from_captivity = check_released(
            released_from_captivity_pattern,
            person[1:]
            )

        place_of_residence, residence = check_residence(
            residence_pattern,
            person[1:]
            )

        if released_from_captivity:
            print("True")

        if died_in_battle:
            date_of_death = date_died_in_battle
            location = place_died_in_battle
            fate = "погиб"
        elif loss:
            date_of_death = date_of_loss
            location = place_of_loss
            fate = "пропал без вести"
        elif pass_away:
            date_of_death = date_of_pass_away
            location = place_of_pass_away
            fate = "умер"
        elif died_of_wounds:
            date_of_death = date_died_of_wounds
            location = place_died_of_wounds
            fate = "умер от ран"
        elif died_in_captivity:
            date_of_death = date_died_in_captivity
            location = place_died_in_captivity
            fate = "погиб в плену"
        elif released_from_captivity:
            date_of_death = date_released_from_captivity
            location = place_released_from_captivity
            fate = "попал в плен, освобожден"
        elif residence:
            location = place_of_residence
            fate = "проживал после войны"
        else:
            fate = "не указано"

        sql = """INSERT INTO persons
        (surname, name, patronymic,
        date_of_birth, place_of_conscription, military_rank,
        date_of_death, location,
        fate,
        is_valid)
        VALUES
        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""

        val = (
            surname, name, patronymic,
            date_of_birth, place_of_conscription, military_rank,
            date_of_death, location,
            fate,
            is_valid
            )

        mycursor.execute(sql, val)


folder = r'/mnt/c/projects/parsing/html'
make_persons(folder)

for person in persons_data:
    result = re.split(r',', person)
    persons.append(result)
print(len(persons_data))
print(len(persons))
pars(persons)

mydb.commit()
print(mycursor.rowcount, "record inserted.")
