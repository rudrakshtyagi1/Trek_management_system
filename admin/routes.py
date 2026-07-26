from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required

from extensions import db
from models import Trek, Staff, User, Booking, TrekReview
from utils import role_required

admin_bp = Blueprint("admin", __name__)


def _bar_chart(pairs):
    """Turn a list of (label, count) into bars with a pre-computed width %,
    so the template can render plain CSS bars with zero JS."""
    top = max((c for _, c in pairs), default=0)
    return [{"label": l, "count": c, "pct": round(c / top * 100) if top else 0} for l, c in pairs]


@admin_bp.route("/dashboard")
@login_required
@role_required("admin")
def dashboard():
    stats = {
        "total_treks": Trek.query.count(),
        "total_users": User.query.count(),
        "total_staff": Staff.query.count(),
        "total_bookings": Booking.query.count(),
    }
    recent_bookings = Booking.query.order_by(Booking.booking_date.desc()).limit(5).all()

    difficulty_counts = {"Easy": 0, "Moderate": 0, "Hard": 0}
    for trek in Trek.query.all():
        if trek.difficulty in difficulty_counts:
            difficulty_counts[trek.difficulty] += 1

    staff_status_counts = {"Pending": 0, "Approved": 0, "Rejected": 0, "Blacklisted": 0}
    for s in Staff.query.all():
        key = s.status.capitalize()
        if key in staff_status_counts:
            staff_status_counts[key] += 1

    popular = (
        db.session.query(Trek.name, db.func.count(Booking.id))
        .join(Booking, Booking.trek_id == Trek.id)
        .group_by(Trek.id)
        .order_by(db.desc(db.func.count(Booking.id)))
        .limit(5)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_bookings=recent_bookings,
        difficulty_chart=_bar_chart(list(difficulty_counts.items())),
        staff_chart=_bar_chart(list(staff_status_counts.items())),
        popular_chart=_bar_chart(popular),
    )


@admin_bp.route("/treks")
@login_required
@role_required("admin")
def treks():
    query = request.args.get("q", "").strip()
    treks_query = Trek.query
    if query:
        like = f"%{query}%"
        treks_query = treks_query.filter(
            db.or_(Trek.name.ilike(like), Trek.location.ilike(like))
        )
    all_treks = treks_query.order_by(Trek.id.desc()).all()
    return render_template("admin/treks.html", treks=all_treks, query=query)


@admin_bp.route("/treks/new", methods=["GET", "POST"])
@login_required
@role_required("admin")
def new_trek():
    staff_options = Staff.query.filter_by(status="approved").all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        location = request.form.get("location", "").strip()
        difficulty = request.form.get("difficulty")
        duration_days = request.form.get("duration_days", type=int)
        total_slots = request.form.get("total_slots", type=int)
        staff_id = request.form.get("staff_id", type=int) or None
        status = request.form.get("status", "Pending")
        description = request.form.get("description", "").strip()
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")

        if not all([name, location, difficulty, duration_days, total_slots]):
            flash("Please fill in all required fields.", "danger")
            return render_template("admin/trek_form.html", staff_options=staff_options, trek=None)

        trek = Trek(
            name=name,
            location=location,
            difficulty=difficulty,
            duration_days=duration_days,
            total_slots=total_slots,
            available_slots=total_slots,
            staff_id=staff_id,
            status=status,
            description=description,
            start_date=datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None,
            end_date=datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None,
        )
        db.session.add(trek)
        db.session.commit()
        flash("Trek created.", "success")
        return redirect(url_for("admin.treks"))

    return render_template("admin/trek_form.html", staff_options=staff_options, trek=None)


