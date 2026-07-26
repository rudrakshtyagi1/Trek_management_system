from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db
from models import Trek, Booking, TrekReview
from utils import role_required

user_bp = Blueprint("user", __name__)


@user_bp.route("/dashboard")
@login_required
@role_required("user")
def dashboard():
    available_treks = Trek.query.filter_by(status="Open").order_by(Trek.id.desc()).limit(6).all()
    my_bookings = (
        Booking.query.filter_by(user_id=current_user.id)
        .order_by(Booking.booking_date.desc())
        .limit(5)
        .all()
    )
    return render_template("user/dashboard.html", treks=available_treks, bookings=my_bookings)


@user_bp.route("/treks")
@login_required
@role_required("user")
def browse_treks():
    query = request.args.get("q", "").strip()
    difficulty = request.args.get("difficulty", "").strip()
    location = request.args.get("location", "").strip()

    treks_query = Trek.query.filter_by(status="Open")
    if query:
        like = f"%{query}%"
        treks_query = treks_query.filter(Trek.name.ilike(like))
    if difficulty:
        treks_query = treks_query.filter_by(difficulty=difficulty)
    if location:
        treks_query = treks_query.filter(Trek.location.ilike(f"%{location}%"))

    treks = treks_query.order_by(Trek.id.desc()).all()
    all_locations = sorted({t.location for t in Trek.query.all()})

    return render_template(
        "user/browse_treks.html",
        treks=treks,
        query=query,
        difficulty=difficulty,
        location=location,
        all_locations=all_locations,
    )


@user_bp.route("/treks/<int:trek_id>")
@login_required
@role_required("user")
def trek_details(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    already_booked = Booking.query.filter_by(
        user_id=current_user.id, trek_id=trek.id, status="Booked"
    ).first()
    return render_template("user/trek_details.html", trek=trek, already_booked=already_booked)


@user_bp.route("/treks/<int:trek_id>/book", methods=["POST"])
@login_required
@role_required("user")
def book_trek(trek_id):
    trek = Trek.query.get_or_404(trek_id)

    if trek.status != "Open":
        flash("This trek is not open for booking.", "danger")
        return redirect(url_for("user.trek_details", trek_id=trek.id))

    if trek.available_slots <= 0:
        flash("Sorry, this trek is fully booked.", "danger")
        return redirect(url_for("user.trek_details", trek_id=trek.id))

    existing = Booking.query.filter_by(
        user_id=current_user.id, trek_id=trek.id, status="Booked"
    ).first()
    if existing:
        flash("You've already booked this trek.", "warning")
        return redirect(url_for("user.trek_details", trek_id=trek.id))

    # Re-check slots right before commit to guard against overbooking
    # under concurrent requests.
    if trek.available_slots <= 0:
        flash("Sorry, this trek just got fully booked.", "danger")
        return redirect(url_for("user.trek_details", trek_id=trek.id))

    booking = Booking(user_id=current_user.id, trek_id=trek.id, status="Booked")
    trek.available_slots -= 1
    db.session.add(booking)
    db.session.commit()

    flash("Trek booked successfully!", "success")
    return redirect(url_for("user.my_bookings"))


@user_bp.route("/bookings")
@login_required
@role_required("user")
def my_bookings():
    bookings = (
        Booking.query.filter_by(user_id=current_user.id)
        .filter(Booking.status.in_(["Booked", "Cancelled"]))
        .order_by(Booking.booking_date.desc())
        .all()
    )
    return render_template("user/my_bookings.html", bookings=bookings)


@user_bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@login_required
@role_required("user")
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        abort(403)
    if booking.status != "Booked":
        flash("This booking can't be cancelled.", "warning")
        return redirect(url_for("user.my_bookings"))

    booking.status = "Cancelled"
    booking.trek.available_slots += 1
    db.session.commit()
    flash("Booking cancelled.", "info")
    return redirect(url_for("user.my_bookings"))


@user_bp.route("/history")
@login_required
@role_required("user")
def history():
    completed = (
        Booking.query.filter_by(user_id=current_user.id, status="Completed")
        .order_by(Booking.booking_date.desc())
        .all()
    )
    my_review_trek_ids = {r.trek_id for r in TrekReview.query.filter_by(user_id=current_user.id).all()}
    return render_template("user/history.html", bookings=completed, reviewed=my_review_trek_ids)


@user_bp.route("/history/<int:trek_id>/review", methods=["POST"])
@login_required
@role_required("user")
def submit_review(trek_id):
    rating = request.form.get("rating", type=int)
    comment = request.form.get("comment", "").strip()

    if not rating or rating < 1 or rating > 5:
        flash("Please give a rating between 1 and 5.", "danger")
        return redirect(url_for("user.history"))

    completed_booking = Booking.query.filter_by(
        user_id=current_user.id, trek_id=trek_id, status="Completed"
    ).first()
    if not completed_booking:
        abort(403)

    if TrekReview.query.filter_by(user_id=current_user.id, trek_id=trek_id).first():
        flash("You've already reviewed this trek.", "warning")
        return redirect(url_for("user.history"))

    review = TrekReview(user_id=current_user.id, trek_id=trek_id, rating=rating, comment=comment)
    db.session.add(review)
    db.session.commit()
    flash("Thanks for your review!", "success")
    return redirect(url_for("user.history"))


@user_bp.route("/profile", methods=["GET", "POST"])
@login_required
@role_required("user")
def profile():
    if request.method == "POST":
        current_user.name = request.form.get("name", "").strip()
        current_user.contact = request.form.get("contact", "").strip()

        new_password = request.form.get("new_password", "")
        if new_password:
            current_user.password_hash = generate_password_hash(new_password)

        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("user.profile"))

    return render_template("user/profile.html")
