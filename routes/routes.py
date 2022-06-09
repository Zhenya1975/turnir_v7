from flask import Blueprint, render_template, redirect, url_for, abort, request, jsonify
from models.models import ParticipantsDB, FightsDB, CompetitionsDB, BacklogDB, RegistrationsDB
from extensions import extensions
from sqlalchemy import desc

db = extensions.db
home = Blueprint('home', __name__, template_folder='templates')


def fight_create_func(competition_id, round_number, final_status):
    competition_id = competition_id
    round_number = round_number
    final_status = final_status
    backlog_data = BacklogDB.query.filter_by(competition_id=competition_id, round_number=round_number).all()
    red_fighter_reg_id = backlog_data[0].reg_id
    blue_fighter_reg_id = backlog_data[1].reg_id
    new_fight = FightsDB(competition_id=competition_id, round_number=round_number, red_fighter_id=red_fighter_reg_id,
                         blue_fighter_id=blue_fighter_reg_id, final_status=final_status)
    db.session.add(new_fight)

    try:
        db.session.commit()

    except Exception as e:
        print("не получилось создать новый бой. Ошибка:  ", e)
        db.session.rollback()

    return round_number

    ################################################################


def delete_backlog_records(competition_id, round_number):
    competition_id = competition_id
    round_number = round_number
    # удаляем из бэклога записи с бойцами из созданного боя
    last_created_fight = FightsDB.query.filter_by(competition_id=competition_id, round_number=round_number).order_by(
        desc(FightsDB.fight_id)).first()
    # удаляем записи из бэклога бойцов, которые зашли в бой
    backlog_record_to_delete_red = BacklogDB.query.filter_by(competition_id=competition_id, round_number=round_number,
                                                             reg_id=last_created_fight.red_fighter_id).order_by(
        desc(BacklogDB.reg_id)).first()
    if backlog_record_to_delete_red is None:
        abort(404, description="No backlog record was Found with the given ID")
    else:
        db.session.delete(backlog_record_to_delete_red)
    backlog_record_to_delete_blue = BacklogDB.query.filter_by(competition_id=competition_id, round_number=round_number,
                                                              reg_id=last_created_fight.blue_fighter_id).order_by(
        desc(BacklogDB.reg_id)).first()
    if backlog_record_to_delete_blue is None:
        abort(404, description="No backlog record was Found with the given ID")
    else:
        db.session.delete(backlog_record_to_delete_blue)
    try:
        db.session.commit()

    except Exception as e:
        print("Не удалось удалить записи из бэклога", e)
        db.session.rollback()
    ########################################################


def clear_backlog(competition_id):
    backlog_data = BacklogDB.query.filter_by(competition_id=competition_id).all()
    if len(backlog_data) > 0:
        for row in backlog_data:
            if row is None:
                abort(404, description="No backlog record was Found with the given ID")
            else:
                db.session.delete(row)
        try:
            db.session.commit()
        except Exception as e:
            print("Не удалось очистить бэклог", e)
            db.session.rollback()


@home.route('/')
def home_view():
    return redirect(url_for('home.competition_start'))


@home.route('/competition_start/')
def competition_start():
    return render_template('competition_start.html')


