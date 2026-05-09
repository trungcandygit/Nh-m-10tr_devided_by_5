"""
Parser file .eml đặt hàng từ đại lý
Cấu trúc email thực tế:
  Subject: "[ĐẶT HÀNG] BH26.XXXX" hoặc "Purchase Order BH26.XXXX"
  Body: Số chứng từ, Ngày đặt, MST, tổng số lượng, tổng giá trị
  Attachment: file PDF BH26_XXXX.pdf
"""
import email
import email.policy
import re
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("tnbike.email_parser")


@dataclass
class EmailData:
    message_id:       str
    from_address:     str
    from_name:        str
    received_at:      str
    subject:          str
    attachment_name:  str
    attachment_bytes: bytes
    body_text:        str
    raw_path:         str
    # Các trường trích từ body email
    so_number_body:   str = ""   # Số chứng từ trong body
    order_date_body:  str = ""   # Ngày đặt trong body
    mst_body:         str = ""   # MST đại lý trong body
    error:            Optional[str] = None


def _decode_header(value: str) -> str:
    """Giải mã email header có encoding (quoted-printable, base64)."""
    from email.header import decode_header as _dh
    parts = _dh(value)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def parse_eml(path: Path) -> EmailData:
    """Đọc 1 file .eml → EmailData. Trả về error nếu file rỗng."""
    raw = path.read_bytes()
    if not raw:
        return EmailData(
            message_id=path.stem, from_address="", from_name="",
            received_at="", subject="", attachment_name="",
            attachment_bytes=b"", body_text="", raw_path=str(path),
            error="File rỗng"
        )

    try:
        msg = email.message_from_bytes(raw, policy=email.policy.default)
    except Exception:
        msg = email.message_from_bytes(raw, policy=email.policy.compat32)

    from_raw = str(msg.get("From", ""))
    m = re.match(r'^"?([^"<]*)"?\s*<?([^>]*)>?\s*$', from_raw.strip())
    from_name    = _decode_header(m.group(1).strip()) if m else ""
    from_address = m.group(2).strip() if m else from_raw.strip()

    subject_raw = str(msg.get("Subject", ""))
    subject     = _decode_header(subject_raw)
    date_raw    = str(msg.get("Date", ""))
    message_id  = str(msg.get("Message-ID", path.stem))

    attachment_name  = ""
    attachment_bytes = b""
    body_text        = ""

    for part in msg.walk():
        content_type = part.get_content_type()
        disposition  = str(part.get("Content-Disposition", ""))

        if content_type == "text/plain" and "attachment" not in disposition:
            try:
                body_text = part.get_content()
            except Exception:
                raw_body = part.get_payload(decode=True) or b""
                body_text = raw_body.decode("utf-8", errors="replace")

        elif content_type == "application/pdf" or (
            "attachment" in disposition and ".pdf" in disposition.lower()
        ):
            fname = part.get_filename() or f"{path.stem}.pdf"
            try:
                fname = _decode_header(fname)
            except Exception:
                pass
            attachment_name  = fname
            attachment_bytes = part.get_payload(decode=True) or b""

    # Trích thông tin từ body email
    so_number_body  = ""
    order_date_body = ""
    mst_body        = ""

    if body_text:
        m_so = re.search(r'S[ốo]\s*ch[ứu]ng\s*t[ừu]\s*[:\|]\s*(BH\d+\.\d+)', body_text, re.IGNORECASE)
        if m_so:
            so_number_body = m_so.group(1).strip()

        m_date = re.search(r'Ng[àa]y\s+[đd][ặa]t\s*[:\|]\s*([\d/\-]+)', body_text, re.IGNORECASE)
        if m_date:
            order_date_body = m_date.group(1).strip()

        m_mst = re.search(r'MST\s*[:\|]\s*(\d{10,13})', body_text, re.IGNORECASE)
        if m_mst:
            mst_body = m_mst.group(1).strip()

    # Fallback: lấy số đơn từ tên file nếu body không có
    if not so_number_body:
        m_fn = re.search(r'(BH26\.\d+)', subject + " " + path.stem.replace("_", "."))
        if m_fn:
            so_number_body = m_fn.group(1)

    return EmailData(
        message_id=message_id,
        from_address=from_address,
        from_name=from_name,
        received_at=date_raw,
        subject=subject,
        attachment_name=attachment_name,
        attachment_bytes=attachment_bytes,
        body_text=body_text,
        raw_path=str(path),
        so_number_body=so_number_body,
        order_date_body=order_date_body,
        mst_body=mst_body,
    )


def parse_all_emails(email_dir: Path) -> list:
    """Đọc toàn bộ .eml trong thư mục, bỏ qua file rỗng."""
    results = []
    files = sorted(email_dir.glob("*.eml"))
    logger.info(f"Tìm thấy {len(files)} file .eml trong {email_dir}")
    for f in files:
        try:
            ed = parse_eml(f)
            results.append(ed)
        except Exception as e:
            logger.warning(f"Lỗi đọc {f.name}: {e}")
            results.append(EmailData(
                message_id=f.stem, from_address="", from_name="",
                received_at="", subject="", attachment_name="",
                attachment_bytes=b"", body_text="", raw_path=str(f),
                error=str(e)
            ))
    return results