@admin_bp.route("/treks/<int:trek_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_trek(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    staff_options = Staff.query.filter_by(status="approved").all()

    if request.method == "POST":
        booked = trek.total_slots - trek.available_slots
        new_total = request.form.get("total_slots", type=int)

        trek.name = request.form.get("name", "").strip()
        trek.location = request.form.get("location", "").strip()
        trek.difficulty = request.form.get("difficulty")
        trek.duration_days = request.form.get("duration_days", type=int)
        trek.staff_id = request.form.get("staff_id", type=int) or None
        trek.status = request.form.get("status", trek.status)
        trek.description = request.form.get("description", "").strip()

        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        trek.start_date = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        trek.end_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

        if new_total is not None:
            if new_total < booked:
                flash(f"Can't set total slots below {booked} (already booked).", "danger")
                return render_template("admin/trek_form.html", staff_options=staff_options, trek=trek)
            trek.total_slots = new_total
            trek.available_slots = new_total - booked

        db.session.commit()
        flash("Trek updated.", "success")
        return redirect(url_for("admin.treks"))

    return render_template("admin/trek_form.html", staff_options=staff_options, trek=trek)


@admin_bp.route("/treks/<int:trek_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_trek(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    db.session.delete(trek)
    db.session.commit()
    flash("Trek deleted.", "info")
    return redirect(url_for("admin.treks"))


@admin_bp.route("/staff")
@login_required
@role_required("admin")
def staff_list():
    tab = request.args.get("tab", "pending")
    status_map = {"pending": "pending", "approved": "approved", "blacklisted": "blacklisted", "rejected": "rejected"}
    filter_status = status_map.get(tab, "pending")
    staff_members = Staff.query.filter_by(status=filter_status).order_by(Staff.created_at.desc()).all()
    counts = {
        "pending": Staff.query.filter_by(status="pending").count(),
        "approved": Staff.query.filter_by(status="approved").count(),
        "blacklisted": Staff.query.filter_by(status="blacklisted").count(),
    }
    return render_template("admin/staff.html", staff_members=staff_members, tab=tab, counts=counts)


@admin_bp.route("/staff/<int:staff_id>/set-status/<string:new_status>", methods=["POST"])
@login_required
@role_required("admin")
def set_staff_status(staff_id, new_status):
    if new_status not in ("approved", "rejected", "blacklisted", "pending"):
        abort(400)
    staff = Staff.query.get_or_404(staff_id)
    staff.status = new_status
    db.session.commit()
    flash(f"Staff status updated to {new_status}.", "success")
    return redirect(url_for("admin.staff_list"))


@admin_bp.route("/users")
@login_required
@role_required("admin")
def users_list():
    query = request.args.get("q", "").strip()
    users_query = User.query
    if query:
        like = f"%{query}%"
        users_query = users_query.filter(db.or_(User.name.ilike(like), User.email.ilike(like)))
    all_users = users_query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users, query=query)


@admin_bp.route("/users/<int:user_id>/toggle-blacklist", methods=["POST"])
@login_required
@role_required("admin")
def toggle_user_blacklist(user_id):
    user = User.query.get_or_404(user_id)
    user.is_blacklisted = not user.is_blacklisted
    db.session.commit()
    flash("User status updated.", "success")
    return redirect(url_for("admin.users_list"))


@admin_bp.route("/bookings")
@login_required
@role_required("admin")
def bookings_list():
    all_bookings = Booking.query.order_by(Booking.booking_date.desc()).all()
    return render_template("admin/bookings.html", bookings=all_bookings)


@admin_bp.route("/search")
@login_required
@role_required("admin")
def search():
    query = request.args.get("q", "").strip()
    treks_found, staff_found, users_found = [], [], []
    if query:
        like = f"%{query}%"
        treks_found = Trek.query.filter(db.or_(Trek.name.ilike(like), Trek.location.ilike(like))).all()
        staff_found = Staff.query.filter(db.or_(Staff.name.ilike(like), Staff.email.ilike(like))).all()
        users_found = User.query.filter(db.or_(User.name.ilike(like), User.email.ilike(like))).all()
    return render_template(
        "admin/search.html", query=query, treks=treks_found, staff=staff_found, users=users_found
    )