@home.route('/competition_create_new/')
def competition_create_new():
    db.session.query(BacklogDB).delete()
    new_competition = CompetitionsDB()
    db.session.add(new_competition)
    db.session.commit()
    created_competition_data = CompetitionsDB.query.order_by(desc(CompetitionsDB.competition_id)).first()
    competition_id = created_competition_data.competition_id
    # создаем записи регистраций на созданное соревнование
    participant_data = ParticipantsDB.query.all()
    for participant in participant_data:
        new_registration = RegistrationsDB(participant_id=participant.participant_id, competition_id=competition_id,
                                           activity_status=1)
        db.session.add(new_registration)
        try:
            db.session.commit()
        except Exception as e:
            print("Не удалось создать запись в регистрациях", e)
            db.session.rollback()

    # помещаем всех зарегистрированных бойцов в бэклог
    # participants_data = ParticipantsDB.query.all()
    regs_data = RegistrationsDB.query.filter_by(competition_id=competition_id).all()
    for registration in regs_data:
        reg_id = registration.reg_id
        new_backlog_record = BacklogDB(reg_id=reg_id, competition_id=competition_id, round_number=1)
        db.session.add(new_backlog_record)
        try:
            db.session.commit()
        except Exception as e:
            print("Не удалось создать запись в бэклоге", e)
            db.session.rollback()

    # проверяем ситуацию в бэклоге в текущем и следующем раунде
    current_backlog_data = BacklogDB.query.filter_by(competition_id=competition_id, round_number=1).all()
    next_round_backlog_data = BacklogDB.query.filter_by(competition_id=competition_id, round_number=2).all()

    if len(current_backlog_data) == 0 and len(next_round_backlog_data) == 2:
        current_round_number = 2

        final_status = 'continue'
        fight_create_func(competition_id, current_round_number, final_status)
        # удаляем из бэклога записи с бойцами
        delete_backlog_records(competition_id, current_round_number)
    elif len(current_backlog_data) == 2 and len(next_round_backlog_data) == 0:

        current_round_number = 1
        final_status = 'continue'
        fight_create_func(competition_id, current_round_number, final_status)
        # удаляем из бэклога записи с бойцами
        delete_backlog_records(competition_id, current_round_number)
    elif len(current_backlog_data) == 1 and len(next_round_backlog_data) == 1:

        current_round_number = 1
        final_status = 'continue'
        next_round_fighter_data = BacklogDB.query.filter_by(competition_id=competition_id,
                                                            round_number=current_round_number + 1).first()
        # проверяем на случай если это один и тот же боец
        current_round_fighter_data = BacklogDB.query.filter_by(competition_id=competition_id,
                                                               round_number=current_round_number).first()
        if next_round_fighter_data.fighter_id != current_round_fighter_data.fighter_id:
            next_round_fighter_data.round_number = current_round_number
            try:
                db.session.commit()

            except Exception as e:
                print("не удалось переписать номер круга в записи бойца из следующего круга", e)
                db.session.rollback()

        fight_create_func(competition_id, current_round_number, final_status)
        # удаляем из бэклога записи с бойцами
        delete_backlog_records(competition_id, current_round_number)
    else:
        fight_create_func(competition_id, 1, 'continue')
        # удаляем из бэклога записи с созданным боем
        last_created_fight = FightsDB.query.filter_by(competition_id=competition_id).order_by(
            desc(FightsDB.fight_id)).first()
        # удаляем записи из бэклога бойцов, которые зашли в бой
        delete_backlog_records(last_created_fight.competition_id, 1)

    return redirect(url_for('home.competition_view', competition_id=competition_id))


@home.route('/competition/<int:competition_id>')
def competition_view(competition_id):
    competition_id = competition_id
    # round_number = fight_create_func(round_number_prev)
    last_created_fight = FightsDB.query.filter_by(competition_id=competition_id).order_by(
        desc(FightsDB.fight_id)).first()

    return render_template("competition.html", fight_data=last_created_fight)


@home.route('/competition_delete/')
def competition_delete():
    db.session.query(CompetitionsDB).delete()
    db.session.commit()

    return "deleted"


