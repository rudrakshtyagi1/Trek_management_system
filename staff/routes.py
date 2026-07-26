from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from extensions import db
from models import Trek, Booking
from utils import role_required

staff_bp = Blueprint("staff", __name__)


def _own_trek_or_404(trek_id):
    """Fetch a trek but only if it's assigned to the currently logged-in
    staff member -- enforces 'only assigned staff can manage a trek' even
    if someone tampers with the URL."""
    trek = Trek.query.get_or_404(trek_id)
    if trek.staff_id != current_user.id:
        abort(403)
    return trek


@staff_bp.route("/dashboard")
@login_required
@role_required("staff")
def dashboard():
    my_treks = Trek.query.filter_by(staff_id=current_user.id).all()
    total_participants = sum(
        Booking.query.filter_by(trek_id=t.id, status="Booked").count() for t in my_treks
    )
    open_treks = sum(1 for t in my_treks if t.status == "Open")
    return render_template(
        "staff/dashboard.html",
        my_treks=my_treks,
        total_participants=total_participants,
        open_treks=open_treks,
    )


@staff_bp.route("/treks/<int:trek_id>", methods=["GET", "POST"])
@login_required
@role_required("staff")
def manage_trek(trek_id):
    trek = _own_trek_or_404(trek_id)

    if request.method == "POST":
        new_status = request.form.get("status")
        new_available = request.form.get("available_slots", type=int)

        if new_status:
            trek.status = new_status
        if new_available is not None:
            if new_available > trek.total_slots or new_available < 0:
                flash("Available slots must be between 0 and total slots.", "danger")
                return redirect(url_for("staff.manage_trek", trek_id=trek.id))
            trek.available_slots = new_available

        db.session.commit()
        flash("Trek updated.", "success")
        return redirect(url_for("staff.manage_trek", trek_id=trek.id))

    participants = (
        Booking.query.filter_by(trek_id=trek.id).order_by(Booking.booking_date.desc()).all()
    )
    return render_template("staff/manage_trek.html", trek=trek, participants=participants)


@staff_bp.route("/treks/<int:trek_id>/mark/<string:new_status>", methods=["POST"])
@login_required
@role_required("staff")
def mark_trek(trek_id, new_status):
    if new_status not in ("Open", "Closed", "Completed"):
        abort(400)
    trek = _own_trek_or_404(trek_id)
    trek.status = new_status

    if new_status == "Completed":
        # roll every active booking on this trek over to Completed too,
        # so it shows up correctly in each trekker's history
        for booking in Booking.query.filter_by(trek_id=trek.id, status="Booked").all():
            booking.status = "Completed"

    db.session.commit()
    flash(f"Trek marked as {new_status}.", "success")
    return redirect(url_for("staff.manage_trek", trek_id=trek.id))
