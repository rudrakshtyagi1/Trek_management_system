from datetime import datetime
from flask_login import UserMixin
from extensions import db

# Admin / Staff / User are 3 separate tables. Flask-Login needs one id per
# session, so get_id() returns "admin-1" / "staff-3" / "user-7" and
# auth/routes.py's user_loader splits on the "-" to know which table to query.


class Admin(db.Model, UserMixin):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def get_id(self):
        return f"admin-{self.id}"


class Staff(db.Model, UserMixin):
    __tablename__ = "staff"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    contact = db.Column(db.String(20))

    # pending -> approved (by admin) -> can log into dashboard
    # admin can also reject or blacklist a staff member
    status = db.Column(db.String(20), default="pending", nullable=False)
    # allowed values: pending, approved, rejected, blacklisted

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    treks = db.relationship("Trek", backref="assigned_staff", lazy=True)

    def get_id(self):
        return f"staff-{self.id}"

    @property
    def is_active(self):
        # Flask-Login uses this to block login entirely for blacklisted staff
        return self.status != "blacklisted"


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    contact = db.Column(db.String(20))
    is_blacklisted = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship("Booking", backref="user", lazy=True)
    reviews = db.relationship("TrekReview", backref="user", lazy=True)

    def get_id(self):
        return f"user-{self.id}"

    @property
    def is_active(self):
        return not self.is_blacklisted


class Trek(db.Model):
    __tablename__ = "treks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)  # Easy / Moderate / Hard
    duration_days = db.Column(db.Integer, nullable=False)

    total_slots = db.Column(db.Integer, nullable=False)
    available_slots = db.Column(db.Integer, nullable=False)

    staff_id = db.Column(db.Integer, db.ForeignKey("staff.id"), nullable=True)

    # Pending -> Approved -> Open -> Closed -> Completed
    status = db.Column(db.String(20), default="Pending", nullable=False)

    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship("Booking", backref="trek", lazy=True)
    reviews = db.relationship("TrekReview", backref="trek", lazy=True)

    @property
    def booked_slots(self):
        return self.total_slots - self.available_slots

    @property
    def average_rating(self):
        ratings = [r.rating for r in self.reviews]
        return round(sum(ratings) / len(ratings), 1) if ratings else None


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    trek_id = db.Column(db.Integer, db.ForeignKey("treks.id"), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Booked -> Cancelled / Completed
    status = db.Column(db.String(20), default="Booked", nullable=False)


class TrekReview(db.Model):
    """Optional depth feature: trekkers can rate/review a completed trek.
    Feeds the 'popular treks' chart on the admin dashboard."""
    __tablename__ = "trek_reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    trek_id = db.Column(db.Integer, db.ForeignKey("treks.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
