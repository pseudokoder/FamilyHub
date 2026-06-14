"""Family Plans business logic — plans, checklist items, and attachments.

The attachment half is the security-sensitive part. We accept ONLY images
and PDFs — never arbitrary files — and here's the WHY, because it's a real
lesson (D315): a general "upload any file" feature is a classic foothold.
A .html file becomes a phishing page hosted on your trusted domain; an
.svg can carry JavaScript; an .exe/.bat is malware handed a download link.
So the rule is an ALLOW-LIST of safe, viewable document types, each
validated by its actual bytes, stored under a random name outside the web
root, and served only through a login-walled route. Same discipline as
the photo uploader, applied to documents.

v2 mapping: PlanService + an AttachmentStorageService.
"""

import os
import uuid

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError

from app.extensions import db
from app.models import FamilyPlan, PlanAttachment, PlanItem
from app.services import audit_service, photo_service

# Reuse the photo uploader's image allow-list, then add PDFs. One source
# of truth for "what counts as an image" across the app.
IMAGE_EXTENSIONS = photo_service.ALLOWED_EXTENSIONS
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | {"pdf"}


# --- Plans --------------------------------------------------------------------

def get_all_plans():
    """Newest first — active planning is what people come back to."""
    return FamilyPlan.query.order_by(FamilyPlan.created_at.desc()).all()


def create_plan(title, description, user):
    plan = FamilyPlan(
        title=title.strip(),
        description=(description or "").strip(),
        created_by=user.id,
    )
    db.session.add(plan)
    db.session.flush()  # assign plan.id so the audit row can name it
    audit_service.log_event(user, "create", "plan", plan.id, plan.title)
    db.session.commit()
    return plan


def update_plan(plan, title, description, user):
    """Any member may edit — plans are collaborative, like the wiki."""
    plan.title = title.strip()
    plan.description = (description or "").strip()
    audit_service.log_event(user, "edit", "plan", plan.id, plan.title)
    db.session.commit()
    return plan


def can_delete(plan, user):
    """The Trial Period rule, same as every content pillar: an admin
    always may; the creator may only while the plan is unlocked."""
    if user.is_admin:
        return True
    return plan.created_by == user.id and not plan.is_locked


def delete_plan(plan, user):
    """Remove the plan, its items (FK cascade), and its attachment FILES."""
    for attachment in plan.attachments:
        path = attachment_path(attachment)
        if os.path.exists(path):
            os.remove(path)
    folder = _plan_dir(plan.id)
    audit_service.log_event(user, "delete", "plan", plan.id, plan.title)
    db.session.delete(plan)
    db.session.commit()
    try:
        os.rmdir(folder)  # tidy the now-empty folder; cosmetic if it fails
    except OSError:
        pass


# --- Checklist items ----------------------------------------------------------

def add_item(plan, text, user):
    item = PlanItem(plan_id=plan.id, text=text.strip(), created_by=user.id)
    db.session.add(item)
    db.session.commit()
    return item


def toggle_item(item):
    """Tick / untick. Any member may — shared ticking is the collaboration,
    so it's intentionally NOT audited (it would flood the log)."""
    item.is_done = not item.is_done
    db.session.commit()
    return item


def can_delete_item(item, user):
    """The line's author, or an admin."""
    return user.is_admin or item.created_by == user.id


def delete_item(item):
    db.session.delete(item)
    db.session.commit()


# --- Attachments (images + PDFs only) -----------------------------------------

def _plan_dir(plan_id):
    path = os.path.join(
        current_app.config["UPLOAD_FOLDER"], "plans", str(plan_id)
    )
    os.makedirs(path, exist_ok=True)
    return path


def attachment_path(attachment):
    return os.path.join(_plan_dir(attachment.plan_id), attachment.filename)


def can_delete_attachment(attachment, user):
    """The uploader, or an admin (same rule as deleting a photo)."""
    return user.is_admin or attachment.uploaded_by == user.id


def save_attachment(plan, file, user):
    """Validate + store one uploaded file. Returns (attachment, error):
    exactly one is None. Mirrors the photo uploader's forgiving, friendly
    feedback."""
    if not file or not file.filename:
        return None, "No file was chosen."

    name = file.filename
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in ALLOWED_EXTENSIONS:
        return None, (
            f'"{name}" isn\'t a kind of file we allow here. '
            "You can share photos and PDFs."
        )

    stored_name = f"{uuid.uuid4().hex}"
    if ext == "pdf":
        # Validate by MAGIC BYTES, not the extension: a real PDF begins
        # with "%PDF-". Renaming malware.exe to plan.pdf fails this.
        head = file.stream.read(5)
        file.stream.seek(0)
        if head != b"%PDF-":
            return None, f'"{name}" doesn\'t look like a real PDF file.'
        stored_name += ".pdf"
        full_path = os.path.join(_plan_dir(plan.id), stored_name)
        file.save(full_path)
        kind = "pdf"
    else:
        # Image: verify the bytes really are an image, then RE-ENCODE to
        # strip EXIF/GPS — the same privacy rule as the photo gallery
        # (Ch. 11). GIF passes through to keep animation.
        try:
            Image.open(file.stream).verify()
        except (UnidentifiedImageError, OSError):
            return None, f'"{name}" doesn\'t look like a real image file.'
        file.stream.seek(0)
        if ext == "gif":
            stored_name += ".gif"
            full_path = os.path.join(_plan_dir(plan.id), stored_name)
            file.save(full_path)
        else:
            out_ext = "jpg" if ext in ("jpg", "jpeg", "heic", "heif") else ext
            stored_name += f".{out_ext}"
            full_path = os.path.join(_plan_dir(plan.id), stored_name)
            img = ImageOps.exif_transpose(Image.open(file.stream))
            for meta_key in ("exif", "xmp", "XML:com.adobe.xmp"):
                img.info.pop(meta_key, None)
            fmt = "JPEG" if out_ext == "jpg" else out_ext.upper()
            if fmt == "JPEG":
                img.convert("RGB").save(full_path, fmt, quality=90)
            else:
                img.save(full_path, fmt)
        kind = "image"

    attachment = PlanAttachment(
        plan_id=plan.id, filename=stored_name, original_filename=name[:255],
        kind=kind, uploaded_by=user.id,
    )
    db.session.add(attachment)
    audit_service.log_event(user, "upload", "plan", plan.id,
                            f"attached {name}")
    db.session.commit()
    return attachment, None


def delete_attachment(attachment, user):
    path = attachment_path(attachment)
    if os.path.exists(path):
        os.remove(path)
    audit_service.log_event(user, "delete", "plan attachment", attachment.id)
    db.session.delete(attachment)
    db.session.commit()
