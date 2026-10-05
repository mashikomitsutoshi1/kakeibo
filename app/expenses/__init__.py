from flask import Blueprint

expenses = Blueprint('expenses', __name__)

from app.expenses import routes  # noqa: F401, E402
