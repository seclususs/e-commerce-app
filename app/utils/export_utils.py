import csv
from io import StringIO
from datetime import datetime
from flask import Response

def generate_csv_response(data, headers, report_name):
    """
    Membuat file CSV dari data dan header, lalu mengembalikannya sebagai Flask Response.
    
    :param data: List of tuples/rows dari database.
    :param headers: List of strings untuk header kolom CSV.
    :param report_name: Nama file laporan (tanpa ekstensi).
    :return: Objek Flask Response dengan file CSV.
    """
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