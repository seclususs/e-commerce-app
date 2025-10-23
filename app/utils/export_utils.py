import csv
from io import StringIO
from datetime import datetime
from flask import Response


def generate_csv_response(data, headers, report_name):
    si = StringIO()
    cw = csv.writer(si)

    cw.writerow(headers)
    if data:
        for row in data:
            cw.writerow(row)

    output = si.getvalue()

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={report_name}_report_{datetime.now().strftime('%Y%m%d')}.csv"}
    )