@home.route('/ajaxfile', methods=["POST", "GET"])
def ajaxfile():
    final_status = "continue"
    if request.method == 'POST':
        fight_id = request.form['fight_id']
        winner_color = request.form['winner_color']
        current_fight_data = FightsDB.query.get(fight_id)
        competition_id = current_fight_data.competition_id
        current_round_number = current_fight_data.round_number

        # обновляем данные о победителе и проигравшем
        if winner_color == "red":
            current_fight_data.blue_fighter.activity_status = 0
            current_fight_data.fight_winner_id = current_fight_data.red_fighter_id
        else:
            current_fight_data.red_fighter.activity_status = 0
            current_fight_data.fight_winner_id = current_fight_data.blue_fighter_id
        try:
            db.session.commit()
        except Exception as e:
            print("Не удалось вывести из игры синего бойца", e)
            db.session.rollback()
        # добавляем в бэклог в следующий круг новую запись с победившим
        if winner_color == "red":
            new_backlog_record = BacklogDB(reg_id=current_fight_data.red_fighter_id, competition_id=competition_id,
                                           round_number=current_round_number + 1)
        else:
            new_backlog_record = BacklogDB(reg_id=current_fight_data.blue_fighter_id, competition_id=competition_id,
                                           round_number=current_round_number + 1)
        db.session.add(new_backlog_record)
        try:
            db.session.commit()

        except Exception as e:
            print("не удалось добавить запись с победившим в бэклог", e)
            db.session.rollback()

        # проверяем ситуацию в бэклоге в текущем и следующем раунде
        next_round_backlog_data = BacklogDB.query.filter_by(competition_id=competition_id,
                                                            round_number=current_round_number + 1).all()

        current_backlog_data = BacklogDB.query.filter_by(competition_id=competition_id,
                                                         round_number=current_round_number).all()

        # print("len(current_backlog_data): ", len(current_backlog_data), "len(next_round_backlog_data): ", len(next_round_backlog_data))
        if len(current_backlog_data) == 1 and len(next_round_backlog_data) == 1:

            final_status = 'continue'
            next_round_fighter_data = BacklogDB.query.filter_by(competition_id=competition_id,
                                                                round_number=current_round_number + 1).first()

            current_round_fighter_data = BacklogDB.query.filter_by(competition_id=competition_id,
                                                                   round_number=current_round_number).first()

            if next_round_fighter_data.fighter_id != current_round_fighter_data.fighter_id:
                current_round_fighter_data.round_number = current_round_number + 1
                current_round_number = current_round_number + 1
                try:
                    db.session.commit()

                except Exception as e:
                    print("не удалось переписать номер круга в записи бойца из следующего круга", e)
                    db.session.rollback()

                fight_create_func(competition_id, current_round_number, final_status)
                # удаляем из бэклога записи с бойцами
                delete_backlog_records(competition_id, current_round_number)

        elif len(current_backlog_data) == 0 and len(next_round_backlog_data) == 1:
            final_status = 'finish'

            clear_backlog(competition_id)

            return jsonify(
                {
                    'final_status': final_status,
                    'fight_id': fight_id,
                })

        elif len(current_backlog_data) == 0 and len(next_round_backlog_data) == 0:
            final_status = 'finish'

            return jsonify(
                {
                    'final_status': final_status,
                    'fight_id': fight_id,
                })

        # если в след раунде два бойца, а в текущем ни одного
        elif len(current_backlog_data) == 0 and len(next_round_backlog_data) > 1:
            current_round_number = current_round_number + 1
            final_status = 'continue'
            fight_create_func(competition_id, current_round_number, final_status)
            delete_backlog_records(competition_id, current_round_number)

        elif len(current_backlog_data) == 1 and len(next_round_backlog_data) > 1:
            current_round_fighter_data = BacklogDB.query.filter_by(competition_id=competition_id,
                                                                   round_number=current_round_number).first()
            current_round_fighter_data.round_number = current_round_number + 1
            try:
                db.session.commit()
            except Exception as e:
                print("не удалось перекинуть бойца в бэклог следующего круга", e)
                db.session.rollback()
            current_round_number = current_round_number + 1
            final_status = 'continue'
            fight_create_func(competition_id, current_round_number, final_status)
            # удаляем из бэклога записи с бойцами
            delete_backlog_records(competition_id, current_round_number)

        elif len(current_backlog_data) > 1:
            print("len(current_backlog_data) > 1")
            fight_create_func(competition_id, current_round_number, 'continue')
            delete_backlog_records(competition_id, current_round_number)
        else:
            print("что-то непонятное")

        last_created_fight = FightsDB.query.filter_by(competition_id=competition_id,
                                                      round_number=current_round_number).order_by(
            desc(FightsDB.fight_id)).first()

        return jsonify(
            {'htmlresponsered': render_template('response_red_fighter_div.html', fight_data=last_created_fight),
             'htmlresponseblue': render_template('response_blue_fighter_div.html', fight_data=last_created_fight),
             'htmlresponsetitle': render_template('response_title_div.html', fight_data=last_created_fight),
             'final_status': final_status,
             'fight_id': last_created_fight.fight_id
             })


@home.route('/competition_finish/<int:fight_id>')
def finish(fight_id):
    fight_data = FightsDB.query.get(fight_id)
    winner_reg_id = fight_data.fight_winner_id
    competition_id = fight_data.competition_id
    registration_data = RegistrationsDB.query.get(winner_reg_id)
    participant_id = registration_data.participant_id
    winner_data = ParticipantsDB.query.get(participant_id)
    fights_data = FightsDB.query.filter_by(competition_id=competition_id).all()
    return render_template("finish.html", winner_data=winner_data, fights_data=fights_data)
