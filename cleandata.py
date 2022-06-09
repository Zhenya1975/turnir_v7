from models.models import ParticipantsDB, FightsDB, CompetitionsDB, BacklogDB, RegistrationsDB
from extensions import extensions
from app import app

db = extensions.db

with app.app_context():
    db.session.query(ParticipantsDB).delete()
    db.session.query(RegistrationsDB).delete()
    db.session.query(CompetitionsDB).delete()
    db.session.commit()
