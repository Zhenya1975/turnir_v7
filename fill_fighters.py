import csv
from models.models import ParticipantsDB
from extensions import extensions
from app import app

db = extensions.db


def fill_fighters():
    with app.app_context():
        with open('fighters.csv', encoding='utf8') as csvfile:
            fighters_csv_list = csv.reader(csvfile)

            for row in fighters_csv_list:
                new_fighter = ParticipantsDB(participant_first_name=row[0], participant_last_name=row[1],
                                             fighter_image=row[8])
                db.session.add(new_fighter)
                try:
                    db.session.commit()
                    # print("Боец импортирован в ParticipantsDB")
                except Exception as e:
                    print("Не получилось импортировать бойцов. Ошибка: ", e)
                    db.session.rollback()
        participants_data = ParticipantsDB.query.all()
        print("бойцы импортированы: ", len(participants_data))
        return "результат импорта - в принт"


fill_fighters()
