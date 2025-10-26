import csv
from datetime import datetime
from io import StringIO
from typing import Any, Iterable, List

from flask import Response

from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


def generate_csv_response(
    data: Iterable[Iterable[Any]], headers: List[str], report_name: str
) -> Response:
    logger.debug(
        f"Membuat respons CSV untuk laporan: {report_name}, "
        f"Headers: {headers}, Baris data: {len(list(data)) if data else 0}"
    )

    si: StringIO = StringIO()
    csv_writer = csv.writer(si)
    csv_writer.writerow(headers)

    if data:
        for row in data:
            csv_writer.writerow(row)

    output: str = si.getvalue()
    filename: str = (
        f"{report_name}_report_{datetime.now().strftime('%Y%m%d')}.csv"
    )

    logger.info(
        f"CSV berhasil dibuat untuk {report_name}. Nama file: {filename}"
    )

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )